import hashlib
import json
import os
from functools import wraps
from typing import Any, Optional

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover - exercised via runtime fallback
    redis = None

# Initialize Redis client (Phase 4)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

try:
    if redis is None:
        raise ModuleNotFoundError("redis")

    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    # Test connection
    redis_client.ping()
    REDIS_AVAILABLE = True
    print(f"✅ Redis connected at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️  Redis not available: {e}. Caching disabled.")
    redis_client = None


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a unique cache key from function arguments."""
    key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
    digest = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{digest}"


def cache_response(ttl: int = 300, prefix: str = "api"):
    """
    Decorator to cache API responses in Redis.
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        prefix: Cache key prefix
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Cache read error: {e}")
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(result)
                )
            except Exception as e:
                print(f"Cache write error: {e}")
            
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str):
    """Invalidate all cache entries with given prefix."""
    if not REDIS_AVAILABLE:
        return
    
    try:
        pattern = f"{prefix}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            print(f"Invalidated {len(keys)} cache entries for {prefix}")
    except Exception as e:
        print(f"Cache invalidation error: {e}")


def get_cache_stats() -> dict:
    """Get Redis cache statistics."""
    if not REDIS_AVAILABLE:
        return {"available": False}
    
    try:
        info = redis_client.info('stats')
        return {
            "available": True,
            "total_keys": redis_client.dbsize(),
            "hits": info.get('keyspace_hits', 0),
            "misses": info.get('keyspace_misses', 0),
            "hit_rate": info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
