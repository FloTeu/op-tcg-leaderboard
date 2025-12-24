import logging
from typing import Any
from cachetools import TTLCache
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# Multiple cache instances for different TTL values
_CACHE_6H = TTLCache(maxsize=512, ttl=60*60*6)   # 6 hours
_CACHE_1H = TTLCache(maxsize=512, ttl=60*60*1)   # 1 hour
_CACHE_30M = TTLCache(maxsize=512, ttl=60*30)    # 30 minutes
_CACHE_1D = TTLCache(maxsize=256, ttl=60*60*24)  # 1 day

# Export cache instances for monitoring
CACHE_INSTANCES = {
    "1D": _CACHE_1D,
    "6H": _CACHE_6H,
    "1H": _CACHE_1H,
    "30M": _CACHE_30M
}


def clear_all_caches() -> None:
    """Clear all cache instances"""
    for name, cache in CACHE_INSTANCES.items():
        cache.clear()
        logger.info(f"Cleared cache: {name}")

def get_cache_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all cache instances"""
    stats = {}
    for name, cache in CACHE_INSTANCES.items():
        try:
            stats[name] = {
                "size": len(cache),
                "max_size": cache.maxsize,
                "ttl_seconds": cache.ttl,
                "ttl_hours": round(cache.ttl / 3600, 1),
                "utilization_percent": round((len(cache) / cache.maxsize * 100) if cache.maxsize > 0 else 0, 1)
            }
        except Exception as e:
            logger.error(f"Error getting stats for cache {name}: {e}")
            stats[name] = {
                "size": 0,
                "max_size": 0,
                "ttl_seconds": 0,
                "ttl_hours": 0,
                "utilization_percent": 0
            }
    
    return stats

def get_total_cache_items() -> int:
    """Get total number of items across all caches"""
    return sum(len(cache) for cache in CACHE_INSTANCES.values())

def get_total_cache_capacity() -> int:
    """Get total capacity across all caches"""
    return sum(cache.maxsize for cache in CACHE_INSTANCES.values()) 