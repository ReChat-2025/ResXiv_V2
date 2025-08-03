# ResXiv Database Setup

This directory contains scripts to set up the complete ResXiv database schema with PostgreSQL and MongoDB.

## Recent Updates ✅

**All warnings and errors have been resolved!** The setup now runs cleanly with:
- ✅ Fixed SyntaxWarning for email regex escape sequence  
- ✅ Corrected vector extension name (was `pgvector`, now `vector`)
- ✅ Graceful handling of existing database triggers
- ✅ Improved logging and status messages

## Features Added

✅ **Complete Academic Platform Database Schema**
- User management with authentication & sessions
- Project collaboration with roles & permissions  
- Paper management with annotations (highlights, notes)
- LaTeX version control (commits, comments, snapshots, conflicts)
- **NEW: Asana-like Task Management System**
  - Task lists, tasks with subtasks
  - Multiple assignees, dependencies, time tracking
  - Comments, attachments (files & papers)
  - Activity logging, watchers, recurring tasks
- Real-time chat system (MongoDB)
- External project invitations via email
- Analytics & feature usage tracking
- File management & audit logging

## Prerequisites

1. **PostgreSQL 16** (or compatible version)
2. **MongoDB** (any recent version)
3. **Python 3.8+** with pip

## Quick Setup

### Step 1: Install Dependencies

**Option A: Automatic Installation (Recommended)**
```bash
# Install all PostgreSQL extensions and Python dependencies
bash install_postgres_deps.sh
```

**Option B: Manual Installation**
```bash
# Install PostgreSQL extensions
sudo apt update
sudo apt install -y postgresql-16-contrib postgresql-16-pgvector

# Install Python dependencies  
pip install psycopg2-binary pymongo python-dotenv

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp env_example.txt .env

# Edit with your database credentials
nano .env
```

### Step 3: Create Database

```bash
# Create fresh database (drops existing if present)
python setup_databases.py --drop-existing

# Or update existing database
python setup_databases.py
```

## Configuration

Edit `.env` file with your settings:

```env
# PostgreSQL Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=resxiv
DB_USER=postgres
DB_PASSWORD=your_password

# MongoDB Configuration  
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB_NAME=resxiv_chat
MONGO_USERNAME=
MONGO_PASSWORD=
```

## Database Schema Overview

### PostgreSQL Tables (44 total)

**Core Tables:**
- `users` - User accounts with email verification
- `projects` - Research projects with collaboration
- `papers` - Academic papers with metadata
- `conversations` - Chat conversations

**Task Management Tables (NEW):**
- `task_lists` - Organize tasks within projects
- `tasks` - Main task management with status, priority, progress
- `task_assignees` - Multiple users per task
- `task_dependencies` - Task relationships & scheduling
- `task_comments` - Discussion threads on tasks
- `task_attachments` - Link files/papers to tasks
- `task_time_logs` - Time tracking per task
- `task_tags` - User-specific task categorization
- `task_activity` - Complete audit trail
- `task_watchers` - Users following task updates
- `task_recurrence` - Recurring task patterns

**Collaboration Tables:**
- `project_members` - User roles in projects
- `project_invitations` - External email invitations
- `highlights` & `notes` - Paper annotations
- `latex_*` - Version control for LaTeX documents

**Analytics Tables:**
- `user_feature_usage` - Track feature adoption
- `user_engagement_daily` - Daily activity metrics
- `ab_test_participants` - A/B testing framework

### MongoDB Collections

- `messages` - Chat messages with reactions, replies
- `conversation_metadata` - Cached conversation stats

## Extensions & Dependencies

### PostgreSQL Extensions
- **pgcrypto** ✅ - Required for UUID generation and encryption
- **vector** ✅ - Optional for vector similarity search (was pgvector)

### Python Dependencies
- **psycopg2-binary** - PostgreSQL adapter
- **pymongo** - MongoDB driver  
- **python-dotenv** - Environment variable loading

## Verification

After setup, verify the installation:

```bash
# Check PostgreSQL tables
sudo -u postgres psql -d resxiv -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Expected: 44

# Check PostgreSQL functions  
sudo -u postgres psql -d resxiv -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public';"
# Expected: 77+

# Check extensions
sudo -u postgres psql -d resxiv -c "SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto', 'vector');"
# Expected: pgcrypto, vector

# Check MongoDB collections
python -c "from pymongo import MongoClient; client = MongoClient(); db = client.resxiv_chat; print('Collections:', db.list_collection_names())"
# Expected: ['messages', 'conversation_metadata']

# Verify task tables specifically
sudo -u postgres psql -d resxiv -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'task%' ORDER BY table_name;"
# Expected: All 11 task management tables
```

## Task Management Features

The new task management system provides Asana-like functionality:

### Core Features
- **Hierarchical Tasks**: Parent tasks with unlimited subtasks
- **Multiple Assignees**: Teams can collaborate on single tasks  
- **Task Dependencies**: Define prerequisite relationships
- **Progress Tracking**: 0-100% completion with time estimates
- **Priority Levels**: Low, Medium, High, Urgent
- **Status Workflow**: Todo → In Progress → Review → Done/Cancelled

### Advanced Features
- **Time Tracking**: Log actual hours worked per task
- **File Attachments**: Link research papers or files to tasks
- **Comments & Discussions**: Threaded conversations on tasks
- **Activity Logging**: Complete audit trail of all changes
- **Watchers**: Users can follow task updates
- **Recurring Tasks**: Daily, weekly, monthly, quarterly patterns
- **Milestones**: Mark important project checkpoints

