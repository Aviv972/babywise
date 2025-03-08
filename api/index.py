"""
Babywise Assistant - API Entry Point

This module serves as the entry point for the Vercel serverless function.
It initializes the FastAPI application and handles routing.
"""

import sys
import os
import logging
import asyncio
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vercel_app")

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Log environment info
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir()}")

# Create FastAPI app
app = FastAPI(
    title="Babywise Assistant",
    description="A chatbot for baby care advice and routine tracking",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - customize for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": sys.version
        }
    })

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "message": "Babywise API is running",
        "environment": {
            "python_version": sys.version
        }
    }

# Test Redis connection
@app.get("/api/test-redis")
async def test_redis():
    """Test Redis connection"""
    try:
        import aioredis
        
        # Get Redis URL from environment
        redis_url = os.getenv("STORAGE_URL")
        if not redis_url:
            return {"status": "error", "message": "Redis URL not found in environment variables"}
        
        # Mask credentials for logging
        masked_url = redis_url.replace(redis_url.split('@')[0], '***:***@')
        logger.info(f"Attempting to connect to Redis at {masked_url}")
        
        # Use asyncio.wait_for to add a timeout
        start_time = datetime.now()
        redis_client = await asyncio.wait_for(
            aioredis.from_url(redis_url, socket_timeout=5.0),
            timeout=5.0
        )
        
        # Test connection by pinging Redis
        ping_result = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        
        # Test basic operations
        await redis_client.set("test_key", "test_value", ex=60)
        value = await redis_client.get("test_key")
        
        # Close connection
        await redis_client.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "status": "success",
            "ping_result": ping_result,
            "test_value": value.decode() if value else None,
            "duration_seconds": duration
        }
        
    except asyncio.TimeoutError as e:
        logger.error(f"Redis connection timed out: {str(e)}")
        return {"status": "error", "message": f"Redis connection timed out: {str(e)}"}
    except Exception as e:
        logger.error(f"Error connecting to Redis: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Error connecting to Redis: {str(e)}"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )

# This is required for Vercel serverless deployment
app = app 