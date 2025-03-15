#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, Optional, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
    return {
        "status": "ok",
        "timestamp": "2024-03-15T12:00:00Z",
        "environment": {
            "python_version": "3.12",
        }
    }

# Minimal chat endpoint
@app.post("/api/chat")
async def chat(request: Request):
    """Minimal chat endpoint that returns a static response"""
    body = await request.json()
    message = body.get("message", "")
    thread_id = body.get("thread_id", "thread_12345")

    # Log the received message
    logger.info(f"Received message: {message} for thread: {thread_id}")
    
    # In a real implementation, this would call the LangChain workflow
    # but for deployment testing we'll return a static response
    return {
        "response": "This is a minimal API deployment test. The full AI processing is temporarily unavailable while we optimize the deployment.",
        "thread_id": thread_id
    }

# Root path handler
@app.get("/")
async def root():
    """Return a simple HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Babywise Assistant API - Minimal Version</title>
    </head>
    <body>
        <h1>Babywise Assistant API - Minimal Version</h1>
        <p>This is a minimal version of the API for deployment testing.</p>
    </body>
    </html>
    """
    return html_content

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

# Enable direct running
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 