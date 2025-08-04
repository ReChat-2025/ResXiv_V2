# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements_demo.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_demo.txt

# Install additional packages for Railway
RUN pip install --no-cache-dir gunicorn

# Copy the application code
COPY . .

# Copy data exports for migration
COPY ../../database_export.sql ./database_export.sql
COPY ../../mongodb_dump ./mongodb_dump
COPY ../../migrate_data.py ./migrate_data.py

# Create necessary directories
RUN mkdir -p uploads static downloads

# Expose port
EXPOSE 8000

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Command to run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} 