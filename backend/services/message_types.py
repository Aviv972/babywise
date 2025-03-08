"""
Babywise Chatbot - Message Types

This module provides simple message type classes for the Babywise Chatbot.
"""

from typing import Dict, Any

class BaseMessage:
    """Base class for all message types."""
    def __init__(self, content: str, additional_kwargs: Dict[str, Any] = None):
        self.content = content
        self.additional_kwargs = additional_kwargs or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "type": self.__class__.__name__.lower(),
            "content": self.content,
            "additional_kwargs": self.additional_kwargs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessage':
        """Create message instance from dictionary."""
        return cls(
            content=data["content"],
            additional_kwargs=data.get("additional_kwargs", {})
        )

class HumanMessage(BaseMessage):
    """Message from a human user."""
    pass

class AIMessage(BaseMessage):
    """Message from the AI assistant."""
    pass 