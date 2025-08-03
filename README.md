# ResXiv V2 🚀

ResXiv V2 is a comprehensive research management platform that combines paper collection, LaTeX editing, and AI-powered research assistance.

## 🌟 Features

- **Research Paper Management**: Upload, organize, and analyze research papers
- **LaTeX Editor**: Built-in LaTeX editor with real-time compilation
- **AI Research Assistant**: Intelligent paper search and analysis
- **Project Organization**: Create and manage research projects
- **Collaboration Tools**: Share and collaborate on research projects
- **Graph Visualization**: Visualize research connections and relationships

## 🏗️ Architecture

```
ResXiv_V2/
├── frontend/          # Next.js frontend application
├── backend/           # FastAPI backend application
├── repositories/      # Git repositories for projects (ignored in git)
├── components/        # Shared components
└── lib/              # Shared utilities
```

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 15.4.4 with React 19
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI, Lucide React
- **Code Editor**: Monaco Editor
- **State Management**: Zustand
- **PDF Handling**: React PDF, PDF.js

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL, MongoDB, Redis
- **Authentication**: JWT
- **File Processing**: Git integration for project management
- **AI Integration**: OpenAI GPT models
- **Research APIs**: arXiv, OpenAlex, CrossRef, Papers with Code

## 📋 Prerequisites

- **Node.js**: 18.x or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 13 or higher
- **MongoDB**: 4.4 or higher
- **Redis**: 6 or higher
- **Git**: 2.x or higher
- **LaTeX**: Full TeX Live distribution (for PDF compilation)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ResXiv_V2
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local  # Configure your environment variables
npm run dev
```

The frontend will be available at `http://localhost:3000`

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Configure your environment variables
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The backend API will be available at `http://localhost:8001`

## 🔧 Configuration

### Frontend Environment Variables

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_APP_NAME=ResXiv V2
```

### Backend Environment Variables

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/resxiv_v2
MONGODB_URL=mongodb://localhost:27017/resxiv_v2
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Integration
OPENAI_API_KEY=your-openai-api-key

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Storage
UPLOAD_DIR=./uploads
REPOSITORIES_DIR=./repositories
```

## 🗄️ Database Setup

### PostgreSQL

```sql
CREATE DATABASE resxiv_v2;
CREATE USER resxiv_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE resxiv_v2 TO resxiv_user;
```

### MongoDB

No setup required - collections will be created automatically.

### Redis

Start Redis server:

```bash
redis-server
```

## 📦 Dependencies

### Frontend Dependencies (package.json)

The frontend uses the following key dependencies:

- **Next.js**: React framework
- **React**: UI library
- **Tailwind CSS**: Styling
- **Monaco Editor**: Code editing
- **Radix UI**: Accessible UI components
- **React PDF**: PDF viewing
- **D3.js**: Data visualization

### Backend Dependencies (requirements.txt)

The backend uses:

- **FastAPI**: Web framework
- **SQLAlchemy**: Database ORM
- **Alembic**: Database migrations
- **PyJWT**: JWT authentication
- **OpenAI**: AI integration
- **Requests**: HTTP client
- **Pydantic**: Data validation

## 🔧 Development

### Running Tests

```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd backend
pytest
```

### Code Formatting

```bash
# Frontend
cd frontend
npm run lint

# Backend
cd backend
black .
isort .
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Manual Deployment

1. Build frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Set up production backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes
4. Add tests for your changes
5. Run the test suite
6. Commit your changes: `git commit -am 'Add new feature'`
7. Push to the branch: `git push origin feature/new-feature`
8. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

1. **Frontend won't start**: Check Node.js version and run `npm install`
2. **Backend API errors**: Verify database connections and environment variables
3. **LaTeX compilation fails**: Ensure TeX Live is properly installed
4. **File upload issues**: Check file permissions and upload directory configuration

### Getting Help

- Check the [Issues](../../issues) page for known problems
- Review the API documentation at `/docs`
- Ensure all environment variables are properly configured

## 🔄 Version History

- **v2.0.0**: Complete rewrite with Next.js and FastAPI
- **v1.x**: Legacy version (deprecated)

## 👥 Authors

- **Yashwardhan** - Initial development

## 🙏 Acknowledgments

- Built with Next.js, FastAPI, and modern web technologies
- Uses research APIs from arXiv, OpenAlex, CrossRef
- AI capabilities powered by OpenAI GPT models 