#!/usr/bin/env python3
"""
Redis Connection Test Script

This script tests the connection to Redis with detailed logging and timeouts.
"""

import os
import sys
import asyncio
import logging
import aioredis
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("redis_test")

# Redis connection timeout in seconds
REDIS_CONNECTION_TIMEOUT = 5.0

async def test_redis_connection():
    """Test Redis connection with timeout"""
    start_time = datetime.now()
    logger.info(f"Starting Redis connection test at {start_time}")
    
    # Get Redis URL from environment
    redis_url = os.getenv("STORAGE_URL")
    if not redis_url:
        logger.error("Redis URL not found in environment variables")
        return False
    
    # Log Redis connection attempt (without exposing credentials)
    masked_url = redis_url.replace(redis_url.split('@')[0], '***:***@')
    logger.info(f"Attempting to connect to Redis at {masked_url}")
    
    try:
        # Use asyncio.wait_for to add a timeout
        logger.info(f"Connecting with timeout of {REDIS_CONNECTION_TIMEOUT} seconds")
        redis_client = await asyncio.wait_for(
            aioredis.from_url(redis_url, socket_timeout=REDIS_CONNECTION_TIMEOUT),
            timeout=REDIS_CONNECTION_TIMEOUT
        )
        
        logger.info("Redis client initialized successfully")
        
        # Test connection by pinging Redis
        logger.info("Testing connection with PING command")
        ping_result = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        logger.info(f"Redis ping result: {ping_result}")
        
        # Test basic operations
        logger.info("Testing SET operation")
        await redis_client.set("test_key", "test_value", ex=60)
        
        logger.info("Testing GET operation")
        value = await redis_client.get("test_key")
        logger.info(f"Retrieved value: {value}")
        
        # Close connection
        await redis_client.close()
        logger.info("Redis connection closed")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Redis test completed successfully in {duration:.2f} seconds")
        return True
        
    except asyncio.TimeoutError:
        logger.error(f"Redis connection timed out after {REDIS_CONNECTION_TIMEOUT} seconds")
        return False
    except Exception as e:
        logger.error(f"Error connecting to Redis: {str(e)}", exc_info=True)
        return False

async def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("Redis Connection Test")
    logger.info("=" * 50)
    
    # Log environment info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Test Redis connection
    success = await test_redis_connection()
    
    if success:
        logger.info("Redis connection test PASSED")
        return 0
    else:
        logger.error("Redis connection test FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 