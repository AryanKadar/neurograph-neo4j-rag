"""
═══════════════════════════════════════════════════════════════
 🚀 Cache Service (In-Memory LRU)
═══════════════════════════════════════════════════════════════
"""

import time
import hashlib
import json
from threading import Lock
from typing import Any, Optional
from config import cache_config
from utils.logger import setup_logger

logger = setup_logger()

class CacheService:
    """
    Simple thread-safe in-memory cache with TTL.
    """
    
    def __init__(self):
        self.enabled = cache_config.ENABLE_CACHE
        self._cache = {}
        self._lock = Lock()
        logger.info(f"🚀 CacheService initialized (Type: {cache_config.CACHE_TYPE})")

    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired"""
        if not self.enabled:
            return None
            
        with self._lock:
            if key in self._cache:
                data, expiry = self._cache[key]
                if time.time() < expiry:
                    logger.debug(f"⚡ Cache HIT: {key[:20]}...")
                    return data
                else:
                    logger.debug(f"🏚️ Cache EXPIRED: {key[:20]}...")
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Set value with TTL"""
        if not self.enabled:
            return

        if ttl is None:
            ttl = cache_config.DEFAULT_TTL
            
        expiry = time.time() + ttl
        
        with self._lock:
            # Simple eviction if full (random/arbitrary for now, or clear old)
            if len(self._cache) >= cache_config.MAX_CACHE_SIZE:
                 # Clear 10% of cache to make space (simple strategy)
                 keys_to_remove = list(self._cache.keys())[:int(cache_config.MAX_CACHE_SIZE * 0.1)]
                 for k in keys_to_remove:
                     del self._cache[k]
            
            self._cache[key] = (value, expiry)

    def generate_key(self, prefix: str, data: Any) -> str:
        """Generate a consistent hash key"""
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
            
        return f"{prefix}:{hashlib.md5(data_str.encode()).hexdigest()}"

_cache_service = None

def get_cache_service():
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
