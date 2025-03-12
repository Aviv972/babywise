"""
Babywise Assistant - Main Application

This module defines the main FastAPI application, including all routes and middleware.
It serves both the API endpoints and static frontend files.
"""

import os
import logging
import sys
import traceback
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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
    start_time = datetime.now()
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Request {request_id} failed with error: {str(e)} after {process_time:.3f}s")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)}
        )

# Enhanced health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint that tests all service components"""
    start_time = datetime.now()
    try:
        # Test results
        results = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "environment": {
                "vercel": os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel'),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "event_loop": str(asyncio.get_running_loop()),
                "serverless": os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None or os.environ.get('VERCEL', '0') == '1'
            }
        }
        
        # Check Redis connection - completely isolated
        try:
            from backend.services.redis_service import test_redis_connection
            redis_status = await test_redis_connection()
            results["services"]["redis"] = {
                "status": "connected" if redis_status else "disconnected",
                "url_configured": bool(os.environ.get("STORAGE_URL")),
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            results["services"]["redis"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check database - completely isolated
        try:
            from backend.db.routine_tracker import check_db_connection
            db_status = check_db_connection()
            results["services"]["database"] = {
                "status": "connected" if db_status else "disconnected",
                "type": "SQLite"
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            results["services"]["database"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check workflow - completely isolated
        try:
            from backend.workflow.workflow import get_workflow
            workflow = await get_workflow()
            results["services"]["workflow"] = {
                "status": "initialized" if workflow else "uninitialized",
                "api_key_configured": bool(os.environ.get("OPENAI_API_KEY"))
            }
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            results["services"]["workflow"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Check thread state access
        try:
            from backend.services.redis_service import get_thread_state, save_thread_state
            test_thread_id = "health-check-thread"
            test_data = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # Test write
            save_result = await save_thread_state(test_thread_id, test_data)
            
            # Test read
            read_result = await get_thread_state(test_thread_id)
            
            results["services"]["thread_state"] = {
                "status": "working" if save_result and read_result and read_result.get("test") is True else "failing",
                "write_success": bool(save_result),
                "read_success": bool(read_result)
            }
        except Exception as e:
            logger.error(f"Thread state health check failed: {e}")
            results["services"]["thread_state"] = {
                "status": "error", 
                "error": str(e),
                "traceback": traceback.format_exc().split("\n")[-5:]
            }
        
        # Overall status determination
        service_statuses = [s.get("status") for s in results["services"].values()]
        if any(status == "error" for status in service_statuses):
            results["status"] = "error"
        elif any(status in ["disconnected", "failing", "uninitialized"] for status in service_statuses):
            results["status"] = "degraded"
        else:
            results["status"] = "ok"
            
        # Performance metrics
        process_time = (datetime.now() - start_time).total_seconds()
        results["performance"] = {
            "health_check_duration_seconds": process_time
        }
        
        return JSONResponse(results)
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Health check failed: {str(e)} after {process_time:.3f}s")
        logger.error(traceback.format_exc())
        return JSONResponse({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "traceback": traceback.format_exc().split("\n")[-10:],
            "duration_seconds": process_time
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

# Startup event with enhanced isolation
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup with complete isolation"""
    startup_start = datetime.now()
    logger.info("🚀 Application starting up...")
    
    # Record environment information
    env_info = {
        "vercel": os.environ.get('VERCEL', '0') == '1' or os.path.exists('/.vercel'),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "event_loop_type": str(type(asyncio.get_running_loop())),
        "serverless": os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None or os.environ.get('VERCEL', '0') == '1'
    }
    logger.info(f"Environment: {env_info}")
    
    # Test Redis connection - completely isolated
    try:
        from backend.services.redis_service import test_redis_connection
        logger.info("Testing Redis connection...")
        redis_ok = await test_redis_connection()
        if redis_ok:
            logger.info("✅ Redis connection test passed")
        else:
            logger.warning("⚠️ Redis connection test failed - some features may not work properly")
            # Check if Redis URL is configured
            redis_url = os.environ.get("STORAGE_URL")
            if not redis_url:
                logger.error("❌ No Redis URL configured in STORAGE_URL environment variable")
            else:
                logger.info(f"Redis URL is configured (masked): {redis_url[:10]}...{redis_url[-5:]}")
    except Exception as e:
        logger.error(f"❌ Redis initialization error: {e}")
        logger.error(traceback.format_exc())
    
    # Initialize database - completely isolated
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
        logger.error(traceback.format_exc())
        
    # Initialize workflow - completely isolated
    try:
        from backend.workflow.workflow import get_workflow
        logger.info("Initializing workflow...")
        workflow = await get_workflow()
        if workflow:
            logger.info("✅ Workflow initialized successfully")
        else:
            logger.warning("⚠️ Workflow initialization failed - chat features may not work properly")
            # Check if OpenAI API key is configured
            openai_key = os.environ.get("OPENAI_API_KEY")
            if not openai_key:
                logger.error("❌ No OpenAI API key configured in OPENAI_API_KEY environment variable")
            else:
                logger.info("OpenAI API key is configured (masked)")
    except Exception as e:
        logger.error(f"❌ Workflow initialization error: {e}")
        logger.error(traceback.format_exc())
    
    # Test thread state - completely isolated
    try:
        from backend.services.redis_service import get_thread_state, save_thread_state
        logger.info("Testing thread state storage...")
        test_thread_id = "startup-test-thread"
        test_data = {"test": True, "startup_time": datetime.now().isoformat()}
        
        # Test write
        save_result = await save_thread_state(test_thread_id, test_data)
        if save_result:
            logger.info("✅ Thread state write test passed")
        else:
            logger.warning("⚠️ Thread state write test failed")
        
        # Test read
        read_result = await get_thread_state(test_thread_id)
        if read_result and read_result.get("test") is True:
            logger.info("✅ Thread state read test passed")
        else:
            logger.warning("⚠️ Thread state read test failed")
    except Exception as e:
        logger.error(f"❌ Thread state test error: {e}")
        logger.error(traceback.format_exc())
        
    # Log startup complete with timing
    startup_duration = (datetime.now() - startup_start).total_seconds()
    logger.info(f"✅ Application startup complete in {startup_duration:.3f}s") 