"""
Caching Module - Optimization #4
Hash-based caching for extracted text and embeddings
"""

import hashlib
import pickle
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

from app.config import *

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache only.")


class CacheBackend:
    """Base cache interface"""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = None):
        raise NotImplementedError
    
    def delete(self, key: str):
        raise NotImplementedError
    
    def clear(self):
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """
    In-memory LRU cache (fallback when Redis unavailable)
    """
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.cache = OrderedDict()
        self.expiry = {}
        self.max_size = max_size
        logger.info(f"MemoryCache initialized (max_size={max_size})")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Check expiry
        if key in self.expiry:
            if datetime.now() > self.expiry[key]:
                self.delete(key)
                return None
        
        # Get and move to end (LRU)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in cache"""
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)
        
        self.cache[key] = value
        self.cache.move_to_end(key)
        
        # Set expiry
        if ttl:
            self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str):
        """Delete key from cache"""
        self.cache.pop(key, None)
        self.expiry.pop(key, None)
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
        self.expiry.clear()
        logger.info("Cache cleared")


class RedisCache(CacheBackend):
    """
    Redis cache backend (production use)
    """
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not installed")
        
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=False  # We'll handle serialization
        )
        
        # Test connection
        try:
            self.client.ping()
            logger.info(f"RedisCache connected to {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Set value in Redis"""
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete key from Redis"""
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
    
    def clear(self):
        """Clear all keys (dangerous!)"""
        try:
            self.client.flushdb()
            logger.warning("Redis database flushed")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")


class ProcessingCache:
    """
    High-level cache for document processing
    """
    
    def __init__(self):
        """Initialize cache with appropriate backend"""
        if not ENABLE_CACHE:
            self.backend = None
            logger.info("Caching disabled")
            return
        
        if CACHE_BACKEND == 'redis' and REDIS_AVAILABLE:
            try:
                self.backend = RedisCache()
                logger.info("Using Redis cache backend")
            except Exception as e:
                logger.warning(f"Redis init failed: {e}. Falling back to memory cache.")
                self.backend = MemoryCache()
        else:
            self.backend = MemoryCache()
            logger.info("Using in-memory cache backend")
    
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """
        Generate SHA-256 hash of file
        
        Args:
            file_path: Path to file
        
        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            # Fallback: use filename + size + mtime
            import os
            stat = os.stat(file_path)
            fallback_str = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.sha256(fallback_str.encode()).hexdigest()
    
    def get_extracted_text(self, file_hash: str) -> Optional[Dict]:
        """
        Get cached extracted text
        
        Args:
            file_hash: Hash of file
        
        Returns:
            Cached extraction result or None
        """
        if not self.backend:
            return None
        
        key = f"extract:{file_hash}"
        return self.backend.get(key)
    
    def set_extracted_text(self, file_hash: str, pages: Dict, ttl: int = None):
        """
        Cache extracted text
        
        Args:
            file_hash: Hash of file
            pages: Extraction result
            ttl: TTL in seconds (None = use default)
        """
        if not self.backend:
            return
        
        key = f"extract:{file_hash}"
        ttl = ttl or CACHE_TTL_SECONDS
        self.backend.set(key, pages, ttl)
        logger.debug(f"Cached extraction: {file_hash}")
    
    def get_embeddings(self, text_hash: str) -> Optional[Any]:
        """
        Get cached embeddings
        
        Args:
            text_hash: Hash of text
        
        Returns:
            Cached embeddings or None
        """
        if not self.backend:
            return None
        
        key = f"embed:{text_hash}"
        return self.backend.get(key)
    
    def set_embeddings(self, text_hash: str, embeddings: Any, ttl: int = None):
        """
        Cache embeddings
        
        Args:
            text_hash: Hash of text
            embeddings: Embedding vectors
            ttl: TTL in seconds
        """
        if not self.backend:
            return
        
        key = f"embed:{text_hash}"
        ttl = ttl or CACHE_TTL_SECONDS
        self.backend.set(key, embeddings, ttl)
        logger.debug(f"Cached embeddings: {text_hash}")
    
    def clear_all(self):
        """Clear all cache"""
        if self.backend:
            self.backend.clear()


# Global cache instance
_cache_instance = None

def get_cache() -> ProcessingCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ProcessingCache()
    return _cache_instance
