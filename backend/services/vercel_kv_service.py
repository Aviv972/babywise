"""
Vercel KV Service for Redis access using the vercel-kv package.
This provides a higher-level interface to the Redis connection used by Vercel KV.
"""

import logging
import json
import traceback
from typing import Any, Dict, List, Optional, Union

try:
    from vercel_kv import VercelKV
    VERCEL_KV_AVAILABLE = True
except ImportError:
    VERCEL_KV_AVAILABLE = False
    logging.warning("vercel-kv package not available, using fallback Redis client")

# Configure logging
logger = logging.getLogger(__name__)

# In-memory fallback cache when Vercel KV is unavailable
_memory_cache = {}

class VercelKVService:
    """
    Service for interacting with Vercel KV (Redis).
    Provides common operations and handles connection errors with fallbacks.
    """
    
    def __init__(self):
        """Initialize the Vercel KV service."""
        self.client = None
        if VERCEL_KV_AVAILABLE:
            try:
                self.client = VercelKV()
                logger.info("Vercel KV client initialized")
            except Exception as e:
                logger.error(f"Error initializing Vercel KV client: {e}")
                logger.error(traceback.format_exc())
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Vercel KV.
        Falls back to memory cache if Vercel KV is unavailable.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found, or None
        """
        if not key:
            logger.warning("Attempted to get with empty key")
            return None
            
        logger.debug(f"Getting value for key: {key}")
        
        try:
            if self.client:
                # Try to get from Vercel KV
                value = await self.client.get(key)
                
                if value is not None:
                    logger.debug(f"Got value from Vercel KV for key: {key}")
                    
                    # Try to parse JSON if it looks like JSON
                    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            return value
                    return value
                else:
                    logger.debug(f"No value found in Vercel KV for key: {key}")
            else:
                logger.warning("Vercel KV client not available")
        except Exception as e:
            logger.error(f"Error getting value from Vercel KV for key {key}: {e}")
        
        # Fall back to memory cache
        if key in _memory_cache:
            logger.info(f"Using memory cache fallback for key: {key}")
            return _memory_cache.get(key)
        
        logger.debug(f"No value found for key: {key}")
        return None
    
    async def set(self, key: str, value: Any, expiration: Optional[int] = None) -> bool:
        """
        Set a value in Vercel KV.
        Always updates memory cache regardless of Vercel KV availability.
        
        Args:
            key: The key to set
            value: The value to store
            expiration: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not key:
            logger.warning("Attempted to set with empty key")
            return False
            
        logger.debug(f"Setting value for key: {key}")
        
        # Convert complex objects to JSON strings for storage
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)
        
        success = False
        try:
            if self.client:
                # Try to set in Vercel KV
                if expiration:
                    await self.client.set(key, value, ex=expiration)
                else:
                    await self.client.set(key, value)
                logger.debug(f"Value set in Vercel KV for key: {key}")
                success = True
            else:
                logger.warning("Vercel KV client not available for setting value")
        except Exception as e:
            logger.error(f"Error setting value in Vercel KV for key {key}: {e}")
        
        # Always update memory cache
        try:
            # For memory cache, store already parsed objects if possible
            if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                try:
                    _memory_cache[key] = json.loads(value)
                except json.JSONDecodeError:
                    _memory_cache[key] = value
            else:
                _memory_cache[key] = value
                
            logger.debug(f"Value set in memory cache for key: {key}")
            
            # We consider it a success if at least the memory cache was updated
            return True
        except Exception as e:
            logger.error(f"Error setting value in memory cache for key {key}: {e}")
            return success
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from Vercel KV.
        Always tries to delete from memory cache regardless of Vercel KV availability.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not key:
            logger.warning("Attempted to delete with empty key")
            return False
            
        logger.debug(f"Deleting key: {key}")
        
        success = False
        try:
            if self.client:
                # Try to delete from Vercel KV
                await self.client.delete(key)
                logger.debug(f"Key deleted from Vercel KV: {key}")
                success = True
            else:
                logger.warning("Vercel KV client not available for deleting key")
        except Exception as e:
            logger.error(f"Error deleting key from Vercel KV: {key}, error: {e}")
        
        # Always try to delete from memory cache
        try:
            if key in _memory_cache:
                del _memory_cache[key]
                logger.debug(f"Key deleted from memory cache: {key}")
                
            # We consider it a success if at least we got here without errors
            return True
        except Exception as e:
            logger.error(f"Error deleting key from memory cache: {key}, error: {e}")
            return success
            
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Vercel KV.
        Falls back to memory cache if Vercel KV is unavailable.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        if not key:
            logger.warning("Attempted to check existence with empty key")
            return False
            
        logger.debug(f"Checking if key exists: {key}")
        
        try:
            if self.client:
                # Try to check in Vercel KV
                exists = await self.client.exists(key)
                logger.debug(f"Key {key} exists in Vercel KV: {exists}")
                return exists == 1
            else:
                logger.warning("Vercel KV client not available for checking key existence")
        except Exception as e:
            logger.error(f"Error checking if key exists in Vercel KV: {key}, error: {e}")
        
        # Fall back to memory cache
        exists = key in _memory_cache
        logger.debug(f"Key {key} exists in memory cache: {exists}")
        return exists

# Create a singleton instance
vercel_kv_service = VercelKVService()

# Convenience functions that use the service
async def get_kv(key: str) -> Optional[Any]:
    """Get a value from Vercel KV."""
    return await vercel_kv_service.get(key)

async def set_kv(key: str, value: Any, expiration: Optional[int] = None) -> bool:
    """Set a value in Vercel KV."""
    return await vercel_kv_service.set(key, value, expiration)

async def delete_kv(key: str) -> bool:
    """Delete a value from Vercel KV."""
    return await vercel_kv_service.delete(key)

async def exists_kv(key: str) -> bool:
    """Check if a key exists in Vercel KV."""
    return await vercel_kv_service.exists(key) 