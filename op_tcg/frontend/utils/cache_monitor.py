import time
from dataclasses import dataclass, field
from typing import Dict, Any
from op_tcg.frontend.utils.cache import get_cache_stats, get_total_cache_items, get_total_cache_capacity

@dataclass
class CacheStats:
    """Cache statistics for monitoring"""
    cache_name: str
    max_size: int
    current_size: int
    hit_rate: float = 0.0
    ttl_seconds: int = 0
    last_updated: float = field(default_factory=time.time)

def get_cache_summary() -> Dict[str, Any]:
    """Get a summary of cache performance"""
    cache_stats = get_cache_stats()
    
    total_items = get_total_cache_items()
    total_capacity = get_total_cache_capacity()
    
    return {
        "total_cached_items": total_items,
        "total_capacity": total_capacity,
        "utilization_percent": round((total_items / total_capacity * 100) if total_capacity > 0 else 0, 1),
        "cache_details": cache_stats,
        "timestamp": time.time()
    } 