"""
Babywise Chatbot - Data Models

This module defines the Pydantic models used for API requests and responses.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Model for chat request data"""
    message: str = Field(..., description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    language: str = Field("en", description="Language code (e.g., 'en', 'he', 'ar')")

class ChatResponse(BaseModel):
    """Model for chat response data"""
    text: str = Field(..., description="Assistant response")
    thread_id: str = Field(..., description="Thread ID for conversation continuity")
    domain: str = Field(..., description="Detected domain of the conversation")
    context: Dict[str, Any] = Field({}, description="Extracted context from the conversation")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata") 