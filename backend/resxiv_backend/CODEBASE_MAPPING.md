# ResXiv Backend - Codebase Mapping
## L6 Engineering Standards Implementation

### 🏗️ Architecture Overview

```
resxiv_backend/
├── app/                         # Core Application Layer
│   ├── main.py                  # FastAPI app with middleware, error handling
│   ├── agentic/                 # AI Agent System (LangGraph)
│   ├── config/                  # Configuration management
│   ├── core/                    # Core functionality (auth, security, errors)
│   ├── database/                # Database connections & migrations
│   ├── models/                  # Pydantic models for API contracts
│   ├── repositories/            # Data access layer (Repository pattern)
│   ├── schemas/                 # SQLAlchemy database schemas
│   ├── services/                # Business logic layer
│   ├── utils/                   # Utility functions and helpers
│   └── websockets/              # Real-time collaboration WebSockets
├── api/                         # API Routes Layer
│   └── v1/endpoints/            # Versioned API endpoints
├── tests/                       # Comprehensive test suite
└── migrations/                  # Database schema migrations
```

## 📋 Core Functionalities

### 🔐 Authentication & Authorization
- **Location**: `app/core/auth.py`, `api/v1/endpoints/auth.py`
- **Features**: JWT tokens, refresh tokens, role-based access
- **Dependencies**: `app/services/admin_service.py`
- **Status**: ✅ Production Ready

### 👥 User Management
- **Primary Service**: `app/services/user/user_service_integrated.py`
- **Repository**: `app/repositories/user_repository.py`
- **Modules**:
  - Authentication: `app/services/user/user_auth_service.py`
  - Profiles: `app/services/user/user_profile_service.py`
  - Verification: `app/services/user/user_verification_service.py`
- **Status**: ✅ Production Ready

### 📄 Paper Management
- **Primary Service**: `app/services/paper/paper_service_integrated.py`
- **Repository**: `app/repositories/paper_repository.py`
- **Modules**:
  - Storage: `app/services/paper/paper_storage_service.py`
  - Processing: `app/services/paper/paper_processing_service.py`
  - Embeddings: `app/services/paper/paper_embedding_service.py`
  - CRUD: `app/services/paper/paper_crud_service.py`
- **Endpoints**: `api/v1/endpoints/papers_consolidated.py`
- **Status**: ✅ Production Ready

### 📁 Project Collaboration
- **Repository**: `app/repositories/project_repository.py`
- **Endpoints**: `api/v1/endpoints/projects.py`
- **Features**: Multi-user projects, role-based permissions
- **Status**: ⚠️ Partial (Some repository methods not implemented)

### ✅ Task Management
- **Service**: `app/services/task_service.py`
- **Repository**: `app/repositories/task_repository.py`
- **Endpoints**: `api/v1/endpoints/tasks.py`
- **Features**: Asana-like task tracking, dependencies, time logs
- **Status**: ✅ Production Ready

### 💬 Real-time Conversations
- **Primary Service**: `app/services/conversation/conversation_service_integrated.py`
- **Repository**: `app/repositories/conversation_repository.py`
- **Modules**:
  - CRUD: `app/services/conversation/conversation_crud_service.py`
  - Project Integration: `app/services/conversation/conversation_project_service.py`
- **WebSocket**: `app/websockets/collab_ws.py`
- **Status**: ✅ Production Ready

### 📨 Message System
- **Primary Service**: `app/services/message/message_service_integrated.py`
- **Repository**: `app/repositories/message_repository.py`
- **Modules**:
  - Core: `app/services/message/message_core.py`
  - Real-time: `app/services/message/message_realtime.py`
  - Reactions: `app/services/message/message_reactions.py`
- **Status**: ✅ Production Ready

### 🌿 Git Branch Management
- **Service**: `app/services/branch_service.py`
- **Repository**: `app/repositories/branch_repository.py`
- **Endpoints**: `api/v1/endpoints/branches.py`
- **Features**: Version control, collaborative editing
- **Status**: ✅ Production Ready

### 🤖 AI Agent System (LangGraph)
- **Core Orchestrator**: `app/agentic/production_langgraph.py`
- **Enhanced Features**: `app/agentic/enhanced_langgraph.py`
- **Agent Types**:
  - Base: `app/agentic/graph/agents/base_agent.py`
  - Research: `app/agentic/graph/agents/research_agent.py`
  - Project: `app/agentic/graph/agents/project_agent.py`
  - Paper: `app/agentic/graph/agents/paper_agent.py`
- **Tools**: `app/agentic/graph/tools.py`
- **Production Tools**: `app/agentic/production_tools_registry.py`
- **Endpoints**: `api/v1/endpoints/agentic.py`, `api/v1/endpoints/agentic_production.py`
- **Status**: ✅ Production Ready

### 🔍 Search System
- **Endpoints**: `api/v1/endpoints/search.py`
- **Features**: Unified search across papers, projects, users, conversations
- **Types**: Semantic, keyword, hybrid search
- **Status**: ✅ Production Ready

