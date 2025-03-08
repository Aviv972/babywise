"""
Integration tests for the Babywise Chatbot

This module tests the complete functionality of both routine tracking and chat workflows.
"""

import httpx
import asyncio
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_THREAD_ID = "test_thread_123"

async def test_routine_tracking_workflow():
    """Test the complete routine tracking workflow"""
    async with httpx.AsyncClient() as client:
        # 1. Record sleep start
        sleep_start_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "baby went to sleep at 9:30",
                "thread_id": TEST_THREAD_ID,
                "language": "en"
            }
        )
        assert sleep_start_response.status_code == 200
        sleep_start_data = sleep_start_response.json()
        assert sleep_start_data["command_processed"] == True
        assert sleep_start_data["command_type"] == "sleep_event"
        assert "Recorded sleep start" in sleep_start_data["response"]

        # 2. Record sleep end
        sleep_end_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "baby woke up at 11:00",
                "thread_id": TEST_THREAD_ID,
                "language": "en"
            }
        )
        assert sleep_end_response.status_code == 200
        sleep_end_data = sleep_end_response.json()
        assert sleep_end_data["command_processed"] == True
        assert sleep_end_data["command_type"] == "sleep_event"
        assert "Recorded wake up" in sleep_end_data["response"]

        # 3. Record feeding start
        feed_start_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "started feeding at 11:15",
                "thread_id": TEST_THREAD_ID,
                "language": "en"
            }
        )
        assert feed_start_response.status_code == 200
        feed_start_data = feed_start_response.json()
        assert feed_start_data["command_processed"] == True
        assert feed_start_data["command_type"] == "feeding_event"
        assert "Recorded feeding start" in feed_start_data["response"]

        # 4. Record feeding end
        feed_end_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "finished feeding at 11:35",
                "thread_id": TEST_THREAD_ID,
                "language": "en"
            }
        )
        assert feed_end_response.status_code == 200
        feed_end_data = feed_end_response.json()
        assert feed_end_data["command_processed"] == True
        assert feed_end_data["command_type"] == "feeding_event"
        assert "Recorded feeding end" in feed_end_data["response"]

        # 5. Get summary
        summary_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "show me today's summary",
                "thread_id": TEST_THREAD_ID,
                "language": "en"
            }
        )
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        assert summary_data["command_processed"] == True
        assert "Summary for day" in summary_data["response"]
        assert "Sleep" in summary_data["response"]
        assert "Feeding" in summary_data["response"]

        # 6. Verify analytics endpoints
        # Daily stats
        daily_stats = await client.get(f"{BASE_URL}/api/analytics/daily")
        assert daily_stats.status_code == 200
        daily_data = daily_stats.json()
        assert "sleep" in daily_data
        assert "feeding" in daily_data

        # Weekly stats
        weekly_stats = await client.get(f"{BASE_URL}/api/analytics/weekly")
        assert weekly_stats.status_code == 200
        weekly_data = weekly_stats.json()
        assert "sleep" in weekly_data
        assert "feeding" in weekly_data

        # Pattern stats
        pattern_stats = await client.get(f"{BASE_URL}/api/analytics/patterns")
        assert pattern_stats.status_code == 200
        pattern_data = pattern_stats.json()
        assert "sleep_patterns" in pattern_data or "feeding_patterns" in pattern_data

async def test_chat_workflow():
    """Test the chat workflow for non-command messages"""
    async with httpx.AsyncClient() as client:
        # 1. General advice question
        advice_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "What's a good sleep schedule for a 3-month-old baby?",
                "thread_id": "chat_test_123",
                "language": "en"
            }
        )
        assert advice_response.status_code == 200
        advice_data = advice_response.json()
        assert advice_data["command_processed"] == False
        assert advice_data["command_type"] is None
        assert len(advice_data["response"]) > 0

        # 2. Follow-up question
        followup_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "How many naps should they take during the day?",
                "thread_id": "chat_test_123",
                "language": "en"
            }
        )
        assert followup_response.status_code == 200
        followup_data = followup_response.json()
        assert followup_data["command_processed"] == False
        assert followup_data["command_type"] is None
        assert len(followup_data["response"]) > 0

        # 3. Question about feeding
        feeding_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "How often should I feed my baby?",
                "thread_id": "chat_test_123",
                "language": "en"
            }
        )
        assert feeding_response.status_code == 200
        feeding_data = feeding_response.json()
        assert feeding_data["command_processed"] == False
        assert feeding_data["command_type"] is None
        assert len(feeding_data["response"]) > 0

async def test_multilingual_support():
    """Test both workflows with Hebrew language"""
    async with httpx.AsyncClient() as client:
        # 1. Hebrew sleep command
        hebrew_sleep_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "התינוק הלך לישון ב-20:30",
                "thread_id": "hebrew_test_123",
                "language": "he"
            }
        )
        assert hebrew_sleep_response.status_code == 200
        hebrew_sleep_data = hebrew_sleep_response.json()
        assert hebrew_sleep_data["command_processed"] == True
        assert hebrew_sleep_data["command_type"] == "sleep_event"
        assert "רשמתי" in hebrew_sleep_data["response"]

        # 2. Hebrew chat question
        hebrew_chat_response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "מה לוח הזמנים המומלץ לתינוק בן 3 חודשים?",
                "thread_id": "hebrew_test_123",
                "language": "he"
            }
        )
        assert hebrew_chat_response.status_code == 200
        hebrew_chat_data = hebrew_chat_response.json()
        assert hebrew_chat_data["command_processed"] == False
        assert hebrew_chat_data["command_type"] is None
        assert len(hebrew_chat_data["response"]) > 0

async def main():
    """Run all tests"""
    print("\nTesting Routine Tracking Workflow...")
    await test_routine_tracking_workflow()
    print("✓ Routine tracking tests passed")

    print("\nTesting Chat Workflow...")
    await test_chat_workflow()
    print("✓ Chat workflow tests passed")

    print("\nTesting Multilingual Support...")
    await test_multilingual_support()
    print("✓ Multilingual support tests passed")

if __name__ == "__main__":
    asyncio.run(main()) 