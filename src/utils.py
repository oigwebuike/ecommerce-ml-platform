"""
Shared utilities for the platform
"""
import logging
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class SmartCache:
    """Intelligent caching that falls back from Redis to in-memory"""
    
    def __init__(self, use_redis: bool = None):
        self.logger = logging.getLogger(__name__)
        
        # Auto-detect Redis availability if not specified
        if use_redis is None:
            use_redis = self._test_redis_connection()
        
        self.use_redis = use_redis
        
        if self.use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    decode_responses=True
                )
                self.redis_client.ping()
                self.logger.info("✅ Using Redis for caching")
            except Exception as e:
                self.logger.warning(f"Redis failed, falling back to memory: {e}")
                self.use_redis = False
        
        if not self.use_redis:
            self.memory_cache = {}
            self.cache_timestamps = {}
            self.max_size = 10000
            self.ttl = 60
            self.logger.info("⚠️ Using in-memory cache")
    
    def _test_redis_connection(self) -> bool:
        """Test if Redis is available"""
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379)
            client.ping()
            return True
        except:
            return False
    
    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields"""
        if self.use_redis:
            return self.redis_client.hgetall(key)
        else:
            # Check TTL for in-memory cache
            if key in self.cache_timestamps:
                if time.time() - self.cache_timestamps[key] > self.ttl:
                    # Expired
                    self.memory_cache.pop(key, None)
                    self.cache_timestamps.pop(key, None)
                    return {}
            return self.memory_cache.get(key, {})
    
    def hset(self, key: str, mapping: Dict[str, Any]):
        """Set hash fields"""
        if self.use_redis:
            self.redis_client.hset(key, mapping=mapping)
        else:
            # In-memory with TTL
            current_time = time.time()
            self.memory_cache[key] = {k: str(v) for k, v in mapping.items()}
            self.cache_timestamps[key] = current_time
            
            # Simple cleanup
            self._cleanup_memory_cache()
    
    def _cleanup_memory_cache(self):
        """Clean expired entries and enforce max size"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            k for k, t in self.cache_timestamps.items() 
            if current_time - t > self.ttl
        ]
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
        
        # Enforce max size (simple LRU)
        if len(self.memory_cache) > self.max_size:
            oldest_keys = sorted(
                self.cache_timestamps.items(), 
                key=lambda x: x[1]
            )[:len(self.memory_cache) - self.max_size]
            
            for key, _ in oldest_keys:
                self.memory_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)

def setup_logging(name: str) -> logging.Logger:
    """Setup consistent logging across services"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(name)

def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat()

def calculate_latency_percentile(latencies: list, percentile: int = 99) -> float:
    """Calculate latency percentiles"""
    if not latencies:
        return 0.0
    
    import numpy as np
    return np.percentile(latencies, percentile)