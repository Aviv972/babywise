<<<<<<< HEAD
"""
Babywise Assistant - Vercel Entry Point

This module serves as the entry point for Vercel serverless deployment.
It imports and exposes the FastAPI application.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
=======
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import os
import logging
>>>>>>> 64a3e7edaee2f1f0d035ab9cce454790894bc3ab

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Import the FastAPI app from server.py
from server import app

# This is required for Vercel serverless deployment
=======
# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_environment():
    """Check and log environment variables status"""
    logger.info("=== Vercel Environment Check ===")
    required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY']
    missing_vars = []
    
    # Check required variables
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

    # Check optional MODEL_NAME with default
    model_name = os.getenv('MODEL_NAME', 'gpt-4o-mini')
    logger.info(f"MODEL_NAME: {model_name} (using default if not set)")
    os.environ['MODEL_NAME'] = model_name  # Set the default value if not present

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Environment check completed successfully")

# Check environment variables before importing app
check_environment()

# Import app after environment check
logger.info("Attempting to import FastAPI app...")
try:
    from src.server import app
    logger.info("Successfully imported FastAPI app")
except Exception as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
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
>>>>>>> 64a3e7edaee2f1f0d035ab9cce454790894bc3ab
app = app 