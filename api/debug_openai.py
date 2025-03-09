"""
Babywise - OpenAI Debug Endpoint

This module provides a debug endpoint for testing OpenAI API integration.
"""

import os
import logging
import traceback
from fastapi import APIRouter, Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/openai")
async def debug_openai():
    """Debug endpoint to check OpenAI API integration."""
    try:
        # Check if OpenAI is installed and configured
        import openai
        
        # Log the version
        logger.info(f"OpenAI Python library version: {openai.__version__}")
        
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_key_status = "Available" if api_key else "Not available"
        
        # Try a simple completion to test the API
        client = openai.OpenAI(api_key=api_key)
        if api_key:
            try:
                # Make a simple test call
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'Hello, Babywise!' as a test."}
                    ],
                    max_tokens=20
                )
                response_text = completion.choices[0].message.content
                api_test = "Success"
            except Exception as e:
                response_text = f"Error: {str(e)}"
                api_test = "Failed"
        else:
            response_text = "No API key available"
            api_test = "Skipped"
        
        return {
            "status": "ok",
            "openai_version": openai.__version__,
            "api_key_status": api_key_status,
            "api_test": api_test,
            "response": response_text
        }
    except Exception as e:
        logger.error(f"Error in debug_openai: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        } 