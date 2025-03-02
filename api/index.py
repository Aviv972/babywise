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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the FastAPI app from server.py
from server import app

# This is required for Vercel serverless deployment
app = app 