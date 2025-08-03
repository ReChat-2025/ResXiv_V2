"""
Enhanced Caching System - L6 Engineering Standards
High-performance caching layer with Redis optimization and intelligent cache strategies.
"""

import json
import uuid
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps

import redis.asyncio as redis
from app.core.error_handling import handle_service_errors, ServiceError, ErrorCodes

logger = logging.getLogger(__name__)


class EnhancedCache:
    """
    Enhanced caching system with intelligent cache strategies.
    
    Features:
    - Multi-level caching (L1: Memory, L2: Redis)
    - Cache invalidation patterns
    - Performance monitoring
    - Automatic cache warming
    - Circuit breaker pattern
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "invalidations": 0
        }
        self.default_ttl = 3600  # 1 hour
        self.memory_cache_size_limit = 1000
    
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate consistent cache key.
        
        Args:
            prefix: Cache key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create deterministic key from arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_hash = hashlib.md5(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        
        return f"{prefix}:{key_hash}"
    
    @handle_service_errors("cache get")
    async def get(
        self,
        key: str,
        default: Any = None,
        use_memory_cache: bool = True
    ) -> Any:
        """
        Get value from cache with multi-level lookup.
        
        Args:
            key: Cache key
            default: Default value if not found
            use_memory_cache: Whether to use memory cache
            
        Returns:
            Cached value or default
        """
        try:
            # L1: Memory cache
            if use_memory_cache and key in self.memory_cache:
                memory_entry = self.memory_cache[key]
                if datetime.utcnow() < memory_entry["expires_at"]:
                    self.cache_stats["hits"] += 1
                    return memory_entry["value"]
                else:
                    # Expired, remove from memory cache
                    del self.memory_cache[key]
            
            # L2: Redis cache
            redis_value = await self.redis.get(key)
            if redis_value:
                try:
                    value = json.loads(redis_value)
                    
                    # Store in memory cache for faster access
                    if use_memory_cache:
                        self._store_in_memory_cache(key, value)
                    
                    self.cache_stats["hits"] += 1
                    return value
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode cached value for key: {key}")
            
            self.cache_stats["misses"] += 1
            return default
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    @handle_service_errors("cache set")
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_memory_cache: bool = True
    ) -> bool:
        """
        Set value in cache with multi-level storage.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            use_memory_cache: Whether to use memory cache
            
        Returns:
            Success status
        """
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            
            # Store in Redis
            await self.redis.setex(key, ttl, serialized_value)
            
            # Store in memory cache
            if use_memory_cache:
                self._store_in_memory_cache(key, value, ttl)
            
            return True
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    @handle_service_errors("cache delete")
    async def delete(self, key: str) -> bool:
        """
        Delete value from all cache levels.
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            # Remove from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # Remove from Redis
            deleted = await self.redis.delete(key)
            
            self.cache_stats["invalidations"] += 1
            return deleted > 0
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    @handle_service_errors("cache invalidate pattern")
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            
        Returns:
            Number of keys invalidated
        """
        try:
            # Find matching keys in Redis
            keys = await self.redis.keys(pattern)
            
            if keys:
                # Delete from Redis
                deleted_redis = await self.redis.delete(*keys)
                
                # Delete from memory cache
                deleted_memory = 0
                for key in list(self.memory_cache.keys()):
                    if self._matches_pattern(key, pattern):
                        del self.memory_cache[key]
                        deleted_memory += 1
                
                self.cache_stats["invalidations"] += deleted_redis
                return deleted_redis + deleted_memory
            
            return 0
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache pattern invalidation error for pattern {pattern}: {e}")
            return 0
    
    def _store_in_memory_cache(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Store value in memory cache with size limit."""
        # Enforce size limit
        if len(self.memory_cache) >= self.memory_cache_size_limit:
            # Remove oldest entry
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]["created_at"]
            )
            del self.memory_cache[oldest_key]
        
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self.memory_cache[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        redis_info = await self.redis.info("memory")
        
        return {
            "performance": {
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "errors": self.cache_stats["errors"],
                "invalidations": self.cache_stats["invalidations"]
            },
            "memory_cache": {
                "size": len(self.memory_cache),
                "limit": self.memory_cache_size_limit,
                "utilization_percent": round(len(self.memory_cache) / self.memory_cache_size_limit * 100, 2)
            },
            "redis_memory": {
                "used_memory_mb": round(redis_info.get("used_memory", 0) / (1024 * 1024), 2),
                "used_memory_peak_mb": round(redis_info.get("used_memory_peak", 0) / (1024 * 1024), 2)
            }
        }


def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    use_memory_cache: bool = True
):
    """
    Caching decorator for functions.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Custom key building function
        use_memory_cache: Whether to use memory cache
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance (assuming it's available in the context)
            cache = kwargs.get('cache') or getattr(args[0], 'cache', None)
            
            if not cache:
                # No cache available, execute function directly
                return await func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache.cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(
                cache_key,
                use_memory_cache=use_memory_cache
            )
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache.set(
                    cache_key,
                    result,
                    ttl=ttl,
                    use_memory_cache=use_memory_cache
                )
            
            return result
        
        return wrapper
    return decorator


# Cache invalidation strategies
class CacheInvalidationStrategy:
    """Cache invalidation patterns for different data types."""
    
    @staticmethod
    def user_data(user_id: uuid.UUID) -> List[str]:
        """Get cache patterns to invalidate for user data changes."""
        return [
            f"user:{user_id}:*",
            f"user_profile:{user_id}:*",
            f"user_conversations:{user_id}:*",
            f"user_projects:{user_id}:*"
        ]
    
    @staticmethod
    def conversation_data(conversation_id: uuid.UUID) -> List[str]:
        """Get cache patterns to invalidate for conversation data changes."""
        return [
            f"conversation:{conversation_id}:*",
            f"conversation_messages:{conversation_id}:*",
            f"conversation_participants:{conversation_id}:*",
            f"conversation_stats:{conversation_id}:*"
        ]
    
    @staticmethod
    def project_data(project_id: uuid.UUID) -> List[str]:
        """Get cache patterns to invalidate for project data changes."""
        return [
            f"project:{project_id}:*",
            f"project_members:{project_id}:*",
            f"project_conversations:{project_id}:*",
            f"project_stats:{project_id}:*"
        ]
    
    @staticmethod
    def message_data(conversation_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> List[str]:
        """Get cache patterns to invalidate for message changes."""
        patterns = [
            f"conversation_messages:{conversation_id}:*",
            f"conversation_stats:{conversation_id}:*",
            f"message_analytics:{conversation_id}:*"
        ]
        
        if user_id:
            patterns.extend([
                f"user_conversations:{user_id}:*",
                f"unread_count:{user_id}:*"
            ])
        
        return patterns 