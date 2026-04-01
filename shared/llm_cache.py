"""
LLM Response Caching System
Phase 6: AI Efficiency - Prompt Caching

Caches deterministic LLM responses to reduce API calls and latency.
Uses in-memory cache with TTL, can be swapped for Redis in production.
"""
import hashlib
import json
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """
    Simple LRU (Least Recently Used) cache implementation.
    Thread-safe for single-process applications.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() > entry['expires_at']:
            self.delete(key)
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set item in cache with TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Evict oldest item if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = min(self.access_times, key=self.access_times.get)
            self.delete(oldest_key)
        
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        self.access_times[key] = time.time()
    
    def delete(self, key: str):
        """Remove item from cache"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'utilization': len(self.cache) / self.max_size,
            'default_ttl': self.default_ttl
        }


class PromptCache:
    """
    Specialized cache for LLM prompts and responses.
    Automatically generates cache keys from prompt content.
    """
    
    def __init__(self, max_size: int = 500, default_ttl: int = 3600):
        """
        Initialize prompt cache.
        
        Args:
            max_size: Maximum number of cached responses
            default_ttl: Default time-to-live in seconds (1 hour default)
        """
        self.cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, prompt: str, model: str = "default", **kwargs) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: The prompt text
            model: Model identifier
            **kwargs: Additional parameters that affect response
        
        Returns:
            Hashed cache key
        """
        # Create deterministic representation
        cache_input = {
            'prompt': prompt.strip(),
            'model': model,
            **kwargs
        }
        
        # Hash the input
        cache_str = json.dumps(cache_input, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def get(self, prompt: str, model: str = "default", **kwargs) -> Optional[str]:
        """
        Get cached response for a prompt.
        
        Args:
            prompt: The prompt text
            model: Model identifier
            **kwargs: Additional parameters
        
        Returns:
            Cached response or None
        """
        key = self._generate_key(prompt, model, **kwargs)
        result = self.cache.get(key)
        
        if result is not None:
            self.hits += 1
            logger.debug(f"Cache HIT for prompt (key: {key[:16]}...)")
        else:
            self.misses += 1
            logger.debug(f"Cache MISS for prompt (key: {key[:16]}...)")
        
        return result
    
    def set(self, prompt: str, response: str, model: str = "default", 
            ttl: Optional[int] = None, **kwargs):
        """
        Cache a prompt-response pair.
        
        Args:
            prompt: The prompt text
            response: The LLM response
            model: Model identifier
            ttl: Time-to-live in seconds
            **kwargs: Additional parameters
        """
        key = self._generate_key(prompt, model, **kwargs)
        self.cache.set(key, response, ttl=ttl)
        logger.debug(f"Cached response for prompt (key: {key[:16]}...)")
    
    def invalidate(self, prompt: str, model: str = "default", **kwargs):
        """Invalidate cache entry for a specific prompt"""
        key = self._generate_key(prompt, model, **kwargs)
        self.cache.delete(key)
    
    def clear_all(self):
        """Clear entire cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            **self.cache.stats(),
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'cost_savings': hit_rate  # % of API calls saved
        }


# Global prompt cache instance
_prompt_cache = PromptCache(max_size=500, default_ttl=3600)  # 1 hour TTL


def cached_llm_call(
    ttl: int = 3600,
    cache_instance: Optional[PromptCache] = None
) -> Callable:
    """
    Decorator to cache LLM API calls.
    
    Args:
        ttl: Time-to-live for cached responses (seconds)
        cache_instance: Custom cache instance (uses global by default)
    
    Usage:
        @cached_llm_call(ttl=7200)  # 2 hour cache
        def ask_llm(prompt: str, model: str = "gpt-4") -> str:
            response = openai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
    """
    cache = cache_instance or _prompt_cache
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(prompt: str, *args, **kwargs):
            # Extract model from kwargs or use default
            cache_kwargs = dict(kwargs)
            model = cache_kwargs.pop('model', 'default')
            
            # Try to get from cache
            cached_response = cache.get(prompt, model=model, **cache_kwargs)
            if cached_response is not None:
                return cached_response
            
            # Call actual function
            response = func(prompt, *args, **kwargs)
            
            # Cache the response
            cache.set(prompt, response, model=model, ttl=ttl, **cache_kwargs)
            
            return response
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics"""
    return _prompt_cache.stats()


def clear_cache():
    """Clear global cache"""
    _prompt_cache.clear_all()


# Example usage:
"""
# 1. Direct cache usage
from shared.llm_cache import _prompt_cache

# Check cache
cached_result = _prompt_cache.get("What is 2+2?", model="gpt-4")
if cached_result:
    print(f"Using cached: {cached_result}")
else:
    result = call_llm("What is 2+2?")
    _prompt_cache.set("What is 2+2?", result, model="gpt-4", ttl=7200)

# 2. Decorator usage
@cached_llm_call(ttl=3600)
def grade_question(student_answer: str, correct_answer: str, model: str = "gemini-pro") -> str:
    prompt = f"Compare student answer '{student_answer}' to correct answer '{correct_answer}'"
    # Make actual LLM call
    response = gemini.generate(prompt, model=model)
    return response.text

# First call - makes API request
result1 = grade_question("Paris", "Paris, France")  # API call

# Second identical call - uses cache
result2 = grade_question("Paris", "Paris, France")  # Cached!

# 3. Check statistics
stats = get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
print(f"Cost savings: {stats['cost_savings']:.2%} of API calls")
print(f"Total cached: {stats['size']} responses")

# 4. Clear cache if needed
clear_cache()
"""
