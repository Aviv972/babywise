"""
Babywise Assistant - Analytics API Router

This module implements the analytics-related API endpoints.
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.services.analytics_service import (
    get_daily_stats,
    get_weekly_stats,
    get_pattern_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/daily")
async def get_daily_analytics(date: Optional[str] = None):
    """
    Get daily analytics for a specific date
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        stats = await get_daily_stats(target_date)
        return stats
    except Exception as e:
        logger.error(f"Error getting daily analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/weekly")
async def get_weekly_analytics(date: Optional[str] = None):
    """
    Get weekly analytics for the week containing the specified date
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        stats = await get_weekly_stats(target_date)
        return stats
    except Exception as e:
        logger.error(f"Error getting weekly analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns")
async def get_pattern_analytics():
    """
    Get pattern analytics for sleep and feeding routines
    """
    try:
        stats = await get_pattern_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting pattern analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 