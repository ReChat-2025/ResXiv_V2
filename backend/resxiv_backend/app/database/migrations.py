"""
Database Migration Manager

Handles database schema migrations for the ResXiv backend.
Provides a clean interface for running schema updates.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import db_manager

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self):
        self.migrations: List[Dict[str, Any]] = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations"""
        self.migrations = [
            {
                "id": "001_fix_project_slug_uniqueness",
                "description": "Fix project slug uniqueness to work with soft deletes",
                "up": self._fix_project_slug_uniqueness_up,
                "down": self._fix_project_slug_uniqueness_down,
                "version": "1.0.0"
            },
            {
                "id": "002_add_collaborative_latex_tables",
                "description": "Add tables for Git-like collaborative LaTeX editor",
                "up": self._add_collaborative_latex_tables_up,
                "down": self._add_collaborative_latex_tables_down,
                "version": "1.1.0"
            },
            {
                "id": "003_add_paper_extra_columns",
                "description": "Add new metadata columns to papers table (xml_path, arxiv_id, doi, etc.)",
                "up": self._add_paper_extra_columns_up,
                "down": self._add_paper_extra_columns_down,
                "version": "1.2.0"
            },
            {
                "id": "004_add_diagnostics_extra_columns",
                "description": "Add strengths, contributions, limitations columns to diagnostics table",
                "up": self._add_diagnostics_extra_columns_up,
                "down": self._add_diagnostics_extra_columns_down,
                "version": "1.3.0"
            },
            {
                "id": "005_add_paper_embeddings_table",
                "description": "Add paper_embeddings table for semantic search with all-mini-lmv6 model",
                "up": self._add_paper_embeddings_table_up,
                "down": self._add_paper_embeddings_table_down,
                "version": "1.4.0"
            },
            {
                "id": "006_add_user_saved_searches_table",
                "description": "Add user_saved_searches table for search functionality",
                "up": self._add_user_saved_searches_table_up,
                "down": self._add_user_saved_searches_table_down,
                "version": "1.5.0"
            }
        ]
    
    async def run_migration(self, migration_id: str) -> bool:
        """
        Run a specific migration
        
        Args:
            migration_id: ID of migration to run
            
        Returns:
            True if successful, False otherwise
        """
        migration = next((m for m in self.migrations if m["id"] == migration_id), None)
        if not migration:
            logger.error(f"Migration {migration_id} not found")
            return False
        
        try:
            if not db_manager._initialized:
                await db_manager.initialize()
            
            async with db_manager.get_postgres_session() as session:
                logger.info(f"Running migration: {migration['description']}")
                await migration["up"](session)
                await session.commit()
                logger.info(f"Migration {migration_id} completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Migration {migration_id} failed: {str(e)}")
            return False
    
    async def rollback_migration(self, migration_id: str) -> bool:
        """
        Rollback a specific migration
        
        Args:
            migration_id: ID of migration to rollback
            
        Returns:
            True if successful, False otherwise
        """
        migration = next((m for m in self.migrations if m["id"] == migration_id), None)
        if not migration:
            logger.error(f"Migration {migration_id} not found")
            return False
        
        try:
            if not db_manager._initialized:
                await db_manager.initialize()
            
            async with db_manager.get_postgres_session() as session:
                logger.info(f"Rolling back migration: {migration['description']}")
                await migration["down"](session)
                await session.commit()
                logger.info(f"Migration {migration_id} rollback completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Migration {migration_id} rollback failed: {str(e)}")
            return False
    
    async def list_migrations(self) -> List[Dict[str, str]]:
        """List all available migrations"""
        return [
            {
                "id": m["id"],
                "description": m["description"],
                "version": m["version"]
            }
            for m in self.migrations
        ]
    
    # Migration implementations
    
    async def _fix_project_slug_uniqueness_up(self, session: AsyncSession):
        """
        Migration: Fix project slug uniqueness to work with soft deletes
        
        This migration:
        1. Drops the existing unique constraint on projects.slug
        2. Creates a partial unique index that only applies to non-deleted rows
        
        This follows industry best practices for soft-delete uniqueness.
        """
        
        # Step 1: Drop existing unique constraint if it exists
        await session.execute(text("""
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'projects_slug_key' 
                    AND table_name = 'projects'
                ) THEN
                    ALTER TABLE projects DROP CONSTRAINT projects_slug_key;
                    RAISE NOTICE 'Dropped existing projects_slug_key constraint';
                ELSE
                    RAISE NOTICE 'projects_slug_key constraint does not exist, skipping';
                END IF;
            END $$;
        """))
        
        # Step 2: Drop existing unique index if it exists (in case it was created manually)
        await session.execute(text("""
            DROP INDEX IF EXISTS projects_slug_key;
        """))
        
        # Step 3: Create partial unique index for active projects only
        await session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_projects_slug_unique_active
                ON projects(slug)
                WHERE deleted_at IS NULL;
        """))
        
        # Step 4: Create additional performance indexes if they don't exist
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_projects_created_by ON projects(created_by);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_projects_deleted_at ON projects(deleted_at);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_projects_created_at ON projects(created_at);
        """))
        
        logger.info("✅ Project slug uniqueness constraint fixed")
        logger.info("   - Dropped old unique constraint")
        logger.info("   - Created partial unique index for active projects only")
        logger.info("   - Added performance indexes")
    
    async def _fix_project_slug_uniqueness_down(self, session: AsyncSession):
        """
        Rollback: Restore original unique constraint
        
        WARNING: This rollback may fail if there are soft-deleted projects
        with duplicate slugs. Clean up data before rolling back.
        """
        
        # Step 1: Drop the partial unique index
        await session.execute(text("""
            DROP INDEX IF EXISTS ix_projects_slug_unique_active;
        """))
        
        # Step 2: Restore the simple unique constraint
        # Note: This may fail if there are conflicts with soft-deleted rows
        await session.execute(text("""
            DO $$ 
            BEGIN
                BEGIN
                    ALTER TABLE projects ADD CONSTRAINT projects_slug_key UNIQUE (slug);
                    RAISE NOTICE 'Restored projects_slug_key unique constraint';
                EXCEPTION WHEN unique_violation THEN
                    RAISE EXCEPTION 'Cannot restore unique constraint: duplicate slugs exist. Clean up soft-deleted projects first.';
                END;
            END $$;
        """))
        
        logger.info("⚠️  Rolled back to original unique constraint")
        logger.info("   - Removed partial unique index")
        logger.info("   - Restored simple unique constraint on slug")

    async def _add_collaborative_latex_tables_up(self, session: AsyncSession):
        """Add tables for collaborative LaTeX editor functionality"""
        
        # Create ENUM types
        await session.execute(text("""
            DO $$ 
            BEGIN
                -- Create branch_status enum
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'branch_status') THEN
                    CREATE TYPE branch_status AS ENUM ('active', 'merged', 'archived', 'deleted');
                END IF;
                
                -- Create crdt_state_type enum  
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'crdt_state_type') THEN
                    CREATE TYPE crdt_state_type AS ENUM ('yjs', 'automerge', 'json');
                END IF;
            END $$;
        """))
        
        # Create branches table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS branches (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                source_branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
                head_commit_hash TEXT,
                status branch_status DEFAULT 'active',
                is_default BOOLEAN DEFAULT FALSE,
                is_protected BOOLEAN DEFAULT FALSE,
                created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                merged_at TIMESTAMPTZ,
                merged_by UUID REFERENCES users(id) ON DELETE SET NULL,
                deleted_at TIMESTAMPTZ,
                
                CONSTRAINT unique_project_branch_name UNIQUE (project_id, name),
                CONSTRAINT no_self_source CHECK (id != source_branch_id)
            );
        """))
        
        # Create branch_permissions table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS branch_permissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                can_read BOOLEAN DEFAULT TRUE,
                can_write BOOLEAN DEFAULT FALSE,
                can_admin BOOLEAN DEFAULT FALSE,
                granted_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                granted_at TIMESTAMPTZ DEFAULT now(),
                
                CONSTRAINT unique_branch_user_permission UNIQUE (branch_id, user_id)
            );
        """))
        
        # Create latex_files table
        # Create latex_files table for metadata only (NO CONTENT STORAGE)
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS latex_files (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT DEFAULT 'tex',
                file_size BIGINT DEFAULT 0,
                encoding TEXT DEFAULT 'utf-8',
                created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                last_modified_by UUID REFERENCES users(id) ON DELETE SET NULL,
                deleted_at TIMESTAMPTZ,
                
                CONSTRAINT unique_branch_file_path UNIQUE (branch_id, file_path)
            );
        """))
        
        # Create document_sessions table for CRDT state
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS document_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id UUID NOT NULL REFERENCES latex_files(id) ON DELETE CASCADE,
                session_token TEXT NOT NULL UNIQUE,
                crdt_state JSONB,
                crdt_type crdt_state_type DEFAULT 'yjs',
                active_users JSONB DEFAULT '[]'::jsonb,
                last_activity TIMESTAMPTZ DEFAULT now(),
                autosave_pending BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '24 hours'
            );
        """))
        
        # Create git_repositories table to track repo state
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS git_repositories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE UNIQUE,
                repo_path TEXT NOT NULL,
                repo_url TEXT,
                default_branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
                last_commit_hash TEXT,
                initialized BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """))
        
        # Create autosave_queue table for managing Git commits
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS autosave_queue (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                file_id UUID NOT NULL REFERENCES latex_files(id) ON DELETE CASCADE,
                branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
                change_summary TEXT,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content_snapshot TEXT,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                scheduled_at TIMESTAMPTZ DEFAULT now(),
                processed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """))

        # Create indexes individually to avoid prepared statement issues
        indexes = [
            # Branches indexes
            "CREATE INDEX IF NOT EXISTS idx_branches_project_id ON branches(project_id);",
            "CREATE INDEX IF NOT EXISTS idx_branches_created_by ON branches(created_by);",
            "CREATE INDEX IF NOT EXISTS idx_branches_status ON branches(status);",
            "CREATE INDEX IF NOT EXISTS idx_branches_name ON branches(name);",
            "CREATE INDEX IF NOT EXISTS idx_branches_source_branch_id ON branches(source_branch_id);",
            
            # Branch permissions indexes
            "CREATE INDEX IF NOT EXISTS idx_branch_permissions_branch_id ON branch_permissions(branch_id);",
            "CREATE INDEX IF NOT EXISTS idx_branch_permissions_user_id ON branch_permissions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_branch_permissions_can_write ON branch_permissions(can_write);",
            
            # LaTeX files indexes
            "CREATE INDEX IF NOT EXISTS idx_latex_files_project_id ON latex_files(project_id);",
            "CREATE INDEX IF NOT EXISTS idx_latex_files_branch_id ON latex_files(branch_id);",
            "CREATE INDEX IF NOT EXISTS idx_latex_files_file_path ON latex_files(file_path);",
            "CREATE INDEX IF NOT EXISTS idx_latex_files_file_type ON latex_files(file_type);",
            "CREATE INDEX IF NOT EXISTS idx_latex_files_created_by ON latex_files(created_by);",
            "CREATE INDEX IF NOT EXISTS idx_latex_files_deleted_at ON latex_files(deleted_at);",
            
            # Document sessions indexes
            "CREATE INDEX IF NOT EXISTS idx_document_sessions_file_id ON document_sessions(file_id);",
            "CREATE INDEX IF NOT EXISTS idx_document_sessions_session_token ON document_sessions(session_token);",
            "CREATE INDEX IF NOT EXISTS idx_document_sessions_last_activity ON document_sessions(last_activity);",
            "CREATE INDEX IF NOT EXISTS idx_document_sessions_expires_at ON document_sessions(expires_at);",
            
            # Git repositories indexes
            "CREATE INDEX IF NOT EXISTS idx_git_repositories_project_id ON git_repositories(project_id);",
            "CREATE INDEX IF NOT EXISTS idx_git_repositories_default_branch_id ON git_repositories(default_branch_id);",
            
            # Autosave queue indexes
            "CREATE INDEX IF NOT EXISTS idx_autosave_queue_file_id ON autosave_queue(file_id);",
            "CREATE INDEX IF NOT EXISTS idx_autosave_queue_branch_id ON autosave_queue(branch_id);",
            "CREATE INDEX IF NOT EXISTS idx_autosave_queue_status ON autosave_queue(status);",
            "CREATE INDEX IF NOT EXISTS idx_autosave_queue_scheduled_at ON autosave_queue(scheduled_at);",
            "CREATE INDEX IF NOT EXISTS idx_autosave_queue_priority ON autosave_queue(priority);",
        ]
        
        # Execute each index creation individually
        for index_sql in indexes:
            await session.execute(text(index_sql))

        # Create triggers individually
        triggers = [
            # Branches trigger
            "DROP TRIGGER IF EXISTS update_branches_updated_at ON branches;",
            "CREATE TRIGGER update_branches_updated_at BEFORE UPDATE ON branches FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            
            # LaTeX files trigger
            "DROP TRIGGER IF EXISTS update_latex_files_updated_at ON latex_files;",
            "CREATE TRIGGER update_latex_files_updated_at BEFORE UPDATE ON latex_files FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
            
            # Git repositories trigger
            "DROP TRIGGER IF EXISTS update_git_repositories_updated_at ON git_repositories;",
            "CREATE TRIGGER update_git_repositories_updated_at BEFORE UPDATE ON git_repositories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();",
        ]
        
        # Execute each trigger creation individually
        for trigger_sql in triggers:
            await session.execute(text(trigger_sql))

        logger.info("Successfully created collaborative LaTeX editor tables")

    async def _add_collaborative_latex_tables_down(self, session: AsyncSession):
        """Rollback collaborative LaTeX editor tables"""
        
        # Drop tables in reverse dependency order
        tables = [
            'autosave_queue',
            'document_sessions', 
            'latex_files',
            'branch_permissions',
            'branches',
            'git_repositories'
        ]
        
        for table in tables:
            await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        
        # Drop custom ENUM types
        await session.execute(text("""
            DROP TYPE IF EXISTS branch_status CASCADE;
            DROP TYPE IF EXISTS crdt_state_type CASCADE;
        """))
        
        logger.info("Successfully rolled back collaborative LaTeX editor tables")

    async def _add_paper_extra_columns_up(self, session: AsyncSession):
        """Migration: add new metadata columns to papers table"""

        # Add columns if they do not already exist. We must execute each command separately
        commands = [
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS xml_path TEXT;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS checksum TEXT;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS private_uploaded BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS authors TEXT[] DEFAULT ARRAY[]::TEXT[];",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT ARRAY[]::TEXT[];",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS arxiv_id TEXT;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS doi TEXT;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS abstract TEXT;",
            "ALTER TABLE papers ADD COLUMN IF NOT EXISTS safe_title TEXT;",
        ]

        for cmd in commands:
            await session.execute(text(cmd))

        logger.info("✅ Added extra columns to papers table")

    async def _add_paper_extra_columns_down(self, session: AsyncSession):
        """Rollback: drop the added paper columns"""

        commands = [
            "ALTER TABLE papers DROP COLUMN IF EXISTS xml_path;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS checksum;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS private_uploaded;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS authors;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS keywords;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS arxiv_id;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS doi;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS abstract;",
            "ALTER TABLE papers DROP COLUMN IF EXISTS safe_title;",
        ]

        for cmd in commands:
            await session.execute(text(cmd))

        logger.info("↩️  Rolled back extra columns from papers table")

    async def _add_diagnostics_extra_columns_up(self, session: AsyncSession):
        """Migration: add extra text columns to diagnostics table"""

        commands = [
            "ALTER TABLE diagnostics ADD COLUMN IF NOT EXISTS strengths TEXT;",
            "ALTER TABLE diagnostics ADD COLUMN IF NOT EXISTS contributions TEXT;",
            "ALTER TABLE diagnostics ADD COLUMN IF NOT EXISTS limitations TEXT;"
        ]

        for cmd in commands:
            await session.execute(text(cmd))

        logger.info("✅ Added extra columns to diagnostics table")

    async def _add_diagnostics_extra_columns_down(self, session: AsyncSession):
        """Rollback: drop extra columns from diagnostics table"""

        commands = [
            "ALTER TABLE diagnostics DROP COLUMN IF EXISTS strengths;",
            "ALTER TABLE diagnostics DROP COLUMN IF EXISTS contributions;",
            "ALTER TABLE diagnostics DROP COLUMN IF EXISTS limitations;"
        ]

        for cmd in commands:
            await session.execute(text(cmd))

        logger.info("↩️  Rolled back extra columns from diagnostics table")


