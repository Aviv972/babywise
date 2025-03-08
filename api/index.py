"""
Babywise Assistant - Vercel Serverless Function Entry Point

This module serves as a lightweight proxy entry point for Vercel serverless functions.
Instead of importing the full application, it forwards requests to the backend API.
"""

import os
import logging
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend URL from environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "https://babywise-backend.vercel.app")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info(f"Using backend URL: {BACKEND_URL}")

# Create a minimal FastAPI app
app = FastAPI(title="Babywise API Proxy")

# Create an HTTP client for forwarding requests
http_client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for LLM operations

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if we can connect to the backend
        response = await http_client.get(f"{BACKEND_URL}/api/health")
        if response.status_code == 200:
            return {
                "status": "ok", 
                "service": "Babywise API Proxy",
                "backend_status": "connected",
                "backend_url": BACKEND_URL
            }
        else:
            return {
                "status": "warning",
                "service": "Babywise API Proxy",
                "backend_status": f"error: {response.status_code}",
                "backend_url": BACKEND_URL
            }
    except Exception as e:
        logger.error(f"Error connecting to backend: {str(e)}")
        return {
            "status": "warning",
            "service": "Babywise API Proxy",
            "backend_status": f"error: {str(e)}",
            "backend_url": BACKEND_URL
        }

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_endpoint(request: Request, path: str):
    """
    Proxy all API requests to the backend.
    This avoids having to import the full application in the serverless function.
    """
    try:
        # Get the request body
        body = await request.body()
        
        # Get the request headers
        headers = dict(request.headers)
        # Remove headers that might cause issues
        headers.pop("host", None)
        
        # Get the request method
        method = request.method
        
        # Get the request query parameters
        params = dict(request.query_params)
        
        # Log the request
        logger.info(f"Proxying {method} request to {BACKEND_URL}/api/{path}")
        
        # Forward the request to the backend
        response = await http_client.request(
            method=method,
            url=f"{BACKEND_URL}/api/{path}",
            params=params,
            headers=headers,
            content=body
        )
        
        # Return the response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Close the HTTP client when the application shuts down."""
    await http_client.aclose() 