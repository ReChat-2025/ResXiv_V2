#!/bin/bash

# Development startup script for ResXiv backend
# This script sets the required environment variables and starts the backend server

echo "Starting ResXiv backend in development mode..."

# Set environment variables
export JWT_SECRET_KEY="demo-jwt-secret-key-2024"
export SECRET_KEY="demo-secret-key-for-investors-2024"
export ENVIRONMENT="development"
export DEBUG="true"
export DATABASE_URL="postgresql://resxiv_user:resxiv_password@localhost:5432/resxiv_db"
export REDIS_URL="redis://localhost:6379/0"
export MONGODB_URL="mongodb://localhost:27017/resxiv_chat"
export CORS_ORIGINS="http://localhost:3000,http://localhost:3001"

echo "Environment variables set..."
echo "Starting uvicorn server..."

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload