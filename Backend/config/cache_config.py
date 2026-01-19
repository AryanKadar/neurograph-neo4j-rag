"""
═══════════════════════════════════════════════════════════════
 🚀 Cache Configuration
═══════════════════════════════════════════════════════════════
"""

ENABLE_CACHE = True
CACHE_TYPE = "memory" # 'memory' or 'redis'

# Memory Cache Settings
MAX_CACHE_SIZE = 1000 # Number of items
DEFAULT_TTL = 3600    # Seconds (1 hour)

# Redis Settings (Future)
REDIS_HOST = "localhost"
REDIS_PORT = 6379
