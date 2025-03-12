"""
Custom message types for the Babywise Chatbot.
These types are compatible with LangChain's message format while providing
additional functionality for Redis serialization.
"""

from typing import Dict, Any, Optional, Literal, Type, TypeVar, Union, List, Set
from pydantic import BaseModel, Field
from datetime import datetime
import json

T = TypeVar("T", bound="BaseMessage")

class BaseMessage(BaseModel):
    """Base class for all message types."""
    content: str = Field(description="The content of the message")
    type: str = Field(description="The type of the message")
    additional_kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional keyword arguments")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def __str__(self) -> str:
        """String representation of the message."""
        return self.content

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create message from dictionary format."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return self.model_dump()
        
    def __getitem__(self, key):
        """Allow dictionary-like access to properties."""
        if hasattr(self, key):
            return getattr(self, key)
        return None
    
    def get(self, key, default=None):
        """Mimic dict.get() method for compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        return default

class HumanMessage(BaseMessage):
    """Message from a human user."""
    type: Literal["human"] = "human"
    
    def __eq__(self, other):
        if isinstance(other, HumanMessage):
            return self.content == other.content
        return False

class AIMessage(BaseMessage):
    """Message from the AI assistant."""
    type: Literal["ai"] = "ai"
    function_call: Optional[Dict[str, Any]] = Field(default=None, description="Optional function call details")
    
    def __eq__(self, other):
        if isinstance(other, AIMessage):
            return self.content == other.content
        return False

class Context(BaseModel):
    """Context information for the conversation."""
    baby_age: Optional[Dict[str, Any]] = Field(default=None, description="Baby's age information")
    sleep_schedule: Optional[Dict[str, Any]] = Field(default=None, description="Sleep schedule information")
    feeding_schedule: Optional[Dict[str, Any]] = Field(default=None, description="Feeding schedule information")
    additional_info: Dict[str, Any] = Field(default_factory=dict, description="Additional context information")

class Metadata(BaseModel):
    """Metadata for the conversation state."""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    thread_id: str = Field(..., description="Unique identifier for the conversation thread")
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: Optional[str] = Field(default=None, description="User identifier if available")

class Routines(BaseModel):
    """Routine tracking information."""
    sleep: List[Dict[str, Any]] = Field(default_factory=list)
    feeding: List[Dict[str, Any]] = Field(default_factory=list)
    diaper: List[Dict[str, Any]] = Field(default_factory=list)

class StateModel(BaseModel):
    """Complete state model for Redis storage."""
    messages: List[Union[HumanMessage, AIMessage]] = Field(default_factory=list)
    context: Context = Field(default_factory=Context)
    domain: str = Field(default="general")
    extracted_entities: Set[str] = Field(default_factory=set)
    language: str = Field(default="en")
    metadata: Metadata
    user_context: Dict[str, Any] = Field(default_factory=dict)
    routines: Routines = Field(default_factory=Routines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format."""
        state_dict = self.model_dump()
        # Convert set to list for JSON serialization
        state_dict["extracted_entities"] = list(state_dict["extracted_entities"])
        # Convert message objects to dictionaries
        state_dict["messages"] = [msg.to_dict() if hasattr(msg, "to_dict") else msg for msg in state_dict["messages"]]
        return state_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateModel":
        """Create state from dictionary format."""
        # Convert list back to set for extracted_entities
        if "extracted_entities" in data and isinstance(data["extracted_entities"], list):
            data["extracted_entities"] = set(data["extracted_entities"])
        # Convert message dictionaries back to objects
        if "messages" in data and isinstance(data["messages"], list):
            messages = []
            for msg in data["messages"]:
                if isinstance(msg, dict):
                    messages.append(create_message_from_dict(msg))
                else:
                    messages.append(msg)
            data["messages"] = [msg for msg in messages if msg is not None]
        return cls(**data)

def create_message_from_dict(data: Dict[str, Any]) -> Optional[Union[HumanMessage, AIMessage]]:
    """Create a message instance from a dictionary."""
    if isinstance(data, (HumanMessage, AIMessage)):
        return data
        
    msg_type = data.get("type", "unknown").lower()
    if msg_type == "human":
        return HumanMessage.from_dict(data)
    elif msg_type == "ai":
        return AIMessage.from_dict(data)
    return None 