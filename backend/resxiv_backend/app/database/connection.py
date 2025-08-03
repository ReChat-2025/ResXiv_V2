"""
Database Connection Manager

Handles connections to PostgreSQL and MongoDB with connection pooling,
async support, and proper error handling.
"""

import asyncio
from typing import Optional, AsyncGenerator
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SQLAlchemy Base for ORM models
Base = declarative_base()


class DatabaseManager:
    """Database connection manager for PostgreSQL, MongoDB, and Redis"""
    
    def __init__(self):
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.mongodb_client = None
        self.mongodb_database = None
        self.redis_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all database connections"""
        if self._initialized:
            return
        
        try:
            await self._init_postgres()
            await self._init_mongodb()
            await self._init_redis()
            self._initialized = True
            logger.info("All database connections initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            await self.close()
            raise
    
    async def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            self.postgres_engine = create_async_engine(
                settings.database.postgres_url,
                echo=settings.database.postgres_echo,
                pool_size=settings.database.postgres_pool_size,
                max_overflow=settings.database.postgres_max_overflow,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
            )
            
            self.postgres_session_factory = async_sessionmaker(
                self.postgres_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.postgres_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("PostgreSQL connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {e}")
            raise
    
    async def _init_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            self.mongodb_client = AsyncIOMotorClient(
                settings.database.mongodb_url,
                maxPoolSize=20,
                minPoolSize=5,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
            )
            
            # Test connection
            await self.mongodb_client.admin.command('ping')
            
            self.mongodb_database = self.mongodb_client[settings.database.mongodb_db]
            
            logger.info("MongoDB connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {e}")
            raise
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.database.redis_url,
                socket_timeout=settings.database.redis_socket_timeout,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                max_connections=settings.database.redis_connection_pool_size,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self):
        """Close all database connections"""
        try:
            if self.postgres_engine:
                await self.postgres_engine.dispose()
                logger.info("PostgreSQL connection closed")
            
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("MongoDB connection closed")
            
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    @asynccontextmanager
    async def get_postgres_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get PostgreSQL session with automatic cleanup
        
        Usage:
            async with db_manager.get_postgres_session() as session:
                # Use session here
                pass
        """
        if not self._initialized:
            await self.initialize()
        
        async with self.postgres_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_mongodb_collection(self, collection_name: str):
        """
        Get MongoDB collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB collection object
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized")
        
        return self.mongodb_database[collection_name]
    
    async def get_redis_client(self):
        """
        Get Redis client
        
        Returns:
            Redis client
        """
        if not self._initialized:
            await self.initialize()
        
        return self.redis_client
    
    async def health_check(self) -> dict:
        """
        Check health of all database connections
        
        Returns:
            Dictionary with health status of each database
        """
        health = {
            "postgres": False,
            "mongodb": False,
            "redis": False
        }
        
        # Check PostgreSQL
        try:
            if self.postgres_engine:
                async with self.postgres_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                health["postgres"] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
        
        # Check MongoDB
        try:
            if self.mongodb_client:
                await self.mongodb_client.admin.command('ping')
                health["mongodb"] = True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
        
        # Check Redis
        try:
            if self.redis_client:
                await self.redis_client.ping()
                health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        return health


# Global database manager instance
db_manager = DatabaseManager()


# Dependency functions for FastAPI

async def get_postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get PostgreSQL session
    
    Usage in endpoints:
        async def my_endpoint(session: AsyncSession = Depends(get_postgres_session)):
            # Use session here
    """
    async with db_manager.get_postgres_session() as session:
        yield session


async def get_mongodb_database():
    """
    FastAPI dependency to get MongoDB database
    
    Usage in endpoints:
        async def my_endpoint(mongodb = Depends(get_mongodb_database)):
            collection = mongodb["my_collection"]
    """
    if not db_manager._initialized:
        await db_manager.initialize()
    
    return db_manager.mongodb_database


async def get_redis_client():
    """
    FastAPI dependency to get Redis client
    
    Usage in endpoints:
        async def my_endpoint(redis_client = Depends(get_redis_client)):
            await redis_client.set("key", "value")
    """
    return await db_manager.get_redis_client()


async def get_database_manager():
    """FastAPI dependency to get the global DatabaseManager instance.

    Ensures all database connections are initialized before returning.
    Usage in endpoints:
        async def my_endpoint(db_manager = Depends(get_database_manager)):
            # Use db_manager.postgres_session_factory, db_manager.redis_client, etc.
            pass
    """
    if not db_manager._initialized:
        await db_manager.initialize()
    return db_manager


# Utility functions

async def create_all_tables():
    """Create all tables in the database"""
    if not db_manager._initialized:
        await db_manager.initialize()
    
    async with db_manager.postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("All database tables created successfully")


async def drop_all_tables():
    """Drop all tables in the database (use with caution!)"""
    if not db_manager._initialized:
        await db_manager.initialize()
    
    async with db_manager.postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.info("All database tables dropped")


# Context manager for database lifecycle
@asynccontextmanager
async def database_lifespan():
    """Context manager for database lifecycle management"""
    try:
        await db_manager.initialize()
        yield
    finally:
        await db_manager.close() 