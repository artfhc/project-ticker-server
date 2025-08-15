import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheService:
    """In-memory cache service for ticker data"""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        logger.info(f"Cache service initialized with TTL: {ttl_seconds} seconds")
    
    def _is_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        try:
            if not cache_entry:
                return False
            
            cache_time = cache_entry.get('timestamp')
            if not cache_time:
                return False
            
            return datetime.utcnow() - cache_time < timedelta(seconds=self._ttl)
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        try:
            cache_entry = self._cache.get(key)
            if cache_entry and self._is_valid(cache_entry):
                logger.debug(f"Cache hit for key: {key}")
                return cache_entry['data']
            
            if cache_entry:
                logger.debug(f"Cache expired for key: {key}")
                self._cache.pop(key, None)  # Clean up expired entry
            else:
                logger.debug(f"Cache miss for key: {key}")
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            raise CacheError(f"Failed to retrieve cache entry: {key}", str(e))
    
    def set(self, key: str, data: Any) -> None:
        """Set data in cache with timestamp"""
        try:
            self._cache[key] = {
                'data': data,
                'timestamp': datetime.utcnow()
            }
            logger.debug(f"Cache set for key: {key}")
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            raise CacheError(f"Failed to set cache entry: {key}", str(e))
    
    def delete(self, key: str) -> bool:
        """Delete specific cache entry"""
        try:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache entry deleted: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache entry: {e}")
            raise CacheError(f"Failed to delete cache entry: {key}", str(e))
    
    def clear(self) -> None:
        """Clear all cache entries"""
        try:
            self._cache.clear()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise CacheError("Failed to clear cache", str(e))
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            valid_entries = 0
            expired_entries = 0
            
            for entry in self._cache.values():
                if self._is_valid(entry):
                    valid_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': len(self._cache),
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'ttl_seconds': self._ttl
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}