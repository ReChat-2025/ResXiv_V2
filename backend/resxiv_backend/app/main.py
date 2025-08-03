"""
ResXiv Backend - Main FastAPI Application

Production-grade FastAPI application with proper configuration,
middleware, error handling, and lifecycle management.
"""

# Load environment variables from a .env file (development convenience)
from dotenv import load_dotenv

# This must be done before any other imports that rely on environment variables
load_dotenv()

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import uuid

from app.config.settings import get_settings
from app.database.connection import database_lifespan, db_manager
from app.core.auth import AuthenticationError, AuthorizationError
from api.v1.api import api_router
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from app.core.ratelimiter import limiter
from app.websockets.collab_ws import router as collab_ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting ResXiv Backend...")
    
    # Startup
    try:
        await db_manager.initialize()
        
        # Initialize production agentic service if configured
        try:
            from app.agentic.production_service import production_agentic_service
            logger.info("Initializing production agentic service...")
            await production_agentic_service.initialize()
            logger.info("Production agentic service initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize production agentic service: {e}")
            # Don't fail startup if agentic service fails
        
        logger.info("Application startup completed successfully")
        yield
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ResXiv Backend...")
        await db_manager.close()
        logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Middleware Configuration

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.origins,
    allow_credentials=settings.cors.credentials,
    allow_methods=settings.cors.methods,
    allow_headers=settings.cors.headers,
)

# Trusted Host Middleware (for production)
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.resxiv.com", "resxiv.com"]
    )


# Custom Middleware

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    
    # Add correlation ID for request tracking
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring"""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"- Client: {request.client.host if request.client else 'unknown'} "
        f"- User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"- Time: {process_time:.3f}s "
        f"- Path: {request.url.path}"
    )
    
    return response


# Exception Handlers

@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    logger.warning(f"Authentication error: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "authentication_failed",
            "message": exc.detail,
            "path": request.url.path,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        },
        headers=exc.headers
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors"""
    logger.warning(f"Authorization error: {exc.detail} - Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "access_denied",
            "message": exc.detail,
            "path": request.url.path,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    
    # Convert any non-serializable error objects to strings
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return obj
    
    serializable_errors = make_serializable(exc.errors())
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_failed",
            "message": "Request validation failed",
            "details": serializable_errors,
            "path": request.url.path,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(exc)} - Path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An internal error occurred",
            "path": request.url.path,
            "correlation_id": getattr(request.state, 'correlation_id', None)
        }
    )


# Health Check Endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check including database connections"""
    try:
        db_health = await db_manager.health_check()
        
        overall_status = "healthy" if all(db_health.values()) else "unhealthy"
        
        return {
            "status": overall_status,
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "databases": db_health,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": time.time()
            }
        )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "description": settings.app_description,
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else "Documentation not available in production",
        "api_prefix": "/api/v1"
    }


# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(collab_ws_router)


# Development-only endpoints
if settings.debug:
    
    @app.get("/debug/settings", tags=["Debug"])
    async def debug_settings():
        """Debug endpoint to view current settings (development only)"""
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
            "cors_origins": settings.cors.origins,
            "postgres_host": settings.database.postgres_host,
            "mongodb_host": settings.database.mongodb_host,
            "redis_host": settings.database.redis_host,
        }
    
    @app.post("/debug/create-tables", tags=["Debug"])
    async def debug_create_tables():
        """Debug endpoint to create database tables (development only)"""
        try:
            from app.database.connection import create_all_tables
            await create_all_tables()
            return {"message": "Database tables created successfully"}
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Failed to create tables: {str(e)}"}
            )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers if not settings.reload else 1,
        log_level="info"
    ) 