### 📊 Knowledge Graphs
- **Service**: `app/services/graph_service.py`
- **Modules**:
  - Generation: `app/services/graph/graph_generation_service.py`
  - Clustering: `app/services/graph/graph_clustering_service.py`
  - Integration: `app/services/graph/graph_service_integrated.py`
- **Endpoints**: `api/v1/endpoints/graphs.py`
- **Status**: ✅ Production Ready

### 📰 Journal Management
- **Service**: `app/services/journal_service.py`
- **Modules**:
  - CRUD: `app/services/journal/journal_crud_service.py`
  - Collaboration: `app/services/journal/journal_collaboration_service.py`
- **Endpoints**: `api/v1/endpoints/journals.py`
- **Status**: ✅ Production Ready

### 🔬 Research Integration
- **Aggregator**: `app/services/research_aggregator_service.py`
- **Core Framework**: `app/services/research_agent_core.py`
- **Data Sources**:
  - ArXiv: `app/services/arxiv_service.py`
  - OpenAlex: `app/services/openalex_service.py`
  - CrossRef: `app/services/crossref_service.py`
  - Papers with Code: `app/services/papers_with_code_service.py`
  - AI Deadlines: `app/services/ai_deadlines_service.py`
  - Grant Scraper: `app/services/grant_scraper_service.py`
- **Status**: ✅ Production Ready

### 📧 Email System
- **Service**: `app/services/email_service.py`
- **Features**: Verification emails, notifications, templates
- **Status**: ✅ Production Ready

### 🗄️ Caching & Storage
- **Redis Service**: `app/services/redis_service.py`
- **Enhanced Cache**: `app/core/enhanced_cache.py`
- **Features**: Message caching, user sessions, performance optimization
- **Status**: ✅ Production Ready

### 📈 Analytics
- **Endpoints**: `api/v1/endpoints/analytics.py`
- **Features**: User analytics, project metrics, system health
- **Status**: ⚠️ Partial (Some test failures)

### 🔧 Core Infrastructure

#### Configuration Management
- **Settings**: `app/config/settings.py`
- **Environment**: `.env.example` (229 lines of config options)
- **Status**: ✅ Production Ready

#### Database Layer
- **Connection**: `app/database/connection.py`
- **Migrations**: `app/database/migrations.py`
- **Support**: PostgreSQL (structured) + MongoDB (unstructured) + Redis (cache)
- **Status**: ✅ Production Ready

#### Error Handling
- **Core**: `app/core/error_handling.py`
- **Centralized**: `app/core/centralized_error_handler.py`
- **Service Errors**: `app/core/error_handler.py`
- **Status**: ✅ Production Ready

#### Security
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based, project-level permissions
- **Rate Limiting**: `app/core/ratelimiter.py`
- **Input Validation**: Pydantic models throughout
- **Status**: ✅ Production Ready

## 🧪 Testing Infrastructure
- **Location**: `tests/` (155 test files)
- **Configuration**: `tests/conftest.py`
- **Coverage**: Unit tests, integration tests, API tests
- **Test Data**: Comprehensive fixtures and helpers
- **Status**: ✅ Good Coverage (some failures to fix)

## 📋 File Size Compliance
- **Limit**: 1000 lines per file (user specification)
- **Current Status**: 
  - ✅ Most files compliant
  - ⚠️ Some files near limit (700+ lines)
  - Largest: `api/v1/endpoints/journals.py` (713 lines)

## 🚀 Production Readiness Score

| Component | Status | Score |
|-----------|--------|-------|
| Architecture | ✅ Excellent | 9/10 |
| Security | ✅ Production Ready | 8/10 |
| Testing | ⚠️ Good (some failures) | 7/10 |
| Performance | ✅ Optimized | 8/10 |
| Documentation | ✅ Well Documented | 8/10 |
| Error Handling | ✅ Comprehensive | 9/10 |
| AI Integration | ✅ Advanced (LangGraph) | 9/10 |

**Overall Score: 8.2/10** - Production Ready with Minor Issues

## 🔄 Migration Notes
- Several services have refactored versions with legacy compatibility
- Gradual migration pattern implemented for zero-downtime updates
- All new services follow L6 engineering standards

## 📚 Technology Stack
- **Framework**: FastAPI 0.104.1
- **Database**: SQLAlchemy 2.0 (async), PostgreSQL, MongoDB, Redis
- **AI**: LangGraph 0.0.26, LangChain-OpenAI 0.0.5
- **Testing**: pytest, pytest-asyncio
- **Authentication**: python-jose, passlib
- **Async**: asyncio, asyncpg, motor

## 🔧 Maintenance Requirements
1. **TODO Items**: Complete repository method implementations
2. **Test Fixes**: Address failing analytics tests
3. **Performance**: Monitor file sizes for 1000-line compliance
4. **Dependencies**: Regular security updates for production packages 