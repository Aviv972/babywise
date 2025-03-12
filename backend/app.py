"""
Babywise Assistant - Main Application

This module defines the main FastAPI application, including all routes and middleware.
It serves both the API endpoints and static frontend files.
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
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

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses"""
    request_id = str(hash(request))[:8]  # Create a short unique ID for this request
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"Request {request_id} completed: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request {request_id} failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)}
        )

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint that tests Redis and database connectivity"""
    try:
        # Test results
        results = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "environment": {
                "vercel": os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel'),
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            }
        }
        
        # Check Redis connection
        try:
            from backend.services.redis_service import test_redis_connection
            redis_status = await test_redis_connection()
            results["services"]["redis"] = "connected" if redis_status else "disconnected"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            results["services"]["redis"] = f"error: {str(e)}"
        
        # Check database
        try:
            from backend.db.routine_tracker import check_db_connection
            db_status = check_db_connection()
            results["services"]["database"] = "connected" if db_status else "disconnected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            results["services"]["database"] = f"error: {str(e)}"
        
        # Check workflow
        try:
            from backend.workflow.workflow import get_workflow
            workflow = await get_workflow()
            results["services"]["workflow"] = "initialized" if workflow else "uninitialized"
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            results["services"]["workflow"] = f"error: {str(e)}"
        
        # Update overall status
        if any(status.startswith("error") for status in results["services"].values()):
            results["status"] = "error"
        elif any(status == "disconnected" for status in results["services"].values()):
            results["status"] = "degraded"
        
        return JSONResponse(results)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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
    # Import Redis service - without maintaining connections
    try:
        from backend.services.redis_service import test_redis_connection
        logger.info("Testing Redis connection...")
        redis_ok = await test_redis_connection()
        if redis_ok:
            logger.info("✅ Redis connection test passed")
        else:
            logger.warning("⚠️ Redis connection test failed - some features may not work properly")
    except Exception as e:
        logger.error(f"❌ Redis initialization error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Initialize database - without maintaining connections
    try:
        from backend.db.routine_tracker import init_db, check_db_connection
        
        # Initialize database
        logger.info("Initializing database...")
        db_success = init_db()
        if db_success:
            logger.info("✅ Database initialized successfully")
        else:
            logger.warning("⚠️ Database initialization failed - some features may not work properly")
            
        # Test database connection
        db_connection = check_db_connection()
        if db_connection:
            logger.info("✅ Database connection verified")
        else:
            logger.warning("⚠️ Database connection check failed - routine tracking may not work properly")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    # Initialize workflow
    try:
        from backend.workflow.workflow import get_workflow
        logger.info("Initializing workflow...")
        workflow = await get_workflow()
        if workflow:
            logger.info("✅ Workflow initialized successfully")
        else:
            logger.warning("⚠️ Workflow initialization failed - chat features may not work properly")
    except Exception as e:
        logger.error(f"❌ Workflow initialization error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    # Log startup complete
    logger.info("✅ Application startup complete") 