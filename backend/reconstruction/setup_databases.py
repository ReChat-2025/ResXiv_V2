#!/usr/bin/env python3
"""
ResXiv Database Setup Script
============================

This script creates all necessary tables in PostgreSQL and collections in MongoDB
for the ResXiv academic collaboration platform.

Requirements:
- psycopg2-binary
- pymongo
- python-dotenv

Usage:
    python setup_databases.py [--drop-existing] [--config-file .env]
"""

import os
import sys
import logging
import argparse
from typing import Optional
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    import pymongo
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install psycopg2-binary pymongo python-dotenv")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self, config_file: str = ".env"):
        """Initialize database setup with configuration."""
        # Try to load from .env file
        if Path(config_file).exists():
            load_dotenv(config_file)
            logger.info(f"Loaded configuration from {config_file}")
        else:
            logger.info(f"Config file {config_file} not found, using environment variables or defaults")
        
        # PostgreSQL configuration
        self.pg_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres'),
            'database': os.getenv('DB_NAME', 'resxiv')
        }
        
        # MongoDB configuration
        self.mongo_config = {
            'host': os.getenv('MONGO_HOST', 'localhost'),
            'port': int(os.getenv('MONGO_PORT', '27017')),
            'database': os.getenv('MONGO_DB_NAME', 'resxiv_chat'),
            'username': os.getenv('MONGO_USERNAME'),
            'password': os.getenv('MONGO_PASSWORD')
        }
        
        logger.info(f"PostgreSQL config: {self.pg_config['user']}@{self.pg_config['host']}:{self.pg_config['port']}/{self.pg_config['database']}")
        logger.info(f"MongoDB config: {self.mongo_config['host']}:{self.mongo_config['port']}/{self.mongo_config['database']}")
        
        self.pg_conn = None
        self.mongo_client = None
        self.mongo_db = None

    def connect_postgres(self) -> bool:
        """Connect to PostgreSQL server."""
        try:
            # First connect to default database to create ResXiv database
            temp_config = self.pg_config.copy()
            temp_config['database'] = 'postgres'
            
            self.pg_conn = psycopg2.connect(**temp_config)
            self.pg_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info("Connected to PostgreSQL server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def connect_mongodb(self) -> bool:
        """Connect to MongoDB server."""
        try:
            # Build MongoDB URI
            if self.mongo_config['username'] and self.mongo_config['password']:
                uri = f"mongodb://{self.mongo_config['username']}:{self.mongo_config['password']}@{self.mongo_config['host']}:{self.mongo_config['port']}"
            else:
                uri = f"mongodb://{self.mongo_config['host']}:{self.mongo_config['port']}"
            
            self.mongo_client = pymongo.MongoClient(uri)
            self.mongo_db = self.mongo_client[self.mongo_config['database']]
            
            # Test connection
            self.mongo_client.admin.command('ping')
            logger.info("Connected to MongoDB server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False

    def create_postgres_database(self, drop_existing: bool = False) -> bool:
        """Create PostgreSQL database and extensions."""
        try:
            cursor = self.pg_conn.cursor()
            
            if drop_existing:
                # Terminate existing connections to the database
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{self.pg_config['database']}'
                      AND pid <> pg_backend_pid()
                """)
                cursor.execute(f"DROP DATABASE IF EXISTS {self.pg_config['database']}")
                logger.info(f"Dropped existing database: {self.pg_config['database']}")
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.pg_config['database']}'")
            db_exists = cursor.fetchone() is not None
            
            if not db_exists:
                # Create database
                cursor.execute(f"CREATE DATABASE {self.pg_config['database']}")
                logger.info(f"Created database: {self.pg_config['database']}")
            else:
                logger.info(f"Database {self.pg_config['database']} already exists - proceeding with table creation")
            
            # Connect to the target database
            cursor.close()
            self.pg_conn.close()
            
            self.pg_conn = psycopg2.connect(**self.pg_config)
            self.pg_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = self.pg_conn.cursor()
            
            # Create extensions
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                logger.info("Created/verified pgcrypto extension")
            except Exception as e:
                logger.warning(f"Could not create pgcrypto extension: {e}")
            
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                logger.info("Created/verified vector extension")
            except Exception as e:
                logger.warning(f"Could not create vector extension (install postgresql-16-vector): {e}")
                logger.info("Continuing without vector - vector search will not be available")
            
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL database: {e}")
            return False

    def create_postgres_enums(self) -> bool:
        """Create ENUM types for PostgreSQL."""
        try:
            cursor = self.pg_conn.cursor()
            
            enums = [
                "CREATE TYPE project_role AS ENUM ('owner', 'admin', 'writer', 'reader')",
                "CREATE TYPE conversation_type AS ENUM ('AI', 'GROUP', 'PDF', 'DROP', 'AGENTIC')",
                "CREATE TYPE permission_type AS ENUM ('read', 'write', 'admin')",
                "CREATE TYPE message_type AS ENUM ('text', 'file', 'image', 'system')"
            ]
            
            for enum_sql in enums:
                try:
                    cursor.execute(enum_sql)
                    logger.info(f"Created enum: {enum_sql.split()[2]}")
                except psycopg2.errors.DuplicateObject:
                    logger.info(f"Enum already exists: {enum_sql.split()[2]}")
            
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Failed to create enums: {e}")
            return False

    def create_postgres_tables(self) -> bool:
        """Create all PostgreSQL tables."""
        tables_sql = [
            # USERS
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'),
                password TEXT NOT NULL,
                public_key TEXT,
                email_verified BOOLEAN DEFAULT FALSE,
                accepted_terms BOOLEAN DEFAULT FALSE,
                interests TEXT[],
                intro TEXT DEFAULT 'Fill in your information',
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                last_login TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ
            )
            """,
            
            # EMAIL VERIFICATION TOKENS
            """
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                email TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                verified_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # PASSWORD RESET TOKENS
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # USER SESSIONS
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                last_used_at TIMESTAMPTZ DEFAULT now(),
                user_agent TEXT,
                ip_address INET
            )
            """,
            
            # CONVERSATIONS
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                type conversation_type NOT NULL,
                entity UUID,
                is_group BOOLEAN DEFAULT FALSE,
                created_by UUID REFERENCES users(id) ON DELETE SET NULL,
                group_key_encrypted JSONB,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # PROJECTS
            """
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                slug TEXT UNIQUE,
                description TEXT,
                conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
                repo_url TEXT,
                created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                deleted_at TIMESTAMPTZ
            )
            """,
            
            # GRAPHS (knowledge graphs for projects)
            """
            CREATE TABLE IF NOT EXISTS graphs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                graph_path TEXT NOT NULL,
                graph_type TEXT DEFAULT 'knowledge_graph',
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT unique_project_graph UNIQUE (project_id)
            )
            """,
            
            # PROJECT MEMBERS
            """
            CREATE TABLE IF NOT EXISTS project_members (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                role project_role NOT NULL DEFAULT 'reader',
                added_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT unique_user_project UNIQUE (user_id, project_id)
            )
            """,
            
            # PROJECT COLLABORATORS
            """
            CREATE TABLE IF NOT EXISTS project_collaborators (
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                permission permission_type NOT NULL,
                added_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (project_id, user_id)
            )
            """,
            
            # PROJECT INVITATIONS
            """
            CREATE TABLE IF NOT EXISTS project_invitations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
                email TEXT NOT NULL,
                role project_role NOT NULL DEFAULT 'reader',
                permission permission_type,
                invitation_token TEXT NOT NULL UNIQUE,
                message TEXT,
                expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
                accepted_at TIMESTAMPTZ,
                accepted_by UUID REFERENCES users(id) ON DELETE SET NULL,
                declined_at TIMESTAMPTZ,
                cancelled_at TIMESTAMPTZ,
                cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT check_invitation_state CHECK (
                    (accepted_at IS NULL AND declined_at IS NULL AND cancelled_at IS NULL) OR
                    (accepted_at IS NOT NULL AND declined_at IS NULL AND cancelled_at IS NULL) OR
                    (accepted_at IS NULL AND declined_at IS NOT NULL AND cancelled_at IS NULL) OR
                    (accepted_at IS NULL AND declined_at IS NULL AND cancelled_at IS NOT NULL)
                )
            )
            """,
            
            # INVITATION REMINDERS
            """
            CREATE TABLE IF NOT EXISTS invitation_reminders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                invitation_id UUID REFERENCES project_invitations(id) ON DELETE CASCADE,
                sent_at TIMESTAMPTZ DEFAULT now(),
                reminder_count INTEGER DEFAULT 1
            )
            """,
            
            # PAPERS
            """
            CREATE TABLE IF NOT EXISTS papers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                date_added TIMESTAMPTZ DEFAULT now(),
                last_modified TIMESTAMPTZ DEFAULT now(),
                pdf_path TEXT,
                bib_path TEXT,
                file_size BIGINT,
                mime_type TEXT,
                checksum TEXT,
                private_uploaded BOOLEAN DEFAULT FALSE,
                authors TEXT[],
                keywords TEXT[],
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                deleted_at TIMESTAMPTZ
            )
            """,
            
            # PROJECT PAPERS
            """
            CREATE TABLE IF NOT EXISTS project_papers (
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
                uploaded BOOLEAN DEFAULT TRUE,
                added_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (project_id, paper_id)
            )
            """,
            
            # DIAGNOSTICS
            """
            CREATE TABLE IF NOT EXISTS diagnostics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                paper_id UUID UNIQUE REFERENCES papers(id) ON DELETE CASCADE,
                abstract TEXT,
                summary TEXT,
                method TEXT,
                dataset TEXT,
                highlights TEXT,
                weakness TEXT,
                future_scope TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # HIGHLIGHTS
            """
            CREATE TABLE IF NOT EXISTS highlights (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                start_pos INTEGER[2],
                end_pos INTEGER[2],
                content TEXT,
                color TEXT DEFAULT '#ffff00',
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # NOTES
            """
            CREATE TABLE IF NOT EXISTS notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                text TEXT NOT NULL,
                position INTEGER[2],
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # LATEX COMMITS
            """
            CREATE TABLE IF NOT EXISTS latex_commits (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                commit_hash TEXT NOT NULL,
                message TEXT,
                parent_commit TEXT,
                branch TEXT DEFAULT 'main',
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # LATEX COMMENTS
            """
            CREATE TABLE IF NOT EXISTS latex_comments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                commit_hash TEXT NOT NULL,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                content TEXT NOT NULL,
                line_number INTEGER,
                file_path TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # LATEX SNAPSHOTS
            """
            CREATE TABLE IF NOT EXISTS latex_snapshots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                commit_hash TEXT NOT NULL,
                label TEXT NOT NULL,
                description TEXT,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # LATEX CONFLICTS
            """
            CREATE TABLE IF NOT EXISTS latex_conflicts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                base_commit TEXT NOT NULL,
                target_commit TEXT NOT NULL,
                conflict_file TEXT NOT NULL,
                conflict_section TEXT,
                resolution TEXT,
                resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                resolved_at TIMESTAMPTZ,
                resolved BOOLEAN DEFAULT FALSE
            )
            """,
            
            # FILE UPLOADS
            """
            CREATE TABLE IF NOT EXISTS file_uploads (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size BIGINT,
                mime_type TEXT,
                checksum TEXT,
                uploaded_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # SYSTEM SETTINGS
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL,
                description TEXT,
                updated_at TIMESTAMPTZ DEFAULT now(),
                updated_by UUID REFERENCES users(id) ON DELETE SET NULL
            )
            """,
            
            # AUDIT LOG
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id UUID,
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # USER TAGS
            """
            CREATE TABLE IF NOT EXISTS user_tags (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#808080',
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT unique_user_tag_name UNIQUE (user_id, name)
            )
            """,
            
            # USER PAPER TAGS
            """
            CREATE TABLE IF NOT EXISTS user_paper_tags (
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
                tag_id UUID REFERENCES user_tags(id) ON DELETE CASCADE,
                tagged_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (user_id, paper_id, tag_id),
                CONSTRAINT fk_user_paper_tags_user_tag 
                FOREIGN KEY (tag_id) REFERENCES user_tags(id) 
                DEFERRABLE INITIALLY DEFERRED
            )
            """,
            
            # USER PROJECT TAGS
            """
            CREATE TABLE IF NOT EXISTS user_project_tags (
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                tag_id UUID REFERENCES user_tags(id) ON DELETE CASCADE,
                tagged_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (user_id, project_id, tag_id),
                CONSTRAINT fk_user_project_tags_user_tag 
                FOREIGN KEY (tag_id) REFERENCES user_tags(id) 
                DEFERRABLE INITIALLY DEFERRED
            )
            """,
            
            # ANALYTICS TABLES
            """
            CREATE TABLE IF NOT EXISTS user_feature_usage (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                feature_name TEXT NOT NULL,
                feature_category TEXT NOT NULL,
                session_id UUID,
                metadata JSONB,
                duration_seconds INTEGER,
                success BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS user_engagement_daily (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                total_sessions INTEGER DEFAULT 0,
                total_time_minutes INTEGER DEFAULT 0,
                features_used TEXT[],
                papers_interacted INTEGER DEFAULT 0,
                highlights_created INTEGER DEFAULT 0,
                notes_created INTEGER DEFAULT 0,
                chat_messages_sent INTEGER DEFAULT 0,
                ai_interactions INTEGER DEFAULT 0,
                latex_commits INTEGER DEFAULT 0,
                login_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT unique_user_date UNIQUE (user_id, date)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS feature_analytics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                feature_name TEXT NOT NULL,
                feature_category TEXT NOT NULL,
                date DATE NOT NULL,
                total_uses INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                avg_duration_seconds NUMERIC,
                success_rate NUMERIC,
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT unique_feature_date UNIQUE (feature_name, date)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS user_behavior_patterns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                pattern_type TEXT NOT NULL,
                pattern_data JSONB NOT NULL,
                confidence_score NUMERIC(3,2),
                last_updated TIMESTAMPTZ DEFAULT now(),
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS user_sessions_detailed (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                session_token UUID NOT NULL,
                start_time TIMESTAMPTZ DEFAULT now(),
                end_time TIMESTAMPTZ,
                duration_minutes INTEGER,
                pages_visited TEXT[],
                features_used TEXT[],
                projects_accessed UUID[],
                papers_accessed UUID[],
                device_type TEXT,
                browser TEXT,
                ip_address INET,
                referrer TEXT,
                exit_page TEXT
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS ab_test_participants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                test_name TEXT NOT NULL,
                variant TEXT NOT NULL,
                assigned_at TIMESTAMPTZ DEFAULT now(),
                converted BOOLEAN DEFAULT FALSE,
                conversion_date TIMESTAMPTZ,
                CONSTRAINT unique_user_test UNIQUE (user_id, test_name)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                metric_name TEXT NOT NULL,
                metric_category TEXT NOT NULL,
                value NUMERIC NOT NULL,
                unit TEXT NOT NULL,
                metadata JSONB,
                recorded_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            # TASK MANAGEMENT TABLES
            """
            CREATE TABLE IF NOT EXISTS task_lists (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#3498db',
                position INTEGER DEFAULT 0,
                created_by UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                task_list_id UUID REFERENCES task_lists(id) ON DELETE SET NULL,
                parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'cancelled')),
                priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                due_date TIMESTAMPTZ,
                start_date TIMESTAMPTZ,
                estimated_hours DECIMAL(5,2),
                actual_hours DECIMAL(5,2),
                progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
                created_by UUID REFERENCES users(id) ON DELETE SET NULL,
                assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
                position INTEGER DEFAULT 0,
                is_milestone BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                completed_at TIMESTAMPTZ,
                deleted_at TIMESTAMPTZ
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_assignees (
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                assigned_by UUID REFERENCES users(id) ON DELETE SET NULL,
                assigned_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (task_id, user_id)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_dependencies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                predecessor_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                successor_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                dependency_type TEXT DEFAULT 'finish_to_start' CHECK (dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish')),
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT no_self_dependency CHECK (predecessor_task_id != successor_task_id),
                CONSTRAINT unique_dependency UNIQUE (predecessor_task_id, successor_task_id)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_comments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                content TEXT NOT NULL,
                reply_to UUID REFERENCES task_comments(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                deleted_at TIMESTAMPTZ
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_attachments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                file_id UUID REFERENCES file_uploads(id) ON DELETE CASCADE,
                paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
                attached_by UUID REFERENCES users(id) ON DELETE SET NULL,
                attached_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT attachment_type_check CHECK (
                    (file_id IS NOT NULL AND paper_id IS NULL) OR 
                    (file_id IS NULL AND paper_id IS NOT NULL)
                )
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_time_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                description TEXT,
                hours DECIMAL(5,2) NOT NULL CHECK (hours > 0),
                log_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                tag_id UUID REFERENCES user_tags(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                tagged_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (task_id, tag_id, user_id)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_activity (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                field_changed TEXT,
                old_value TEXT,
                new_value TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_watchers (
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                watched_at TIMESTAMPTZ DEFAULT now(),
                PRIMARY KEY (task_id, user_id)
            )
            """,
            
            """
            CREATE TABLE IF NOT EXISTS task_recurrence (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                recurrence_type TEXT NOT NULL CHECK (recurrence_type IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')),
                recurrence_interval INTEGER DEFAULT 1,
                days_of_week INTEGER[],
                day_of_month INTEGER,
                end_date TIMESTAMPTZ,
                max_occurrences INTEGER,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        ]
        
        try:
            cursor = self.pg_conn.cursor()
            
            for i, table_sql in enumerate(tables_sql, 1):
                try:
                    cursor.execute(table_sql)
                    table_name = table_sql.split("CREATE TABLE IF NOT EXISTS ")[1].split(" (")[0]
                    logger.info(f"Created table {i}/{len(tables_sql)}: {table_name}")
                except Exception as e:
                    logger.error(f"Failed to create table {i}: {e}")
                    return False
            
            cursor.close()
            logger.info("All PostgreSQL tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            return False

    def create_postgres_indexes(self) -> bool:
        """Create all PostgreSQL indexes."""
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by)",
            "CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug)",
            "CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_projects_deleted_at ON projects(deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON project_members(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON project_members(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_members_role ON project_members(role)",
            "CREATE INDEX IF NOT EXISTS idx_project_collaborators_user_id ON project_collaborators(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_collaborators_project_id ON project_collaborators(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_project_id ON project_invitations(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_email ON project_invitations(email)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_token ON project_invitations(invitation_token)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_invited_by ON project_invitations(invited_by)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_expires_at ON project_invitations(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_created_at ON project_invitations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_project_invitations_pending ON project_invitations(project_id, email)",
            "CREATE INDEX IF NOT EXISTS idx_invitation_reminders_invitation_id ON invitation_reminders(invitation_id)",
            "CREATE INDEX IF NOT EXISTS idx_invitation_reminders_sent_at ON invitation_reminders(sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)",
            "CREATE INDEX IF NOT EXISTS idx_papers_authors ON papers USING GIN(authors)",
            "CREATE INDEX IF NOT EXISTS idx_papers_keywords ON papers USING GIN(keywords)",
            "CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_papers_deleted_at ON papers(deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_type ON conversations(type)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_by ON conversations(created_by)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_graphs_project_id ON graphs(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_graphs_graph_type ON graphs(graph_type)",
            "CREATE INDEX IF NOT EXISTS idx_graphs_created_at ON graphs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_diagnostics_paper_id ON diagnostics(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_highlights_user_id ON highlights(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_highlights_paper_id ON highlights(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_highlights_project_id ON highlights(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_highlights_created_at ON highlights(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_notes_paper_id ON notes(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_notes_project_id ON notes(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_latex_commits_project_id ON latex_commits(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_latex_commits_user_id ON latex_commits(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_latex_commits_created_at ON latex_commits(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_latex_comments_project_id ON latex_comments(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_latex_comments_commit_hash ON latex_comments(commit_hash)",
            "CREATE INDEX IF NOT EXISTS idx_latex_comments_user_id ON latex_comments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_latex_snapshots_project_id ON latex_snapshots(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_latex_conflicts_project_id ON latex_conflicts(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token)",
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_token ON email_verification_tokens(token)",
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires_at ON email_verification_tokens(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_active ON email_verification_tokens(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions(token_hash)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type_id ON audit_log(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON user_tags(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_tags_name ON user_tags(name)",
            "CREATE INDEX IF NOT EXISTS idx_user_paper_tags_user_id ON user_paper_tags(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_paper_tags_paper_id ON user_paper_tags(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_paper_tags_tag_id ON user_paper_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_project_tags_user_id ON user_project_tags(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_project_tags_project_id ON user_project_tags(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_project_tags_tag_id ON user_project_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_feature_usage_user_id ON user_feature_usage(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_feature_usage_feature_name ON user_feature_usage(feature_name)",
            "CREATE INDEX IF NOT EXISTS idx_user_feature_usage_created_at ON user_feature_usage(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_user_feature_usage_session_id ON user_feature_usage(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_engagement_daily_user_id ON user_engagement_daily(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_engagement_daily_date ON user_engagement_daily(date)",
            "CREATE INDEX IF NOT EXISTS idx_feature_analytics_feature_name ON feature_analytics(feature_name)",
            "CREATE INDEX IF NOT EXISTS idx_feature_analytics_date ON feature_analytics(date)",
            "CREATE INDEX IF NOT EXISTS idx_user_behavior_patterns_user_id ON user_behavior_patterns(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_behavior_patterns_pattern_type ON user_behavior_patterns(pattern_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_detailed_user_id ON user_sessions_detailed(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_detailed_start_time ON user_sessions_detailed(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_detailed_session_token ON user_sessions_detailed(session_token)",
            "CREATE INDEX IF NOT EXISTS idx_ab_test_participants_user_id ON ab_test_participants(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ab_test_participants_test_name ON ab_test_participants(test_name)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_metric_name ON performance_metrics(metric_name)",
            "CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at)",
            
            # Task management indexes
            "CREATE INDEX IF NOT EXISTS idx_task_lists_project_id ON task_lists(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_lists_position ON task_lists(position)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_task_list_id ON tasks(task_list_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON tasks(parent_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_position ON tasks(position)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_deleted_at ON tasks(deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_task_assignees_task_id ON task_assignees(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_assignees_user_id ON task_assignees(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_dependencies_predecessor ON task_dependencies(predecessor_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_dependencies_successor ON task_dependencies(successor_task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_comments_task_id ON task_comments(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_comments_user_id ON task_comments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_comments_reply_to ON task_comments(reply_to)",
            "CREATE INDEX IF NOT EXISTS idx_task_comments_created_at ON task_comments(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_task_attachments_task_id ON task_attachments(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_attachments_file_id ON task_attachments(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_attachments_paper_id ON task_attachments(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_time_logs_task_id ON task_time_logs(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_time_logs_user_id ON task_time_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_time_logs_log_date ON task_time_logs(log_date)",
            "CREATE INDEX IF NOT EXISTS idx_task_tags_task_id ON task_tags(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_tags_tag_id ON task_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_tags_user_id ON task_tags(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_activity_task_id ON task_activity(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_activity_user_id ON task_activity(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_activity_created_at ON task_activity(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_task_watchers_task_id ON task_watchers(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_watchers_user_id ON task_watchers(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_recurrence_task_id ON task_recurrence(task_id)"
        ]
        
        try:
            cursor = self.pg_conn.cursor()
            
            for i, index_sql in enumerate(indexes_sql, 1):
                try:
                    cursor.execute(index_sql)
                    index_name = index_sql.split("CREATE INDEX IF NOT EXISTS ")[1].split(" ON ")[0]
                    if i % 10 == 0:  # Log every 10th index to avoid spam
                        logger.info(f"Created indexes: {i}/{len(indexes_sql)}")
                except Exception as e:
                    logger.warning(f"Failed to create index {i}: {e}")
            
            cursor.close()
            logger.info("All PostgreSQL indexes created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL indexes: {e}")
            return False

    def create_postgres_functions(self) -> bool:
        """Create PostgreSQL functions and triggers."""
        functions_sql = [
            # Update trigger function
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ language 'plpgsql'
            """,
            
            # Feature usage tracking function
            """
            CREATE OR REPLACE FUNCTION track_feature_usage(
                p_user_id UUID,
                p_feature_name TEXT,
                p_feature_category TEXT,
                p_session_id UUID DEFAULT NULL,
                p_metadata JSONB DEFAULT NULL,
                p_duration_seconds INTEGER DEFAULT NULL,
                p_success BOOLEAN DEFAULT TRUE
            ) RETURNS VOID AS $$
            BEGIN
                INSERT INTO user_feature_usage (
                    user_id, feature_name, feature_category, session_id, 
                    metadata, duration_seconds, success
                ) VALUES (
                    p_user_id, p_feature_name, p_feature_category, p_session_id,
                    p_metadata, p_duration_seconds, p_success
                );
                
                INSERT INTO user_engagement_daily (user_id, date, features_used)
                VALUES (p_user_id, CURRENT_DATE, ARRAY[p_feature_name])
                ON CONFLICT (user_id, date) 
                DO UPDATE SET 
                    features_used = array_append(
                        CASE WHEN p_feature_name = ANY(user_engagement_daily.features_used) 
                             THEN user_engagement_daily.features_used
                             ELSE user_engagement_daily.features_used 
                        END, 
                        CASE WHEN p_feature_name = ANY(user_engagement_daily.features_used)
                             THEN NULL
                             ELSE p_feature_name
                        END
                    );
            END;
            $$ LANGUAGE plpgsql
            """,
            
            # Project invitation function
            """
            CREATE OR REPLACE FUNCTION create_project_invitation(
                p_project_id UUID,
                p_invited_by UUID,
                p_email TEXT,
                p_role project_role DEFAULT 'reader',
                p_permission permission_type DEFAULT NULL,
                p_message TEXT DEFAULT NULL,
                p_expires_days INTEGER DEFAULT 7
            ) RETURNS UUID AS $$
            DECLARE
                v_invitation_id UUID;
                v_token TEXT;
            BEGIN
                v_token := encode(gen_random_bytes(32), 'base64url');
                
                IF EXISTS (
                    SELECT 1 FROM project_invitations 
                    WHERE project_id = p_project_id 
                      AND email = p_email 
                      AND accepted_at IS NULL 
                      AND declined_at IS NULL 
                      AND cancelled_at IS NULL 
                      AND expires_at > now()
                ) THEN
                    RAISE EXCEPTION 'Active invitation already exists for this email and project';
                END IF;
                
                INSERT INTO project_invitations (
                    project_id, invited_by, email, role, permission, 
                    invitation_token, message, expires_at
                ) VALUES (
                    p_project_id, p_invited_by, p_email, p_role, p_permission,
                    v_token, p_message, now() + (p_expires_days || ' days')::INTERVAL
                ) RETURNING id INTO v_invitation_id;
                
                RETURN v_invitation_id;
            END;
            $$ LANGUAGE plpgsql
            """,
            
            # Accept invitation function
            """
            CREATE OR REPLACE FUNCTION accept_project_invitation(
                p_invitation_token TEXT,
                p_user_id UUID
            ) RETURNS BOOLEAN AS $$
            DECLARE
                v_invitation RECORD;
                v_user_email TEXT;
            BEGIN
                SELECT email INTO v_user_email FROM users WHERE id = p_user_id;
                
                SELECT * INTO v_invitation 
                FROM project_invitations 
                WHERE invitation_token = p_invitation_token
                  AND expires_at > now()
                  AND accepted_at IS NULL 
                  AND declined_at IS NULL 
                  AND cancelled_at IS NULL;
                
                IF NOT FOUND THEN
                    RETURN FALSE;
                END IF;
                
                UPDATE project_invitations 
                SET accepted_at = now(), accepted_by = p_user_id
                WHERE id = v_invitation.id;
                
                INSERT INTO project_members (user_id, project_id, role)
                VALUES (p_user_id, v_invitation.project_id, v_invitation.role)
                ON CONFLICT (user_id, project_id) DO NOTHING;
                
                IF v_invitation.permission IS NOT NULL THEN
                    INSERT INTO project_collaborators (user_id, project_id, permission)
                    VALUES (p_user_id, v_invitation.project_id, v_invitation.permission)
                    ON CONFLICT (project_id, user_id) DO NOTHING;
                END IF;
                
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql
            """
        ]
        
        # Triggers
        triggers_sql = [
            "CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_papers_updated_at BEFORE UPDATE ON papers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_graphs_updated_at BEFORE UPDATE ON graphs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_diagnostics_updated_at BEFORE UPDATE ON diagnostics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_highlights_updated_at BEFORE UPDATE ON highlights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_latex_comments_updated_at BEFORE UPDATE ON latex_comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_task_lists_updated_at BEFORE UPDATE ON task_lists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_task_comments_updated_at BEFORE UPDATE ON task_comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()",
            "CREATE TRIGGER update_task_time_logs_updated_at BEFORE UPDATE ON task_time_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()"
        ]
        
        try:
            cursor = self.pg_conn.cursor()
            
            # Create functions
            for i, function_sql in enumerate(functions_sql, 1):
                try:
                    cursor.execute(function_sql)
                    logger.info(f"Created function {i}/{len(functions_sql)}")
                except Exception as e:
                    logger.error(f"Failed to create function {i}: {e}")
                    return False
            
            # Create triggers
            for i, trigger_sql in enumerate(triggers_sql, 1):
                try:
                    cursor.execute(trigger_sql)
                    if i % 3 == 0:  # Log every 3rd trigger
                        logger.info(f"Created triggers: {i}/{len(triggers_sql)}")
                except psycopg2.errors.DuplicateObject:
                    # Trigger already exists, skip silently
                    if i % 3 == 0:  # Log every 3rd trigger
                        logger.info(f"Verified triggers: {i}/{len(triggers_sql)} (some already existed)")
                except Exception as e:
                    logger.warning(f"Failed to create trigger {i}: {e}")
            
            cursor.close()
            logger.info("All PostgreSQL functions and triggers created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL functions: {e}")
            return False

    def create_mongodb_collections(self, drop_existing: bool = False) -> bool:
        """Create MongoDB collections and indexes."""
        try:
            if drop_existing:
                # Drop existing collections
                for collection_name in self.mongo_db.list_collection_names():
                    self.mongo_db.drop_collection(collection_name)
                    logger.info(f"Dropped existing collection: {collection_name}")
            
            # Create collections
            collections = ['messages', 'conversation_metadata']
            
            for collection_name in collections:
                if collection_name not in self.mongo_db.list_collection_names():
                    self.mongo_db.create_collection(collection_name)
                    logger.info(f"Created collection: {collection_name}")
            
            # Create indexes for messages collection
            messages = self.mongo_db.messages
            message_indexes = [
                [("conversation_id", 1), ("timestamp", 1)],
                [("sender_id", 1), ("timestamp", -1)],
                [("conversation_id", 1), ("message_type", 1)],
                [("metadata.paper_id", 1)],
                [("metadata.mention_users", 1)],
                [("created_at", 1)]
            ]
            
            for index_spec in message_indexes:
                try:
                    messages.create_index(index_spec)
                    logger.info(f"Created index on messages: {index_spec}")
                except Exception as e:
                    logger.warning(f"Failed to create index {index_spec}: {e}")
            
            # Create indexes for conversation_metadata collection
            metadata = self.mongo_db.conversation_metadata
            metadata_indexes = [
                [("updated_at", -1)],
                [("unread_counts", 1)]
            ]
            
            for index_spec in metadata_indexes:
                try:
                    metadata.create_index(index_spec)
                    logger.info(f"Created index on conversation_metadata: {index_spec}")
                except Exception as e:
                    logger.warning(f"Failed to create index {index_spec}: {e}")
            
            logger.info("MongoDB collections and indexes created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create MongoDB collections: {e}")
            return False

    def verify_setup(self) -> bool:
        """Verify that all databases and collections are set up correctly."""
        try:
            # Verify PostgreSQL
            cursor = self.pg_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
            logger.info(f"PostgreSQL verification: {table_count} tables created")
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public'")
            function_count = cursor.fetchone()[0]
            logger.info(f"PostgreSQL verification: {function_count} functions created")
            
            cursor.close()
            
            # Verify MongoDB
            collection_count = len(self.mongo_db.list_collection_names())
            logger.info(f"MongoDB verification: {collection_count} collections created")
            
            return table_count > 0 and collection_count > 0
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

    def close_connections(self):
        """Close database connections."""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("PostgreSQL connection closed")
        
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    def setup_all(self, drop_existing: bool = False) -> bool:
        """Run complete database setup."""
        logger.info("Starting ResXiv database setup...")
        
        # Connect to databases
        if not self.connect_postgres():
            return False
        
        if not self.connect_mongodb():
            return False
        
        # Setup PostgreSQL
        if not self.create_postgres_database(drop_existing):
            return False
        
        if not self.create_postgres_enums():
            return False
        
        if not self.create_postgres_tables():
            return False
        
        if not self.create_postgres_indexes():
            return False
        
        if not self.create_postgres_functions():
            return False
        
        # Setup MongoDB
        if not self.create_mongodb_collections(drop_existing):
            return False
        
        # Verify setup
        if not self.verify_setup():
            return False
        
        logger.info("✅ ResXiv database setup completed successfully!")
        return True


def main():
    """Main function to run database setup."""
    parser = argparse.ArgumentParser(description="Set up ResXiv databases")
    parser.add_argument(
        "--drop-existing", 
        action="store_true", 
        help="Drop existing databases before creating new ones"
    )
    parser.add_argument(
        "--config-file", 
        default=".env", 
        help="Path to environment configuration file"
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config_file).exists():
        logger.warning(f"Config file {args.config_file} not found. Using environment variables or defaults.")
    
    # Initialize and run setup
    setup = DatabaseSetup(args.config_file)
    
    try:
        success = setup.setup_all(args.drop_existing)
        if success:
            logger.info("Database setup completed successfully!")
            sys.exit(0)
        else:
            logger.error("Database setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during setup: {e}")
        sys.exit(1)
    finally:
        setup.close_connections()


if __name__ == "__main__":
    main() 