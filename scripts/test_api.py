"""
Test script for the Babywise Assistant API
"""

import os
import sys
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API base URL
BASE_URL = "http://localhost:8080"

async def test_api():
    """Test all API endpoints."""
    try:
        async with httpx.AsyncClient() as client:
            # Generate a unique test thread ID
            test_thread_id = f"api_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"Starting API test with thread ID: {test_thread_id}")
            
            # Test 1: Create events
            logger.info("Test 1: Creating events...")
            
            now = datetime.utcnow()
            events = [
                {
                    "thread_id": test_thread_id,
                    "event_type": "sleep",
                    "start_time": (now - timedelta(hours=8)).isoformat(),
                    "end_time": (now - timedelta(hours=6)).isoformat(),
                    "notes": "Night sleep"
                },
                {
                    "thread_id": test_thread_id,
                    "event_type": "sleep",
                    "start_time": (now - timedelta(hours=4)).isoformat(),
                    "end_time": (now - timedelta(hours=3)).isoformat(),
                    "notes": "Morning nap"
                },
                {
                    "thread_id": test_thread_id,
                    "event_type": "sleep",
                    "start_time": (now - timedelta(hours=2)).isoformat(),
                    "end_time": (now - timedelta(hours=1)).isoformat(),
                    "notes": "Afternoon nap"
                }
            ]
            
            for event in events:
                response = await client.post(f"{BASE_URL}/events/", json=event)
                assert response.status_code == 200, f"Failed to create event: {response.text}"
                event_id = response.json()["event_id"]
                logger.info(f"Created event with ID: {event_id}")
            
            logger.info("✓ Successfully created all events")
            
            # Test 2: Get events
            logger.info("Test 2: Retrieving events...")
            
            params = {
                "start_date": (now - timedelta(days=1)).isoformat(),
                "end_date": now.isoformat(),
                "event_type": "sleep"
            }
            
            response = await client.get(f"{BASE_URL}/events/{test_thread_id}", params=params)
            assert response.status_code == 200, f"Failed to retrieve events: {response.text}"
            retrieved_events = response.json()
            assert len(retrieved_events) == len(events), "Number of events doesn't match"
            logger.info("✓ Successfully retrieved events")
            
            # Test 3: Get summary
            logger.info("Test 3: Getting routine summary...")
            
            response = await client.get(f"{BASE_URL}/summary/{test_thread_id}/sleep")
            assert response.status_code == 200, f"Failed to get summary: {response.text}"
            summary = response.json()
            assert summary["total_events"] == len(events), "Summary event count doesn't match"
            logger.info("✓ Successfully retrieved summary")
            
            # Test 4: Get analytics
            logger.info("Test 4: Getting analytics...")
            
            # Daily stats
            response = await client.get(f"{BASE_URL}/analytics/daily/{test_thread_id}/sleep")
            assert response.status_code == 200, f"Failed to get daily stats: {response.text}"
            daily_stats = response.json()
            logger.info("✓ Successfully retrieved daily stats")
            
            # Weekly stats
            response = await client.get(f"{BASE_URL}/analytics/weekly/{test_thread_id}/sleep")
            assert response.status_code == 200, f"Failed to get weekly stats: {response.text}"
            weekly_stats = response.json()
            logger.info("✓ Successfully retrieved weekly stats")
            
            # Pattern stats
            response = await client.get(f"{BASE_URL}/analytics/patterns/{test_thread_id}/sleep")
            assert response.status_code == 200, f"Failed to get pattern stats: {response.text}"
            pattern_stats = response.json()
            assert pattern_stats["time_ranges"]["morning"] == 1, "Should have 1 morning nap"
            assert pattern_stats["time_ranges"]["afternoon"] == 1, "Should have 1 afternoon nap"
            assert pattern_stats["time_ranges"]["night"] == 1, "Should have 1 night sleep"
            logger.info("✓ Successfully retrieved pattern stats")
            
            logger.info("All API tests passed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"API test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_api()) 