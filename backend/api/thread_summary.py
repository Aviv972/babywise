#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Thread Summary Module

This module provides functionality for generating thread summaries.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def thread_summary_fallback(thread_id: str, request: Request, backend_available: bool = False):
    """
    Fallback function for thread summary when the backend is not available.
    
    Args:
        thread_id: The ID of the thread to summarize
        request: The FastAPI request object
        backend_available: Whether the backend is available
        
    Returns:
        JSONResponse with thread summary or error message
    """
    logger.info(f"Thread summary fallback called for thread {thread_id}")
    
    if backend_available:
        try:
            # Attempt to get summary from backend
            return JSONResponse({
                "summary": "Thread summary is not available at this time.",
                "status": "fallback"
            })
        except Exception as e:
            logger.error(f"Error in thread summary fallback: {str(e)}")
            return JSONResponse({
                "error": f"Failed to generate thread summary: {str(e)}",
                "status": "error"
            })
    else:
        return JSONResponse({
            "error": "Backend services are currently unavailable",
            "status": "error"
        }) 