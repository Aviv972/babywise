"""
Babywise Assistant - Main Application

This module defines the main FastAPI application, including all routes and middleware.
It serves both the API endpoints and static frontend files.
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
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
    try:
        # Check Redis connection
        from backend.services.redis_service import ensure_redis_initialized
        redis_status = await ensure_redis_initialized()
        
        # Check database
        from backend.db.routine_tracker import check_db_connection
        db_status = check_db_connection()
        
        return JSONResponse({
            "status": "ok" if redis_status and db_status else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": "connected" if redis_status else "disconnected",
                "database": "connected" if db_status else "disconnected"
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status_code=500)

# Import API routers
from backend.api.chat import router as chat_router
from backend.api.routines import router as routines_router
from backend.api.analytics import router as analytics_router
from backend.api.routine_endpoints import router as routine_endpoints_router

# Include API routers - mount before static files
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(routines_router, prefix="/api/routines", tags=["routines"])
app.include_router(routine_endpoints_router, prefix="/api", tags=["routine"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

# Determine static file directories
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

# Ensure frontend directory exists
if not FRONTEND_DIR.exists():
    logger.error(f"Frontend directory not found at {FRONTEND_DIR}")
    raise RuntimeError(f"Frontend directory not found at {FRONTEND_DIR}")

# Mount frontend files at root - must be last
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Import Redis service
    try:
        from backend.services.redis_service import initialize_redis, test_redis_connection
        
        # Initialize Redis
        await initialize_redis()
        
        # Test Redis connection
        redis_ok = await test_redis_connection()
        if not redis_ok:
            logger.warning("Redis connection test failed - some features may not work properly")
        else:
            logger.info("Redis initialized successfully")
    except Exception as e:
        logger.error(f"Redis initialization error: {e}")
        logger.warning("Redis initialization failed - some features may not work properly")
    
    # Initialize database
    try:
        from backend.db.routine_tracker import init_db, check_db_connection
        
        # Initialize database
        db_success = init_db()
        if not db_success:
            logger.warning("Database initialization failed - some features may not work properly")
        else:
            logger.info("Database initialized successfully")
            
        # Test database connection
        if check_db_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Database connection check failed - routine tracking may not work properly")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.warning("Database initialization failed - routine tracking may not work properly")
        
    # Initialize workflow
    try:
        from backend.workflow.workflow import get_workflow
        workflow = await get_workflow()
        if workflow:
            logger.info("Workflow initialized successfully")
        else:
            logger.warning("Workflow initialization failed - chat features may not work properly")
    except Exception as e:
        logger.error(f"Workflow initialization error: {e}")
        logger.warning("Workflow initialization failed - chat features may not work properly") 