# Utility functions for direct use

async def run_project_slug_fix():
    """
    Convenience function to run the project slug fix migration
    
    Usage:
        from app.database.migrations import run_project_slug_fix
        await run_project_slug_fix()
    """
    return await migration_manager.run_migration("001_fix_project_slug_uniqueness")


async def check_migration_needed() -> bool:
    """
    Check if the project slug migration is needed
    
    Returns:
        True if migration is needed, False otherwise
    """
    try:
        if not db_manager._initialized:
            await db_manager.initialize()
        
        async with db_manager.get_postgres_session() as session:
            # Check if the old constraint exists
            result = await session.execute(text("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE constraint_name = 'projects_slug_key' 
                AND table_name = 'projects'
            """))
            old_constraint_exists = result.scalar() > 0
            
            # Check if the new index exists
            result = await session.execute(text("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE indexname = 'ix_projects_slug_unique_active'
            """))
            new_index_exists = result.scalar() > 0
            
            # Migration is needed if old constraint exists or new index doesn't exist
            return old_constraint_exists or not new_index_exists
            
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        return True  # Assume migration is needed if we can't check

    # ================================
    # PAPER EMBEDDINGS TABLE MIGRATION
    # ================================
    
    async def _add_paper_embeddings_table_up(self, session: AsyncSession):
        """Add paper_embeddings table for semantic search functionality"""
        
        logger.info("Creating paper_embeddings table for AI-powered semantic search...")
        
        # Create the paper_embeddings table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                paper_id UUID UNIQUE REFERENCES papers(id) ON DELETE CASCADE,
                embedding vector(384), -- all-mini-lmv6 produces 384-dimensional embeddings
                source_text TEXT NOT NULL, -- concatenated diagnostics text used for embedding
                model_name TEXT DEFAULT 'all-mini-lmv6' NOT NULL,
                model_version TEXT,
                embedding_metadata JSONB, -- additional metadata about embedding generation
                processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
                error_message TEXT, -- store error details if processing fails
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                
                -- Constraints
                CONSTRAINT valid_embedding_dimension CHECK (vector_dims(embedding) = 384),
                CONSTRAINT source_text_not_empty CHECK (length(trim(source_text)) > 0)
            );
        """))
        
        # Create indexes for performance
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_paper_embeddings_paper_id ON paper_embeddings(paper_id);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_paper_embeddings_status ON paper_embeddings(processing_status);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_paper_embeddings_model ON paper_embeddings(model_name);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_paper_embeddings_created_at ON paper_embeddings(created_at);
        """))
        
        # Create vector similarity search index (for semantic search)
        # Note: This requires the vector extension to be installed
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_paper_embeddings_vector 
            ON paper_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """))
        
        # Create trigger for auto-updating updated_at timestamp
        await session.execute(text("""
            CREATE TRIGGER IF NOT EXISTS update_paper_embeddings_updated_at 
            BEFORE UPDATE ON paper_embeddings
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """))
        
        logger.info("✅ Paper embeddings table created successfully with semantic search indexes")
    
    async def _add_paper_embeddings_table_down(self, session: AsyncSession):
        """Remove paper_embeddings table and related objects"""
        
        logger.info("Removing paper_embeddings table and related objects...")
        
        # Drop trigger first
        await session.execute(text("""
            DROP TRIGGER IF EXISTS update_paper_embeddings_updated_at ON paper_embeddings;
        """))
        
        # Drop indexes
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_paper_embeddings_vector;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_paper_embeddings_created_at;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_paper_embeddings_model;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_paper_embeddings_status;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_paper_embeddings_paper_id;
        """))
        
        # Drop the table
        await session.execute(text("""
            DROP TABLE IF EXISTS paper_embeddings;
        """))
        
        logger.info("✅ Paper embeddings table and related objects removed successfully")
    
    async def _add_user_saved_searches_table_up(self, session: AsyncSession):
        """Add user_saved_searches table for search functionality"""
        logger.info("Creating user_saved_searches table...")
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_saved_searches (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                filters JSONB,
                notifications BOOLEAN DEFAULT FALSE,
                last_run TIMESTAMPTZ,
                result_count INTEGER,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                
                CONSTRAINT user_saved_searches_name_unique UNIQUE (user_id, name)
            );
        """))
        
        # Create indexes
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_saved_searches_user_id 
            ON user_saved_searches(user_id);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_saved_searches_name 
            ON user_saved_searches(name);
        """))
        
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_saved_searches_created_at 
            ON user_saved_searches(created_at);
        """))
        
        # Create trigger for updated_at
        await session.execute(text("""
            CREATE TRIGGER update_user_saved_searches_updated_at 
            BEFORE UPDATE ON user_saved_searches
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """))
        
        logger.info("User saved searches table created successfully")
    
    async def _add_user_saved_searches_table_down(self, session: AsyncSession):
        """Drop user_saved_searches table"""
        logger.info("Dropping user_saved_searches table...")
        
        await session.execute(text("""
            DROP TRIGGER IF EXISTS update_user_saved_searches_updated_at ON user_saved_searches;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_user_saved_searches_created_at;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_user_saved_searches_name;
        """))
        
        await session.execute(text("""
            DROP INDEX IF EXISTS idx_user_saved_searches_user_id;
        """))
        
        await session.execute(text("""
            DROP TABLE IF EXISTS user_saved_searches;
        """))
        
        logger.info("User saved searches table dropped successfully")


# Global migration manager instance (must be at end after all methods are defined)
migration_manager = MigrationManager() 