### Integration Features
- **Paper Integration**: Attach research papers directly to tasks
- **Project Integration**: Tasks inherit project permissions
- **User Tags**: Personal organization system
- **Analytics**: Track task completion rates and user productivity

## Troubleshooting

### Recently Fixed Issues ✅

**1. SyntaxWarning: invalid escape sequence**
- **Issue**: Python regex pattern had unescaped backslash
- **Fix**: Updated email regex pattern in user table
- **Status**: ✅ Resolved

**2. pgvector extension not found**
- **Issue**: Extension name was incorrect (`pgvector` vs `vector`)
- **Fix**: Updated setup script to use correct extension name
- **Status**: ✅ Resolved

**3. Trigger creation warnings**
- **Issue**: Warnings about existing triggers
- **Fix**: Added graceful handling of duplicate triggers
- **Status**: ✅ Resolved

### Common Issues & Solutions

#### Extension Installation
```bash
# Verify vector extension is available
sudo -u postgres psql -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"

# If not available, install pgvector package
sudo apt install postgresql-16-pgvector

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### Permission Issues
```bash
# Ensure PostgreSQL service is running
sudo systemctl status postgresql
sudo systemctl start postgresql

# Check PostgreSQL user permissions
sudo -u postgres createdb test_db
sudo -u postgres dropdb test_db

# Check MongoDB connection
mongosh --eval "db.runCommand('ping')"
```

#### Database Connection Issues
```bash
# Test PostgreSQL connection
python -c "import psycopg2; conn = psycopg2.connect('host=localhost user=postgres dbname=postgres'); print('✅ PostgreSQL OK')"

# Test MongoDB connection
python -c "from pymongo import MongoClient; MongoClient().admin.command('ping'); print('✅ MongoDB OK')"
```

#### Setup Script Issues
```bash
# Run with verbose logging
python setup_databases.py --config-file .env

# Check database existence
sudo -u postgres psql -l | grep resxiv

# Drop and recreate (if needed)
python setup_databases.py --drop-existing
```

#### Log Analysis
```bash
# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Check setup script logs
tail -f database_setup.log

# Run verification script
python -c "
import psycopg2
from pymongo import MongoClient
try:
    # Test PostgreSQL
    conn = psycopg2.connect('host=localhost user=postgres dbname=resxiv')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s', ('public',))
    print(f'✅ PostgreSQL: {cursor.fetchone()[0]} tables')
    conn.close()
    
    # Test MongoDB
    client = MongoClient()
    db = client.resxiv_chat
    print(f'✅ MongoDB: {len(db.list_collection_names())} collections')
    client.close()
except Exception as e:
    print(f'❌ Error: {e}')
"
```

## Usage Examples

### Task Management Queries

```sql
-- Get all tasks for a project with assignees
SELECT t.title, t.status, t.priority, u.name as assignee
FROM tasks t 
LEFT JOIN task_assignees ta ON t.id = ta.task_id
LEFT JOIN users u ON ta.user_id = u.id
WHERE t.project_id = 'your-project-id' AND t.deleted_at IS NULL;

-- Get task dependency chain (for Gantt charts)
WITH RECURSIVE task_chain AS (
    SELECT id, title, parent_task_id, 0 as level
    FROM tasks WHERE parent_task_id IS NULL
    UNION ALL
    SELECT t.id, t.title, t.parent_task_id, tc.level + 1
    FROM tasks t
    JOIN task_chain tc ON t.parent_task_id = tc.id
)
SELECT * FROM task_chain ORDER BY level, title;

-- Time tracking summary
SELECT 
    u.name,
    SUM(ttl.hours) as total_hours,
    COUNT(DISTINCT t.id) as tasks_worked
FROM task_time_logs ttl
JOIN users u ON ttl.user_id = u.id
JOIN tasks t ON ttl.task_id = t.id
WHERE ttl.log_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY u.id, u.name
ORDER BY total_hours DESC;
```

### Feature Usage Analytics

```sql
-- Track feature usage
SELECT track_feature_usage(
    'user-uuid', 
    'task_create', 
    'project_management',
    'session-uuid',
    '{"project_id": "proj-123"}'::jsonb,
    45,  -- duration in seconds
    true -- success
);

-- Get user's most used features
SELECT feature_name, usage_count, avg_duration
FROM get_user_top_features('user-uuid', 30, 10);

-- Project invitation workflow
SELECT create_project_invitation(
    'project-uuid',
    'inviter-uuid', 
    'colleague@university.edu',
    'writer',
    'write',
    'Join our research project!',
    7 -- expires in 7 days
);
```

## Status Summary

| Component | Status | Tables/Collections | Functions | Extensions |
|-----------|--------|-------------------|-----------|------------|
| PostgreSQL | ✅ Working | 44 tables | 77 functions | pgcrypto, vector |
| MongoDB | ✅ Working | 2 collections | - | - |
| Setup Script | ✅ Clean Run | No warnings | No errors | All verified |
| Dependencies | ✅ Installed | - | - | All available |

## Files

- `setup_databases.py` - Main database setup script ✅
- `install_postgres_deps.sh` - Dependency installer ✅ 
- `db_details.txt` - Complete SQL schema ✅
- `env_example.txt` - Environment variable template
- `config.py` - Alternative configuration (if .env fails)
- `requirements.txt` - Python dependencies
- `database_setup.log` - Setup execution log

## Next Steps

After successful database setup:
1. ✅ Database schema is complete and tested
2. 🔄 Implement task management API endpoints  
3. 🔄 Create frontend task management UI
4. 🔄 Set up real-time notifications for task updates
5. 🔄 Implement task analytics dashboard
6. 🔄 Add task templates for common research workflows

The database is now ready for a full-featured academic collaboration platform with comprehensive task management! 🚀 