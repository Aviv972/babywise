#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis Migration Test Script

This script tests the Redis compatibility layer and service to ensure
proper functionality with both the aioredis and redis.asyncio backends.
"""

import os
import sys
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("redis_migration_test")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import compatibility layer and redis service
try:
    from backend.services.redis_compat import (
        USE_REDIS_ASYNCIO,  # Flag that determines which backend is used
        redis_connection,
        test_redis_connection,
        get_with_fallback,
        set_with_fallback,
        delete_with_fallback
    )
    from backend.services.redis_service import (
        get_thread_state,
        save_thread_state,
        delete_thread_state,
        cache_routine_summary,
        get_cached_routine_summary,
        cache_recent_events,
        get_cached_recent_events,
        cache_active_routine,
        get_active_routine,
        invalidate_routine_cache,
        get_thread_events,
        add_event_to_thread,
        execute_list_command,
        get_multiple
    )
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Test data
test_thread_id = f"test_migration_{int(time.time())}"
test_event_id = f"event_{int(time.time())}"
test_state = {
    "messages": [
        {"type": "human", "content": "Hello, how are you?"},
        {"type": "ai", "content": "I'm doing well, thank you!"}
    ],
    "context": {
        "baby_age": "3 months",
        "sleep_concern": "waking up frequently"
    },
    "metadata": {
        "language": "en",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
}
test_summary = {
    "sleep": {
        "total_duration": 720,
        "average_duration": 240,
        "count": 3
    }
}
test_events = [
    {
        "id": "event1",
        "type": "sleep_start",
        "timestamp": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "event2",
        "type": "sleep_end",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
]

async def test_basic_connection():
    """Test basic Redis connection"""
    logger.info("Testing basic Redis connection...")
    is_connected = await test_redis_connection()
    if is_connected:
        logger.info("✅ Redis connection successful")
        return True
    else:
        logger.error("❌ Redis connection failed")
        return False

async def test_low_level_operations():
    """Test low-level operations from compatibility layer"""
    logger.info("Testing low-level Redis operations...")
    
    # Test setting a value
    test_key = f"test_key_{int(time.time())}"
    test_value = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
    
    set_result = await set_with_fallback(test_key, test_value)
    if not set_result:
        logger.error("❌ Failed to set test value")
        return False
    
    # Test getting a value
    get_result = await get_with_fallback(test_key)
    if not get_result or get_result.get("test") is not True:
        logger.error("❌ Failed to get test value or value mismatch")
        return False
    
    # Test deleting a value
    delete_result = await delete_with_fallback(test_key)
    if not delete_result:
        logger.error("❌ Failed to delete test value")
        return False
    
    # Verify deletion
    get_after_delete = await get_with_fallback(test_key)
    if get_after_delete is not None:
        logger.error("❌ Value still exists after deletion")
        return False
    
    logger.info("✅ Low-level Redis operations successful")
    return True

async def test_thread_state_operations():
    """Test thread state operations"""
    logger.info("Testing thread state operations...")
    
    # Save thread state
    save_result = await save_thread_state(test_thread_id, test_state)
    if not save_result:
        logger.error("❌ Failed to save thread state")
        return False
    
    # Get thread state
    get_result = await get_thread_state(test_thread_id)
    if not get_result or not isinstance(get_result, dict):
        logger.error("❌ Failed to get thread state or wrong type")
        return False
    
    # Verify content
    if get_result.get("context", {}).get("baby_age") != "3 months":
        logger.error("❌ Thread state content mismatch")
        return False
    
    # Delete thread state
    delete_result = await delete_thread_state(test_thread_id)
    if not delete_result:
        logger.error("❌ Failed to delete thread state")
        return False
    
    # Verify deletion
    get_after_delete = await get_thread_state(test_thread_id)
    if get_after_delete is not None:
        logger.error("❌ Thread state still exists after deletion")
        return False
    
    logger.info("✅ Thread state operations successful")
    return True

async def test_routine_cache_operations():
    """Test routine cache operations"""
    logger.info("Testing routine cache operations...")
    
    # Cache summary
    summary_result = await cache_routine_summary(test_thread_id, "sleep", test_summary)
    if not summary_result:
        logger.error("❌ Failed to cache routine summary")
        return False
    
    # Get cached summary
    get_summary = await get_cached_routine_summary(test_thread_id, "sleep")
    if not get_summary or not isinstance(get_summary, dict):
        logger.error("❌ Failed to get cached summary or wrong type")
        return False
    
    # Cache events
    events_result = await cache_recent_events(test_thread_id, "sleep", test_events)
    if not events_result:
        logger.error("❌ Failed to cache recent events")
        return False
    
    # Get cached events
    get_events = await get_cached_recent_events(test_thread_id, "sleep")
    if not get_events or not isinstance(get_events, list):
        logger.error("❌ Failed to get cached events or wrong type")
        return False
    
    # Cache active routine
    active_result = await cache_active_routine(test_thread_id, "sleep", True)
    if not active_result:
        logger.error("❌ Failed to cache active routine")
        return False
    
    # Get active routine
    is_active = await get_active_routine(test_thread_id, "sleep")
    if not is_active:
        logger.error("❌ Failed to get active routine status")
        return False
    
    # Invalidate cache
    invalidate_result = await invalidate_routine_cache(test_thread_id)
    if not invalidate_result:
        logger.error("❌ Failed to invalidate routine cache")
        return False
    
    # Verify invalidation
    get_after_invalidate = await get_cached_routine_summary(test_thread_id, "sleep")
    if get_after_invalidate is not None:
        logger.error("❌ Routine summary still exists after invalidation")
        return False
    
    logger.info("✅ Routine cache operations successful")
    return True

async def test_list_operations():
    """Test Redis list operations"""
    logger.info("Testing Redis list operations...")
    
    event_key = f"test:event:{test_event_id}"
    thread_events_key = f"test:thread_events:{test_thread_id}"
    
    # Add event to thread
    add_result = await add_event_to_thread(test_thread_id, event_key)
    if not add_result:
        logger.error("❌ Failed to add event to thread")
        return False
    
    # Execute list command
    command_result = await execute_list_command(thread_events_key, "rpush", "another_event")
    if not command_result:
        logger.error("❌ Failed to execute list command")
        return False
    
    # Get thread events
    events = await get_thread_events(test_thread_id)
    if not events or len(events) < 1:
        logger.error("❌ Failed to get thread events or wrong count")
        return False
    
    # Clean up - directly through compatibility layer to test connection
    async with redis_connection() as client:
        if client:
            await client.delete(thread_events_key)
    
    logger.info("✅ List operations successful")
    return True

async def test_multiple_operations():
    """Test getting multiple values at once"""
    logger.info("Testing multiple get operations...")
    
    # Set up multiple keys
    keys = [
        f"test:multi:1:{int(time.time())}",
        f"test:multi:2:{int(time.time())}",
        f"test:multi:3:{int(time.time())}"
    ]
    
    # Set values
    for i, key in enumerate(keys):
        await set_with_fallback(key, {"index": i, "value": f"test_{i}"})
    
    # Get multiple
    multi_result = await get_multiple(keys)
    if not multi_result or len(multi_result) != len(keys):
        logger.error("❌ Failed to get multiple values or wrong count")
        return False
    
    # Clean up
    for key in keys:
        await delete_with_fallback(key)
    
    logger.info("✅ Multiple operations successful")
    return True

async def test_memory_fallback():
    """Test memory fallback when Redis is unavailable"""
    logger.info("Testing memory fallback...")
    
    # This test assumes Redis is available and then simulates a failure
    # by using a non-existent key for retrieval
    
    fallback_key = f"test:fallback:{int(time.time())}"
    fallback_value = {"test": True, "memory_only": True}
    
    # Store directly in memory cache (skipping Redis)
    from backend.services.redis_compat import _memory_cache
    _memory_cache[fallback_key] = fallback_value
    
    # Try to get it via the fallback mechanism
    get_result = await get_with_fallback(fallback_key)
    if not get_result or get_result.get("memory_only") is not True:
        logger.error("❌ Memory fallback failed")
        return False
    
    # Clean up
    if fallback_key in _memory_cache:
        del _memory_cache[fallback_key]
    
    logger.info("✅ Memory fallback successful")
    return True

async def run_tests():
    """Run all tests and report results"""
    logger.info("===== REDIS MIGRATION TEST SUITE =====")
    logger.info(f"Using redis.asyncio: {USE_REDIS_ASYNCIO}")
    
    # Define tests
    tests = [
        test_basic_connection,
        test_low_level_operations,
        test_thread_state_operations,
        test_routine_cache_operations,
        test_list_operations,
        test_multiple_operations,
        test_memory_fallback
    ]
    
    # Run tests and collect results
    results = {}
    overall_success = True
    for test in tests:
        test_name = test.__name__
        try:
            success = await test()
            results[test_name] = success
            if not success:
                overall_success = False
        except Exception as e:
            logger.error(f"Error in {test_name}: {e}")
            results[test_name] = False
            overall_success = False
    
    # Report results
    logger.info("===== TEST RESULTS =====")
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    # Clean up any leftover test data
    try:
        await invalidate_routine_cache(test_thread_id)
        await delete_thread_state(test_thread_id)
    except:
        pass
    
    # Final verdict
    if overall_success:
        logger.info("✅✅✅ ALL TESTS PASSED - Migration is working correctly ✅✅✅")
        return 0
    else:
        logger.error("❌❌❌ SOME TESTS FAILED - Migration needs attention ❌❌❌")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run_tests())) 