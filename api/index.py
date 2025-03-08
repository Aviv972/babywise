import sys
import os
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_app")

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Log environment info
python_version = sys.version
current_dir = os.getcwd()
dir_contents = os.listdir()
logger.info(f"Python version: {python_version}")
logger.info(f"Current directory: {current_dir}")
logger.info(f"Directory contents: {dir_contents}")

# Initialize service status
redis_status = False
db_status = False
workflow_status = False
initialization_complete = False

# Async initialization function with timeout
async def initialize_services():
    global redis_status, db_status, workflow_status, initialization_complete
    
    try:
        # Initialize Redis with timeout
        try:
            logger.info("Attempting to initialize Redis...")
            # Use asyncio.wait_for to add a timeout
            from backend.services.redis_service import ensure_redis_initialized
            redis_status = await asyncio.wait_for(ensure_redis_initialized(), timeout=5.0)
            logger.info(f"Redis initialization {'successful' if redis_status else 'failed'}")
        except asyncio.TimeoutError:
            logger.warning("Redis initialization timed out after 5 seconds")
            redis_status = False
        except Exception as e:
            logger.error(f"Redis initialization error: {str(e)}", exc_info=True)
            redis_status = False
    
        # Initialize database
        try:
            logger.info("Attempting to initialize database...")
            from backend.db.routine_tracker import check_db_connection
            db_status = check_db_connection()
            logger.info(f"Database initialization {'successful' if db_status else 'failed'}")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}", exc_info=True)
            db_status = False
    
        # Initialize workflow
        try:
            logger.info("Attempting to initialize workflow...")
            from backend.workflow.workflow import get_workflow
            workflow = await asyncio.wait_for(get_workflow(), timeout=5.0)
            workflow_status = workflow is not None
            logger.info(f"Workflow initialization {'successful' if workflow_status else 'failed'}")
        except asyncio.TimeoutError:
            logger.warning("Workflow initialization timed out after 5 seconds")
            workflow_status = False
        except Exception as e:
            logger.error(f"Workflow initialization error: {str(e)}", exc_info=True)
            workflow_status = False
    
    except Exception as e:
        logger.error(f"Overall initialization error: {str(e)}", exc_info=True)
    
    # Mark initialization as complete regardless of success/failure
    initialization_complete = True
    logger.info("Service initialization completed")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok" if redis_status and db_status and workflow_status else "degraded",
        "timestamp": datetime.now().isoformat(),
        "initialization_complete": initialization_complete,
        "services": {
            "redis": "connected" if redis_status else "disconnected",
            "database": "connected" if db_status else "disconnected",
            "workflow": "initialized" if workflow_status else "uninitialized"
        }
    })

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "message": "Babywise API is running",
        "initialization_complete": initialization_complete,
        "environment": {
            "python_version": python_version,
            "current_directory": current_dir,
            "services": {
                "redis": "connected" if redis_status else "disconnected",
                "database": "connected" if db_status else "disconnected",
                "workflow": "initialized" if workflow_status else "uninitialized"
            }
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )

# Import API routers with fallback
try:
    from backend.api.chat import router as chat_router
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    logger.info("Chat router initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize chat router: {str(e)}", exc_info=True)

try:
    from backend.api.routines import router as routines_router
    app.include_router(routines_router, prefix="/api/routines", tags=["routines"])
    logger.info("Routines router initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize routines router: {str(e)}", exc_info=True)

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Start initialization in background task
    asyncio.create_task(initialize_services())
    logger.info("Service initialization started in background")

# This is required for Vercel serverless deployment
app = app 