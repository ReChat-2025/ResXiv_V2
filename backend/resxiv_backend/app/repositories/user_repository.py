"""
User Repository

Data access layer for user-related operations.
Handles all database interactions for users, authentication tokens, and sessions.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload
import uuid
import secrets
import hashlib
import logging

logger = logging.getLogger(__name__)

from app.schemas.user import User, EmailVerificationToken, PasswordResetToken, UserSession
from app.models.user import UserProfileUpdate
from app.core.auth import PasswordService


class UserRepository:
    """Repository for user data access operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ================================
    # USER CRUD OPERATIONS
    # ================================
    
    async def create_user(
        self,
        name: str,
        email: str,
        password: str,
        username: str = None,
        interests: List[str] = None,
        accepted_terms: bool = False
    ) -> User:
        """
        Create a new user
        
        Args:
            name: User's full name
            email: User's email address
            password: Plain text password (will be hashed)
            username: Username (optional, will use email if not provided)
            interests: List of research interests
            accepted_terms: Whether user accepted terms and conditions
            
        Returns:
            Created user object
        """
        hashed_password = PasswordService.hash_password(password)
        
        user = User(
            name=" ".join(word.capitalize() for word in name.strip().split()),
            email=email.lower(),
            password=hashed_password,
            interests=interests or [],
            accepted_terms=accepted_terms,
            email_verified=False
        )
        
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        
        return user
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(
            and_(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        stmt = select(User).where(
            and_(User.email == email.lower(), User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Legacy helper – treat username as email (username field removed)"""
        return await self.get_user_by_email(username)
    
    async def update_user(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[User]:
        """
        Update user information
        
        Args:
            user_id: User ID to update
            **kwargs: Fields to update
            
        Returns:
            Updated user object or None if not found
        """
        # Remove None values and handle special cases
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if 'email' in update_data:
            update_data['email'] = update_data['email'].lower()
        
        if 'password' in update_data:
            update_data['password'] = PasswordService.hash_password(update_data['password'])
        
        if update_data:
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            stmt = (
                update(User)
                .where(and_(User.id == user_id, User.deleted_at.is_(None)))
                .values(**update_data)
                .returning(User)
            )
            
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        
        return await self.get_user_by_id(user_id)
    
    async def update_user_profile(self, user_id: uuid.UUID, profile_data: UserProfileUpdate) -> Optional[User]:
        """Update user profile fields (name, intro, interests, public_key) by reusing update_user"""
        return await self.update_user(
            user_id,
            name=profile_data.name,
            intro=profile_data.intro,
            interests=profile_data.interests,
            public_key=profile_data.public_key
        )
    
    async def soft_delete_user(self, user_id: uuid.UUID) -> bool:
        """Soft delete a user (mark as deleted)"""
        stmt = (
            update(User)
            .where(and_(User.id == user_id, User.deleted_at.is_(None)))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def update_last_login(self, user_id: uuid.UUID) -> bool:
        """Update user's last login timestamp"""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    # ================================
    # EMAIL VERIFICATION OPERATIONS
    # ================================
    
    async def create_email_verification_token(
        self,
        user_id: uuid.UUID,
        email: str,
        expires_in_hours: int = 24
    ) -> EmailVerificationToken:
        """Create email verification token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        # Invalidate any existing tokens for this user
        await self._invalidate_email_verification_tokens(user_id)
        
        verification_token = EmailVerificationToken(
            user_id=user_id,
            email=email.lower(),
            token=token,
            expires_at=expires_at
        )
        
        self.session.add(verification_token)
        await self.session.flush()
        await self.session.refresh(verification_token)
        
        return verification_token
    
    async def get_email_verification_token(
        self,
        token: str
    ) -> Optional[EmailVerificationToken]:
        """Get email verification token"""
        stmt = select(EmailVerificationToken).where(
            and_(
                EmailVerificationToken.token == token,
                EmailVerificationToken.expires_at > datetime.now(timezone.utc),
                EmailVerificationToken.verified_at.is_(None)
            )
        ).options(selectinload(EmailVerificationToken.user))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def verify_email_token(self, token: str) -> Optional[User]:
        """Verify email using token and mark user as verified"""
        verification_token = await self.get_email_verification_token(token)
        
        if not verification_token:
            return None
        
        # Mark token as verified
        verification_token.verified_at = datetime.now(timezone.utc)
        
        # Mark user as email verified
        user = verification_token.user
        user.email_verified = True
        user.updated_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        
        return user
    
    async def _invalidate_email_verification_tokens(self, user_id: uuid.UUID):
        """Invalidate existing email verification tokens for user"""
        stmt = (
            update(EmailVerificationToken)
            .where(
                and_(
                    EmailVerificationToken.user_id == user_id,
                    EmailVerificationToken.verified_at.is_(None)
                )
            )
            .values(verified_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
    
    # ================================
    # PASSWORD RESET OPERATIONS
    # ================================
    
    async def create_password_reset_token(
        self,
        user_id: uuid.UUID,
        expires_in_hours: int = 2
    ) -> PasswordResetToken:
        """Create password reset token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        # Invalidate any existing tokens for this user
        await self._invalidate_password_reset_tokens(user_id)
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        self.session.add(reset_token)
        await self.session.flush()
        await self.session.refresh(reset_token)
        
        return reset_token
    
    async def get_password_reset_token(
        self,
        token: str
    ) -> Optional[PasswordResetToken]:
        """Get password reset token"""
        stmt = select(PasswordResetToken).where(
            and_(
                PasswordResetToken.token == token,
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
                PasswordResetToken.used == False
            )
        ).options(selectinload(PasswordResetToken.user))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_recent_password_reset_tokens(
        self,
        user_id: uuid.UUID,
        since: datetime
    ) -> List[PasswordResetToken]:
        """Get recent password reset tokens for rate limiting"""
        stmt = select(PasswordResetToken).where(
            and_(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.created_at >= since
            )
        ).order_by(PasswordResetToken.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def use_password_reset_token(
        self,
        token: str,
        new_password: str
    ) -> Optional[User]:
        """Use password reset token to reset password"""
        reset_token = await self.get_password_reset_token(token)
        
        if not reset_token:
            return None
        
        # Mark token as used
        reset_token.used = True
        
        # Update user password
        user = reset_token.user
        user.password = PasswordService.hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        # Invalidate all user sessions
        await self._invalidate_user_sessions(user.id)
        
        await self.session.flush()
        
        return user
    
    async def invalidate_password_reset_token(self, token: str) -> bool:
        """Invalidate a specific password reset token"""
        stmt = (
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.used == False
                )
            )
            .values(used=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def _invalidate_password_reset_tokens(self, user_id: uuid.UUID):
        """Invalidate existing password reset tokens for user"""
        stmt = (
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used == False
                )
            )
            .values(used=True)
        )
        await self.session.execute(stmt)
    
    # ================================
    # SESSION MANAGEMENT OPERATIONS
    # ================================
    
    async def create_user_session(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str = None,
        ip_address: str = None
    ) -> UserSession:
        """Create user session"""
        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        self.session.add(session)
        await self.session.flush()
        await self.session.refresh(session)
        
        return session
    
    async def get_user_session(self, token_hash: str) -> Optional[UserSession]:
        """Get user session by token hash"""
        stmt = select(UserSession).where(
            and_(
                UserSession.token_hash == token_hash,
                UserSession.expires_at > datetime.now(timezone.utc)
            )
        ).options(selectinload(UserSession.user))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_session_last_used(self, session_id: uuid.UUID) -> bool:
        """Update session last used timestamp"""
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def delete_user_session(self, token_hash: str) -> bool:
        """Delete user session (logout)"""
        stmt = delete(UserSession).where(UserSession.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def invalidate_all_refresh_tokens(self, user_id: uuid.UUID) -> int:
        """Invalidate all refresh tokens (sessions) for a user"""
        return await self._invalidate_user_sessions(user_id)
    
    async def _invalidate_user_sessions(self, user_id: uuid.UUID):
        """Invalidate all sessions for a user"""
        stmt = delete(UserSession).where(UserSession.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        stmt = delete(UserSession).where(
            UserSession.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token: str,
        request_info: Dict[Any, Any] = None
    ) -> UserSession:
        """Store refresh token as a user session"""
        # Hash the token for security
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Extract request info
        user_agent = None
        ip_address = None
        if request_info:
            user_agent = request_info.get('user_agent')
            ip_address = request_info.get('ip_address')
        
        # Refresh tokens typically expire in 7 days
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        return await self.create_user_session(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    async def get_refresh_token(self, user_id: uuid.UUID, token: str):
        """Retrieve stored refresh token (session) by token string"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return await self.get_user_session(token_hash)

    async def replace_refresh_token(
        self,
        old_token: str,
        new_token: str,
        user_id: uuid.UUID,
        request_info: Dict[Any, Any] = None
    ):
        """Replace old refresh token with new one in sessions"""
        # Delete old session
        old_hash = hashlib.sha256(old_token.encode()).hexdigest()
        await self.delete_user_session(old_hash)
        # Store new token
        await self.store_refresh_token(user_id, new_token, request_info)
    
    # ================================
    # VALIDATION AND UTILITY METHODS
    # ================================
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        stmt = select(User.id).where(
            and_(User.email == email.lower(), User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def verify_password(self, email: str, password: str) -> Optional[User]:
        """Verify user password and return user if valid"""
        user = await self.get_user_by_email(email)
        
        if user and PasswordService.verify_password(password, user.password):
            return user
        
        return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password - alias for verify_password"""
        return await self.verify_password(email, password)
    
    async def update_password(self, user_id: uuid.UUID, new_password: str) -> Optional[User]:
        """Update user password by ID"""
        return await self.update_user(user_id, password=new_password)
    
    async def get_user_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user statistics including project and paper counts"""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return {}
        
        # Get actual project and paper counts
        try:
            from sqlalchemy import text
            
            # Count projects where user is a member
            projects_query = text("""
                SELECT COUNT(DISTINCT project_id) 
                FROM project_members 
                WHERE user_id = :user_id
            """)
            projects_result = await self.session.execute(projects_query, {"user_id": user_id})
            projects_count = projects_result.scalar() or 0
            
            # Count papers in projects where user is a member
            papers_query = text("""
                SELECT COUNT(DISTINCT pp.paper_id) 
                FROM project_papers pp
                INNER JOIN project_members pm ON pp.project_id = pm.project_id
                WHERE pm.user_id = :user_id
            """)
            papers_result = await self.session.execute(papers_query, {"user_id": user_id})
            papers_count = papers_result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Failed to get user stats counts: {e}")
            projects_count = 0
            papers_count = 0
        
        return {
            "user_id": user.id,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "email_verified": user.email_verified,
            "interests_count": len(user.interests),
            "projects_count": projects_count,
            "papers_count": papers_count
        } 

    async def get_user_statistics(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Alias for get_user_stats for backward compatibility"""
        return await self.get_user_stats(user_id) 