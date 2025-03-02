"""
Babywise Chatbot - State Schema

This module defines the state schema for the Babywise Chatbot, including
the BabywiseState class that represents the conversation state.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from pydantic import BaseModel, Field

class Message(BaseModel):
    """Base class for chat messages."""
    type: str
    content: str
    timestamp: Any = Field(default_factory=lambda: datetime.now().isoformat())

class HumanMessage(Message):
    """Represents a message from the human user."""
    type: str = "human"

class AIMessage(Message):
    """Represents a message from the AI assistant."""
    type: str = "assistant"

class SystemMessage(Message):
    """Represents a system message or notification."""
    type: str = "system"

class BabywiseState(BaseModel):
    """
    Represents the state of a Babywise Chatbot conversation.
    
    This class stores the conversation history, extracted context,
    current domain, and additional metadata.
    """
    # List of chat messages
    messages: List[Message] = Field(default_factory=list)
    
    # Extracted context from the conversation
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Current topic domain (e.g., sleep, feeding, baby gear)
    domain: str = "general"
    
    # Additional state information
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Current conversation language
    language: str = "en"
    
    # Set of entities that have been extracted from the conversation
    extracted_entities: Set[str] = Field(default_factory=set)
    
    # User-specific context (e.g., gender context for Hebrew)
    user_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Tracked routines (sleep, feeding, diaper changes)
    routines: Dict[str, List[Dict[str, Any]]] = Field(default_factory=lambda: {
        "sleep": [], 
        "feeding": [], 
        "diaper": []
    })
    
    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            message: The message to add.
        """
        self.messages.append(message)
    
    def add_human_message(self, content: str) -> None:
        """
        Add a human message to the conversation history.
        
        Args:
            content: The content of the message.
        """
        self.messages.append(Message(type="human", content=content))
    
    def add_assistant_message(self, content: str) -> None:
        """
        Add an assistant message to the conversation history.
        
        Args:
            content: The content of the message.
        """
        self.messages.append(Message(type="assistant", content=content))
    
    def add_system_message(self, content: str) -> None:
        """
        Add a system message to the conversation history.
        
        Args:
            content: The content of the message.
        """
        self.messages.append(Message(type="system", content=content))
    
    def get_last_message(self) -> Optional[Message]:
        """
        Get the last message in the conversation history.
        
        Returns:
            The last message, or None if there are no messages.
        """
        if not self.messages:
            return None
        return self.messages[-1]
    
    def get_last_human_message(self) -> Optional[Message]:
        """
        Get the last human message in the conversation history.
        
        Returns:
            The last human message, or None if there are no human messages.
        """
        for message in reversed(self.messages):
            if message.type == "human":
                return message
        return None
    
    def get_recent_messages(self, n: int = 5) -> List[Message]:
        """
        Get the n most recent messages in the conversation history.
        
        Args:
            n: The number of recent messages to retrieve.
            
        Returns:
            A list of the n most recent messages.
        """
        return self.messages[-n:] if len(self.messages) >= n else self.messages[:]
    
    def update_context(self, key: str, value: Any, confidence: float = 0.8) -> None:
        """
        Update a specific context value.
        
        Args:
            key: The context key to update.
            value: The new value for the context key.
            confidence: The confidence score for this context value.
        """
        self.context[key] = {
            "value": value,
            "confidence": confidence
        }
        self.extracted_entities.add(key)
    
    def get_context_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context.
        
        Args:
            key: The context key to retrieve.
            default: The default value to return if the key is not found.
            
        Returns:
            The value for the context key, or the default value if not found.
        """
        if key in self.context:
            return self.context[key].get("value", default)
        return default
    
    def get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.
        
        Returns:
            The current timestamp as a string.
        """
        return datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the state to a dictionary representation.
        
        Returns:
            A dictionary representation of the state.
        """
        return {
            "messages": [
                {
                    "type": message.type,
                    "content": message.content,
                    "timestamp": message.timestamp
                } 
                for message in self.messages
            ],
            "context": self.context,
            "domain": self.domain,
            "metadata": self.metadata,
            "language": self.language,
            "extracted_entities": list(self.extracted_entities),
            "user_context": self.user_context,
            "routines": self.routines
        }
    
    def add_routine_event(self, routine_type: str, event_data: Dict[str, Any]) -> None:
        """
        Add a routine event to the state.
        
        Args:
            routine_type: The type of routine (sleep, feeding, diaper).
            event_data: The data for the routine event.
        """
        if routine_type not in self.routines:
            self.routines[routine_type] = []
        
        # Add timestamp if not provided
        if "timestamp" not in event_data:
            event_data["timestamp"] = self.get_current_timestamp()
        
        self.routines[routine_type].append(event_data)

def get_default_state() -> BabywiseState:
    """
    Create a new BabywiseState with default values.
    
    Returns:
        A new BabywiseState instance.
    """
    return BabywiseState(
        messages=[],
        context={},
        domain="general",
        metadata={"created_at": datetime.now().isoformat()},
        language="en",
        extracted_entities=set(),
        user_context={},
        routines={"sleep": [], "feeding": [], "diaper": []}
    ) 