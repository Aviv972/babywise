"""
Test Redis analytics for routine tracking in the Babywise Chatbot.
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

from backend.db.routine_tracker import init_db, add_event
from backend.services.analytics_service import (
    update_daily_stats,
    get_daily_stats,
    update_weekly_stats,
    get_weekly_stats,
    update_pattern_stats,
    get_pattern_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_analytics():
    """Test Redis analytics for routine tracking."""
    try:
        # Initialize database
        if not init_db():
            logger.error("Failed to initialize database")
            return False

        # Generate a unique test thread ID
        test_thread_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Testing analytics with thread ID: {test_thread_id}")
        
        # Test 1: Daily Statistics
        logger.info("Testing daily statistics...")
        
        # Add sleep events
        now = datetime.utcnow()
        events = [
            (now - timedelta(hours=8), now - timedelta(hours=6), "Night sleep"),
            (now - timedelta(hours=4), now - timedelta(hours=3), "Morning nap"),
            (now - timedelta(hours=2), now - timedelta(hours=1), "Afternoon nap")
        ]
        
        # Add events one by one and let the routine tracker handle stats
        for start, end, notes in events:
            event_id = await add_event(test_thread_id, "sleep", start, end, notes)
            assert event_id is not None, "Failed to add sleep event"
        
        # Verify daily stats
        retrieved_stats = await get_daily_stats(test_thread_id, "sleep")
        assert retrieved_stats is not None, "Failed to retrieve daily stats"
        assert retrieved_stats["total_events"] == len(events), "Incorrect number of events"
        logger.info("✓ Daily statistics test passed")
        
        # Test 2: Weekly Statistics
        logger.info("Testing weekly statistics...")
        
        # Verify weekly stats
        retrieved_stats = await get_weekly_stats(test_thread_id, "sleep")
        assert retrieved_stats is not None, "Failed to retrieve weekly stats"
        assert retrieved_stats["total_events"] == len(events), "Incorrect number of events"
        logger.info("✓ Weekly statistics test passed")
        
        # Test 3: Pattern Statistics
        logger.info("Testing pattern statistics...")
        
        # Verify pattern stats
        retrieved_patterns = await get_pattern_stats(test_thread_id, "sleep")
        assert retrieved_patterns is not None, "Failed to retrieve pattern stats"
        assert retrieved_patterns["time_ranges"]["morning"] == 1, "Incorrect morning nap count"
        assert retrieved_patterns["time_ranges"]["afternoon"] == 1, "Incorrect afternoon nap count"
        assert retrieved_patterns["time_ranges"]["night"] == 1, "Incorrect night sleep count"
        assert retrieved_patterns["durations"]["short"] == 2, "Incorrect short sleep count"
        assert retrieved_patterns["durations"]["long"] == 1, "Incorrect long sleep count"
        logger.info("✓ Pattern statistics test passed")
        
        # Test 4: Stats Aggregation
        logger.info("Testing stats aggregation...")
        
        # Add another sleep event
        new_start = now - timedelta(minutes=30)
        new_end = now
        event_id = await add_event(test_thread_id, "sleep", new_start, new_end, "Quick nap")
        assert event_id is not None, "Failed to add new sleep event"
        
        # Verify aggregated stats
        retrieved_stats = await get_daily_stats(test_thread_id, "sleep")
        assert retrieved_stats is not None, "Failed to retrieve aggregated stats"
        assert retrieved_stats["total_events"] == len(events) + 1, "Incorrect total event count"
        logger.info("✓ Stats aggregation test passed")
        
        logger.info("All analytics tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Analytics test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_analytics()) 