from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

class ChatRequest(BaseModel):
    """Request for a chat message"""
    message: str
    thread_id: Optional[str] = None
    agent_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    """Message in a chat conversation"""
    message: str
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_langchain(self) -> BaseMessage:
        """Convert to LangChain message format"""
        if self.metadata and self.metadata.get("role") == "system":
            return SystemMessage(content=self.message)
        elif self.metadata and self.metadata.get("role") == "assistant":
            return AIMessage(content=self.message)
        return HumanMessage(content=self.message)

class ChatResponse(BaseModel):
    """Response from the chat system"""
    type: str
    text: str
    metadata: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    messages: Optional[List[BaseMessage]] = None  # LangChain messages

class ChatHistory(BaseModel):
    """Chat history response"""
    messages: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    langchain_messages: Optional[List[BaseMessage]] = None  # LangChain format

class ChatSession(BaseModel):
    """Chat session information"""
    session_id: str
    created_at: datetime
    last_active: datetime
    current_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    state: Optional[Dict[str, Any]] = None  # LangChain state
    
    def update_state(self, new_state: Dict[str, Any]):
        """Update session state with new LangChain state"""
        if not self.state:
            self.state = {}
        self.state.update(new_state)
        self.last_active = datetime.utcnow()

class ChatState(BaseModel):
    """LangChain state for chat sessions"""
    messages: List[BaseMessage]
    language: str = "en"
    thread_id: Optional[str] = None
    agent_type: Optional[str] = None
    gathered_info: Dict[str, Any] = {}
    transitions: List[Dict[str, Any]] = [] 