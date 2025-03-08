"""
Redis health check script for the Babywise Chatbot.
Verifies Redis connectivity, performs basic operations, and checks cache expiration.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.services.redis_service import initialize_redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_redis_health():
    """Perform a health check on the Redis connection and basic operations."""
    try:
        # Step 1: Initialize Redis client
        logger.info("Step 1: Initializing Redis client...")
        redis_client = await initialize_redis()
        if not redis_client:
            logger.error("Failed to initialize Redis client")
            return False
        logger.info("✓ Redis client initialized successfully")
        
        # Step 2: Test basic operations
        logger.info("Step 2: Testing basic Redis operations...")
        
        # Test SET operation
        test_key = "health_check_test"
        test_value = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "testing"
        }
        result = await redis_client.set(test_key, json.dumps(test_value), ex=60)  # Expire in 60 seconds
        assert result is True, "Failed to set test value"
        logger.info("✓ SET operation successful")
        
        # Test GET operation
        retrieved_value = await redis_client.get(test_key)
        assert retrieved_value is not None, "Failed to get test value"
        retrieved_data = json.loads(retrieved_value)
        assert retrieved_data["status"] == "testing", "Retrieved value does not match"
        logger.info("✓ GET operation successful")
        
        # Test TTL operation
        ttl = await redis_client.ttl(test_key)
        assert ttl > 0, "Key should have a positive TTL"
        logger.info(f"✓ TTL operation successful (expires in {ttl} seconds)")
        
        # Step 3: Test cache expiration
        logger.info("Step 3: Testing cache expiration...")
        
        # Set a key that expires immediately
        await redis_client.set("expire_test", "test", ex=1)
        logger.info("Set test key with 1 second expiration")
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Verify key has expired
        expired_value = await redis_client.get("expire_test")
        assert expired_value is None, "Key should have expired"
        logger.info("✓ Cache expiration working correctly")
        
        # Step 4: Test connection pool
        logger.info("Step 4: Testing connection pool...")
        
        # Perform multiple operations concurrently
        tasks = []
        for i in range(10):
            key = f"concurrent_test_{i}"
            tasks.append(redis_client.set(key, str(i), ex=5))
        
        # Wait for all operations to complete
        await asyncio.gather(*tasks)
        logger.info("✓ Connection pool handling concurrent operations correctly")
        
        # Step 5: Clean up
        logger.info("Step 5: Cleaning up test keys...")
        await redis_client.delete(test_key)
        for i in range(10):
            await redis_client.delete(f"concurrent_test_{i}")
        logger.info("✓ Test keys cleaned up successfully")
        
        logger.info("All Redis health checks passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(check_redis_health()) 