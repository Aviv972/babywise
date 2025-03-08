import sys
import os
import logging
import asyncio
import traceback
import platform
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
python_version = sys.version
current_dir = os.getcwd()
dir_contents = os.listdir()
logger.info(f"Python version: {python_version}")
logger.info(f"Platform: {platform.platform()}")
logger.info(f"Current directory: {current_dir}")
logger.info(f"Directory contents: {dir_contents}")

# Check for Redis URL
redis_url = os.getenv("STORAGE_URL")
if redis_url:
    # Mask credentials for logging
    masked_url = redis_url.replace(redis_url.split('@')[0], '***:***@')
    logger.info(f"Redis URL found: {masked_url}")
else:
    logger.warning("Redis URL not found in environment variables")

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

# Initialize service status
redis_status = False
db_status = False
workflow_status = False
initialization_complete = False
initialization_error = None

# Async initialization function with timeout
async def initialize_services():
    global redis_status, db_status, workflow_status, initialization_complete, initialization_error
    
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
            logger.error(f"Redis initialization error: {str(e)}")
            logger.error(traceback.format_exc())
            redis_status = False
    
        # Initialize database
        try:
            logger.info("Attempting to initialize database...")
            from backend.db.routine_tracker import check_db_connection
            db_status = check_db_connection()
            logger.info(f"Database initialization {'successful' if db_status else 'failed'}")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            logger.error(traceback.format_exc())
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
            logger.error(f"Workflow initialization error: {str(e)}")
            logger.error(traceback.format_exc())
            workflow_status = False
    
    except Exception as e:
        logger.error(f"Overall initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        initialization_error = str(e)
    
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
        "initialization_error": initialization_error,
        "services": {
            "redis": "connected" if redis_status else "disconnected",
            "database": "connected" if db_status else "disconnected",
            "workflow": "initialized" if workflow_status else "uninitialized"
        },
        "environment": {
            "python_version": python_version,
            "platform": platform.platform(),
            "redis_url_configured": redis_url is not None
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
        "initialization_error": initialization_error,
        "environment": {
            "python_version": python_version,
            "platform": platform.platform(),
            "current_directory": current_dir,
            "redis_url_configured": redis_url is not None,
            "services": {
                "redis": "connected" if redis_status else "disconnected",
                "database": "connected" if db_status else "disconnected",
                "workflow": "initialized" if workflow_status else "uninitialized"
            }
        }
    }

# Test Redis connection directly
@app.get("/api/test-redis")
async def test_redis():
    """Test Redis connection directly"""
    start_time = datetime.now()
    connection_info = {}
    
    try:
        import aioredis
        import socket
        
        # Get Redis URL from environment
        redis_url = os.getenv("STORAGE_URL")
        if not redis_url:
            return {"status": "error", "message": "Redis URL not found in environment variables"}
        
        # Parse Redis URL for connection info
        try:
            # Mask credentials for logging and response
            masked_url = redis_url.replace(redis_url.split('@')[0], '***:***@')
            logger.info(f"Test endpoint: Attempting to connect to Redis at {masked_url}")
            
            # Extract host and port for additional tests
            host_port = redis_url.split('@')[-1].split('/')[0]
            host = host_port.split(':')[0]
            port = int(host_port.split(':')[1]) if ':' in host_port else 6379
            
            connection_info = {
                "host": host,
                "port": port,
                "url": masked_url
            }
            
            # Try to resolve DNS
            try:
                logger.info(f"Resolving DNS for {host}")
                ip_address = socket.gethostbyname(host)
                connection_info["ip_address"] = ip_address
                connection_info["dns_resolved"] = True
                logger.info(f"DNS resolved: {host} -> {ip_address}")
            except Exception as e:
                logger.error(f"DNS resolution failed: {str(e)}")
                connection_info["dns_resolved"] = False
                connection_info["dns_error"] = str(e)
        except Exception as e:
            logger.error(f"Error parsing Redis URL: {str(e)}")
            connection_info["parsing_error"] = str(e)
        
        # Use asyncio.wait_for to add a timeout
        logger.info("Creating Redis client...")
        redis_client = await asyncio.wait_for(
            aioredis.from_url(redis_url, socket_timeout=5.0),
            timeout=5.0
        )
        connection_info["client_created"] = True
        
        # Test connection by pinging Redis
        logger.info("Pinging Redis...")
        ping_start = datetime.now()
        ping_result = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        ping_duration = (datetime.now() - ping_start).total_seconds()
        connection_info["ping_successful"] = ping_result
        connection_info["ping_duration_seconds"] = ping_duration
        
        # Test basic operations
        logger.info("Testing SET operation...")
        set_start = datetime.now()
        await redis_client.set("test_key", "test_value", ex=60)
        set_duration = (datetime.now() - set_start).total_seconds()
        connection_info["set_duration_seconds"] = set_duration
        
        logger.info("Testing GET operation...")
        get_start = datetime.now()
        value = await redis_client.get("test_key")
        get_duration = (datetime.now() - get_start).total_seconds()
        connection_info["get_duration_seconds"] = get_duration
        connection_info["test_value"] = value.decode() if value else None
        
        # Close connection
        await redis_client.close()
        logger.info("Redis connection closed")
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_duration_seconds": total_duration,
            "connection_info": connection_info,
            "environment": {
                "python_version": python_version,
                "platform": platform.platform()
            }
        }
        
    except asyncio.TimeoutError as e:
        logger.error(f"Redis test timeout: {str(e)}")
        end_time = datetime.now()
        return {
            "status": "error", 
            "message": f"Redis connection timed out: {str(e)}",
            "duration_seconds": (end_time - start_time).total_seconds(),
            "connection_info": connection_info,
            "environment": {
                "python_version": python_version,
                "platform": platform.platform()
            }
        }
    except Exception as e:
        logger.error(f"Redis test error: {str(e)}")
        logger.error(traceback.format_exc())
        end_time = datetime.now()
        return {
            "status": "error", 
            "message": f"Error connecting to Redis: {str(e)}",
            "duration_seconds": (end_time - start_time).total_seconds(),
            "connection_info": connection_info,
            "error_traceback": traceback.format_exc(),
            "environment": {
                "python_version": python_version,
                "platform": platform.platform()
            }
        }

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

# Import API routers with fallback
try:
    from backend.api.chat import router as chat_router
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    logger.info("Chat router initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize chat router: {str(e)}")
    logger.error(traceback.format_exc())

try:
    from backend.api.routines import router as routines_router
    app.include_router(routines_router, prefix="/api/routines", tags=["routines"])
    logger.info("Routines router initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize routines router: {str(e)}")
    logger.error(traceback.format_exc())

# Startup event to initialize services
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Start initialization in background task
    asyncio.create_task(initialize_services())
    logger.info("Service initialization started in background")

# This is required for Vercel serverless deployment
app = app 