# ResXiv Backend - Production Grade FastAPI Application

A unified research collaboration platform backend built with FastAPI following production best practices.

## 🏗️ Architecture Overview

```
resxiv_backend/
├── app/                      # Application core
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization
│   ├── config/              # Configuration management
│   ├── core/                # Core functionality (auth, security, etc.)
│   ├── database/            # Database connection and models
│   ├── models/              # Pydantic models (separate from endpoints)
│   ├── schemas/             # Database schemas/SQLAlchemy models
│   ├── services/            # Business logic layer
│   ├── repositories/        # Data access layer
│   └── utils/               # Utility functions
├── api/                     # API routes
│   ├── __init__.py
│   ├── dependencies.py      # Shared dependencies
│   ├── v1/                  # API version 1
│   │   ├── __init__.py
│   │   ├── endpoints/       # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── projects.py
│   │   │   ├── papers.py
│   │   │   ├── tasks.py
│   │   │   ├── conversations.py
│   │   │   ├── latex.py
│   │   │   ├── analytics.py
│   │   │   └── files.py
│   │   └── api.py           # API router aggregation
├── middleware/              # Custom middleware
├── tests/                   # Test suite
├── migrations/              # Database migrations
├── static/                  # Static files
├── uploads/                 # File uploads
├── .env.example             # Environment variables template
├── .gitignore
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 📁 Data Directory Structure

ResXiv uses a centralized data directory for organized file storage:

```
/ResXiv_V2/                    # Main data directory (configurable)
├── papers/                    # PDF files with safe naming
├── bib/                      # Bibliography files (from GROBID)
└── xml/                      # XML metadata files (from GROBID)
```

**Configuration:**
- Data directory location: Set via `RESXIV_DATA_DIR` environment variable
- Default location: `/ResXiv_V2` 
- Auto-created on first use with proper permissions
- Safe filename generation prevents conflicts and filesystem issues

## 🚀 Features

### Core Platform Features
- **User Management**: Registration, authentication, profiles, permissions
- **Project Collaboration**: Multi-user projects with role-based access
- **Paper Management**: Upload, annotate, organize research papers
- **Task Management**: Asana-like task tracking with dependencies, time logs
- **Real-time Chat**: WebSocket-based messaging with file sharing
- **LaTeX Editor**: Collaborative editing with version control
- **Knowledge Graphs**: Visual representation of research connections
- **AI Integration**: LLM-powered features for research assistance
- **File Management**: Secure upload, storage, and sharing
- **Analytics**: Usage tracking and insights

### Technical Features
- **JWT Authentication**: Secure token-based auth with refresh tokens
- **Role-based Authorization**: Project-level permissions
- **Database Abstraction**: Repository pattern with PostgreSQL + MongoDB
- **WebSocket Support**: Real-time collaboration
- **File Processing**: PDF parsing, LaTeX compilation
- **Background Tasks**: Celery for async processing
- **API Documentation**: Auto-generated with OpenAPI/Swagger
- **Testing**: Comprehensive test suite with pytest
- **Docker Support**: Containerized deployment
- **Monitoring**: Health checks and logging

## 🔧 Development Principles

### SOLID Principles
- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Extensible without modifying existing code
- **Liskov Substitution**: Proper inheritance hierarchies
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

### Best Practices
- **Separation of Concerns**: Business logic separate from API endpoints
- **DRY (Don't Repeat Yourself)**: Reusable components and utilities
- **Clean Architecture**: Layered approach (API → Services → Repositories → Database)
- **Type Safety**: Full type hints with Pydantic validation
- **Error Handling**: Comprehensive exception handling and logging
- **Security**: Input validation, SQL injection prevention, rate limiting
- **Performance**: Database indexing, query optimization, caching

## 📁 File Organization Rules

- **800 Line Limit**: No file exceeds 800 lines (split into multiple modules)
- **Single Purpose**: Each file has one clear responsibility
- **Import Organization**: Standard library → Third party → Local imports
- **Naming Conventions**: snake_case for files/functions, PascalCase for classes

## 🔐 Security

- **JWT Tokens**: Secure authentication with configurable expiration
- **Project Authorization**: Users must belong to projects to access resources
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection Prevention**: Parameterized queries only
- **Environment Variables**: All secrets in environment configuration
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 🚀 Getting Started

1. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   ```bash
   # Run migrations
   alembic upgrade head
   ```

4. **Start Development Server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **API Documentation**: http://localhost:8000/docs

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test module
pytest tests/test_auth.py
```

## 📊 Database Schema

The application uses a hybrid approach:
- **PostgreSQL**: Structured data (users, projects, tasks, etc.)
- **MongoDB**: Unstructured data (messages, file metadata)

See `ResXiv_V2/backend/reconstruction/db_details.txt` for complete schema.

## 🔄 API Versioning

- All APIs are versioned (`/api/v1/`)
- Backward compatibility maintained
- New features added to new versions
- Deprecation warnings for old endpoints

## 📈 Monitoring & Logging

- Structured logging with correlation IDs
- Health check endpoints
- Performance metrics collection
- Error tracking and alerting

## 🐳 Deployment

### Docker
```bash
docker-compose up -d
```

### Production
- Use environment-specific configs
- Enable SSL/TLS
- Configure reverse proxy (nginx)
- Set up monitoring and backups

## 📝 Contributing

1. Follow the established architecture patterns
2. Add tests for new features
3. Update documentation
4. Run linting and formatting
5. Ensure security best practices

## 📜 License

[Your License Here] 