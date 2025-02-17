from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_environment():
    """Check and log environment variables status"""
    logger.info("=== Vercel Environment Check ===")
    required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'MODEL_NAME']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        is_present = bool(value)
        logger.info(f"{var} present: {is_present}")
        if not is_present:
            missing_vars.append(var)
            logger.error(f"Missing required environment variable: {var}")
        elif var in ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY']:
            # Log first few characters of API keys to verify they're correct
            logger.info(f"{var} starts with: {value[:4]}...")

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

# Check environment variables before importing app
check_environment()

try:
    logger.info("Attempting to import FastAPI app...")
    from src.server import app
    logger.info("Successfully imported FastAPI app")
except Exception as e:
    logger.error(f"Error importing app: {str(e)}", exc_info=True)
    raise

# This file is used by Vercel as the entry point
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Vercel entry point initialization complete")

# Export for Vercel
app = app 