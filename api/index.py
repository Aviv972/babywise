"""
Babywise Assistant - Vercel Serverless Function Entry Point

This module serves as the entry point for Vercel serverless functions.
It imports the FastAPI app from the backend and exposes it for Vercel deployment.

The module follows the project's asynchronous programming guidelines and
provides proper error handling for the serverless environment.
"""

import sys
import os
import logging
import importlib
import base64
from pathlib import Path
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path first
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
logger.info(f"Added {root_dir} to Python path")

# Ensure environment variables are set directly
# Vercel's filesystem is read-only, so we can't create .env files
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
os.environ.setdefault("STORAGE_URL", os.environ.get("STORAGE_URL", ""))

# Import compatibility module to apply patches before any other imports
try:
    logger.info("Importing compatibility module")
    from api.compatibility import patch_results
    logger.info(f"Compatibility patches applied: {patch_results}")
except Exception as e:
    logger.error(f"Failed to import compatibility module: {str(e)}")
    logger.error(traceback.format_exc()) 