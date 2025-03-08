"""
Test Redis caching for routine tracking in the Babywise Chatbot.
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.db.routine_tracker import (
    init_db,
    add_event,
    get_events_by_date_range,
    get_routine_summary
)
from backend.services.routine_cache import (
    get_cached_routine_summary,
    get_cached_recent_events,
    get_active_routine,
    invalidate_routine_cache
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_routine_caching():
    """Test Redis caching for routine tracking."""
    try:
        # Initialize database
        if not init_db():
            logger.error("Failed to initialize database")
            return False

        # Generate a unique test thread ID
        test_thread_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Testing routine caching with thread ID: {test_thread_id}")
        
        # Test 1: Add sleep events and verify caching
        logger.info("Testing sleep event caching...")
        
        # Add multiple sleep events
        now = datetime.utcnow()
        events = [
            (now - timedelta(hours=8), now - timedelta(hours=6), "Night sleep"),
            (now - timedelta(hours=4), now - timedelta(hours=3), "Morning nap"),
            (now - timedelta(hours=2), now - timedelta(hours=1), "Afternoon nap")
        ]
        
        for start, end, notes in events:
            event_id = await add_event(test_thread_id, "sleep", start, end, notes)
            assert event_id is not None, "Failed to add sleep event"
            
        # Get events and verify they're cached
        cached_events = await get_cached_recent_events(test_thread_id, "sleep")
        assert cached_events is None, "Events should not be cached before first retrieval"
        
        # Retrieve events (this should cache them)
        retrieved_events = await get_events_by_date_range(
            test_thread_id,
            now - timedelta(days=1),
            now,
            "sleep"
        )
        assert len(retrieved_events) == 3, "Should have 3 sleep events"
        
        # Verify events are now cached
        cached_events = await get_cached_recent_events(test_thread_id, "sleep")
        assert cached_events is not None, "Events should be cached after retrieval"
        assert len(cached_events) == 3, "Cache should contain 3 sleep events"
        logger.info("✓ Sleep event caching test passed")
        
        # Test 2: Generate and cache summary
        logger.info("Testing routine summary caching...")
        
        # Get summary (this should cache it)
        summary = await get_routine_summary(test_thread_id, "sleep")
        assert summary is not None, "Failed to generate summary"
        assert summary["total_events"] == 3, "Summary should show 3 events"
        
        # Verify summary is cached
        cached_summary = await get_cached_routine_summary(test_thread_id, "sleep")
        assert cached_summary is not None, "Summary should be cached"
        assert cached_summary["total_events"] == 3, "Cached summary should show 3 events"
        logger.info("✓ Routine summary caching test passed")
        
        # Test 3: Cache invalidation
        logger.info("Testing cache invalidation...")
        
        # Add a new event (should invalidate cache)
        new_event_id = await add_event(
            test_thread_id,
            "sleep",
            now - timedelta(minutes=30),
            now,
            "Quick nap"
        )
        assert new_event_id is not None, "Failed to add new sleep event"
        
        # Verify caches are invalidated
        cached_events = await get_cached_recent_events(test_thread_id, "sleep")
        assert cached_events is None, "Events cache should be invalidated"
        
        cached_summary = await get_cached_routine_summary(test_thread_id, "sleep")
        assert cached_summary is None, "Summary cache should be invalidated"
        
        # Retrieve updated data
        updated_events = await get_events_by_date_range(
            test_thread_id,
            now - timedelta(days=1),
            now,
            "sleep"
        )
        assert len(updated_events) == 4, "Should have 4 sleep events after update"
        
        updated_summary = await get_routine_summary(test_thread_id, "sleep")
        assert updated_summary["total_events"] == 4, "Updated summary should show 4 events"
        logger.info("✓ Cache invalidation test passed")
        
        logger.info("All routine caching tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Routine caching test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_routine_caching()) 