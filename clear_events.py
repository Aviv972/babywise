#!/usr/bin/env python3
"""
Script to clear all events from the database
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path - match the path in routine_tracker.py
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "data", "routine_tracker.db")
logger.info(f"Using database at: {DB_PATH}")

def clear_events():
    """Delete all events from the database"""
    try:
        # Check if database file exists
        if not os.path.exists(DB_PATH):
            logger.error(f"Database file not found at {DB_PATH}")
            return False
            
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get count of events before deletion
        cursor.execute("SELECT COUNT(*) FROM routine_events")
        count_before = cursor.fetchone()[0]
        logger.info(f"Found {count_before} events in the database")
        
        # Delete all events
        cursor.execute("DELETE FROM routine_events")
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM routine_events")
        count_after = cursor.fetchone()[0]
        
        logger.info(f"Deleted {count_before - count_after} events. {count_after} events remaining.")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing events: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting database cleanup...")
    success = clear_events()
    if success:
        logger.info("Database cleanup completed successfully")
    else:
        logger.error("Database cleanup failed") 