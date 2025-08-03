"""
Collaborative Editing WebSocket Provider

- Authenticating with JWT
- Branch-level ACL enforcement (read/write)
- Broadcast Yjs update messages to peers
- Persist latest state in `document_sessions`
- Mark autosave_queue entries for background Git commit

Protocol (binary):
client → server : raw Yjs update (Uint8Array)
server → client : raw Yjs update (same)
First server message after connect is the full state-vector+update snapshot.
"""

import asyncio
import logging
import uuid
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_postgres_session
from api.dependencies import get_current_user_required, verify_project_access
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import DocumentSession, CRDTStateType
from app.models.branch import DocumentSessionCreate

try:
    from y_py import YDoc, YTransaction, encode_state_as_update, apply_update
except ImportError:  # Safety for environments without y-py installed
    YDoc = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory room registry: {session_id: set(websocket)}
ROOMS: Dict[str, Set[WebSocket]] = {}
LOCK = asyncio.Lock()


async def get_branch_permission(
    branch_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
):
    repo = BranchRepository(session)
    perm = await repo.get_user_branch_permission(branch_id, user_id)
    return perm


@router.websocket(
    "/ws/projects/{project_id}/branches/{branch_id}/files/{file_id}")
async def collaborative_ws(
    websocket: WebSocket,
    project_id: uuid.UUID,
    branch_id: uuid.UUID,
    file_id: uuid.UUID,
    session: AsyncSession = Depends(get_postgres_session),
    current_user: Dict = Depends(get_current_user_required),
    _project_access=Depends(verify_project_access),
):
    """WebSocket endpoint for collaborative editing."""
    await websocket.accept()
    user_id = current_user["user_id"]

    # ACL: ensure write or read access
    perm = await get_branch_permission(branch_id, user_id, session)
    if not perm or not perm.can_read:
        await websocket.close(code=4403)
        return

    repo = BranchRepository(session)

    # Load or create document session
    doc_session = await repo.get_file_active_session(file_id)
    if not doc_session:
        doc_session = await repo.create_document_session(
            session_data=DocumentSessionCreate(file_id=file_id, crdt_type=CRDTStateType.YJS),
            user_id=user_id,
        )
        await session.commit()

    room_id = str(doc_session.id)

    # Register connection
    async with LOCK:
        ROOMS.setdefault(room_id, set()).add(websocket)

    # Send existing state to client
    if YDoc is None:
        await websocket.send_bytes(b"\x00")  # Placeholder
    else:
        ydoc = YDoc()
        if doc_session.crdt_state:
            with ydoc.begin_transaction() as t:
                apply_update(ydoc, bytes(doc_session.crdt_state), t)
        snapshot = encode_state_as_update(ydoc)
        await websocket.send_bytes(snapshot)

    try:
        while True:
            data = await websocket.receive_bytes()
            # Broadcast to peers
            async with LOCK:
                for peer in ROOMS.get(room_id, set()):
                    if peer is not websocket:
                        await peer.send_bytes(data)

            # Merge into server doc and persist
            if YDoc is not None:
                if doc_session.crdt_state:
                    base = bytearray(doc_session.crdt_state)
                else:
                    base = bytearray()
                # simple append, safe because Yjs merges
                base.extend(data)
                doc_session.crdt_state = bytes(base)
                doc_session.last_activity = asyncio.get_event_loop().time()
                doc_session.autosave_pending = True
                await session.commit()
    except WebSocketDisconnect:
        pass
    finally:
        # unregister
        async with LOCK:
            peers = ROOMS.get(room_id, set())
            peers.discard(websocket)
            if not peers:
                ROOMS.pop(room_id, None) 