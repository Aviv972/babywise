from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from src.langchain.config import (
    BabywiseState,
    create_base_prompt,
    create_memory_store,
    get_default_state,
    convert_to_langchain_messages,
    convert_from_langchain_messages
)
from src.services.agent_router import AgentRouter
from src.models.chat import ChatResponse
from langchain_core.messages import HumanMessage, AIMessage
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ChatSession:
    def __init__(self, session_id: str, agent_router: AgentRouter):
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()
        
        # Initialize components
        self.memory = create_memory_store(session_id)
        self.agent_router = agent_router
        self.base_prompt = create_base_prompt()
        
        # Initialize state
        self.state = get_default_state()
        self.state["metadata"]["session_id"] = session_id
        
        logger.info(f"Initialized chat session: {session_id}")
    
    async def process_message(self, message: str) -> ChatResponse:
        """Process a message and return response"""
        try:
            # Update last active timestamp
            self.last_active = datetime.utcnow()
            
            # Add user message to memory and state
            self.memory.chat_memory.add_user_message(message)
            self.state["messages"] = self.memory.chat_memory.messages
            
            logger.debug(f"Added message to memory: {message}")
            logger.debug(f"Current messages in memory: {[m.content for m in self.memory.chat_memory.messages]}")
            
            # Route and execute through appropriate agent
            result = await self.agent_router.route_and_execute(self.state)
            logger.debug(f"Agent result metadata: {result.get('metadata', {})}")
            
            # Update state with result while preserving existing context
            existing_context = self.state["metadata"].get("extracted_context", {})
            new_context = result.get("metadata", {}).get("extracted_context", {})
            
            # Merge contexts, preferring new values over old ones
            merged_context = {**existing_context, **new_context}
            
            self.state = result
            self.state["metadata"]["extracted_context"] = merged_context
            
            # Add assistant message to memory
            last_message = self.state["messages"][-1]
            if isinstance(last_message, AIMessage):
                self.memory.chat_memory.add_ai_message(last_message.content)
            
            # Prepare response
            response = ChatResponse(
                text=last_message.content,
                type="text",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_type": self.state["agent_type"],
                    "session_id": self.session_id,
                    "language": "en",
                    "gathered_info": self.state["metadata"].get("gathered_info", {}),
                    "extracted_context": merged_context
                }
            )
            logger.debug(f"Prepared response with metadata: {response.metadata}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_msg = "I apologize, but I encountered an error. Please try again."
            return ChatResponse(
                text=error_msg,
                type="error",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "session_id": self.session_id
                }
            )
    
    async def get_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation history"""
        try:
            messages = self.memory.chat_memory.messages
            if limit:
                messages = messages[-limit:]
            return convert_from_langchain_messages(messages)
        except Exception as e:
            logger.error(f"Error retrieving history: {str(e)}")
            return []
    
    def clear(self) -> None:
        """Clear the session"""
        try:
            self.memory.clear()
            self.state = get_default_state()
            self.state["metadata"]["session_id"] = self.session_id
            logger.info(f"Cleared session {self.session_id}")
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            raise
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if session has expired"""
        age = datetime.utcnow() - self.last_active
        return age.total_seconds() > (max_age_hours * 3600) 