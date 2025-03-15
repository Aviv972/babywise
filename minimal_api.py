#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, Optional, Any, List
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for testing
_memory_cache = {}

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": "3.12",
        }
    }

# Minimal chat endpoint
@app.post("/api/chat")
async def chat(request: Request):
    """Minimal chat endpoint that returns a static response"""
    try:
        body = await request.json()
        message = body.get("message", "")
        thread_id = body.get("thread_id", "thread_12345")

        # Log the received message
        logger.info(f"Received message: {message} for thread: {thread_id}")
        
        # Return a static response based on the message content
        if "סיכום" in message or "summary" in message.lower():
            return {
                "response": "זהו API מינימלי לבדיקת פריסה. סיכומי השגרה אינם זמינים כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                "thread_id": thread_id
            }
        elif "שינה" in message or "sleep" in message.lower():
            return {
                "response": "זהו API מינימלי לבדיקת פריסה. מעקב שינה אינו זמין כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                "thread_id": thread_id 
            }
        elif "האכלה" in message or "feed" in message.lower():
            return {
                "response": "זהו API מינימלי לבדיקת פריסה. מעקב האכלה אינו זמין כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                "thread_id": thread_id
            }
        else:
            return {
                "response": "זהו API מינימלי לבדיקת פריסה. המערכת האינטליגנטית המלאה אינה זמינה כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                "thread_id": thread_id
            }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Chat reset endpoint
@app.post("/api/chat/reset")
async def reset_chat(request: Request):
    """Reset chat endpoint"""
    try:
        body = await request.json()
        thread_id = body.get("thread_id", "thread_12345")
        logger.info(f"Reset chat for thread: {thread_id}")
        return {
            "status": "ok",
            "message": "Chat reset successful (minimal API)",
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error in reset chat endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Context endpoint
@app.get("/api/chat/context")
async def get_context(request: Request):
    """Get context endpoint"""
    try:
        thread_id = request.query_params.get("thread_id", "thread_12345")
        logger.info(f"Get context for thread: {thread_id}")
        return {
            "context": [],
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error in get context endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Routine events endpoint
@app.post("/api/routines/events")
async def add_routine_event(request: Request):
    """Add routine event endpoint"""
    try:
        body = await request.json()
        thread_id = body.get("thread_id", "thread_12345")
        event_type = body.get("event_type", "unknown")
        logger.info(f"Add routine event for thread: {thread_id}, type: {event_type}")
        return {
            "status": "ok", 
            "message": "Event added successfully (minimal API)",
            "event_id": f"mock_{int(time.time())}",
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error in add routine event endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/routines/events")
async def get_routine_events(request: Request):
    """Get routine events endpoint"""
    try:
        thread_id = request.query_params.get("thread_id", "thread_12345")
        logger.info(f"Get routine events for thread: {thread_id}")
        return {
            "events": [],
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error in get routine events endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/routines/summary/{thread_id}")
async def get_routine_summary(thread_id: str, request: Request):
    """Get routine summary endpoint"""
    try:
        period = request.query_params.get("period", "day")
        logger.info(f"Get routine summary for thread: {thread_id}, period: {period}")
        return {
            "summary": {
                "sleep": [],
                "feed": [],
                "total_sleep_minutes": 0,
                "total_feed_count": 0,
                "period": period
            },
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Error in get routine summary endpoint: {str(e)}")
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Root path handler
@app.get("/", response_class=HTMLResponse)
async def root():
    """Return a simple HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0;url=/index.html">
        <title>Redirecting...</title>
    </head>
    <body>
        <p>Redirecting to app...</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Redis test endpoint
@app.get("/api/redis-test")
async def redis_test():
    """Test Redis connectivity"""
    try:
        import redis.asyncio
        redis_url = os.environ.get("UPSTASH_REDIS_URL", os.environ.get("STORAGE_URL"))
        if not redis_url:
            return {"status": "error", "message": "Redis URL not configured"}
            
        client = await redis.asyncio.from_url(
            redis_url, 
            decode_responses=True,
            socket_timeout=3.0
        )
        await client.ping()
        return {"status": "ok", "message": "Redis connection successful"}
    except Exception as e:
        logger.error(f"Redis test error: {str(e)}")
        return {"status": "error", "message": f"Redis connection failed: {str(e)}"}

# Mount static files for local development
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Mounted static directory")
except Exception as e:
    logger.warning(f"Could not mount static directory: {str(e)}")

# Enable direct running
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 