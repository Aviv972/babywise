from typing import Dict, Any, List
from src.langchain import BabywiseState
from src.models.chat import ChatState, ChatMessage
import logging
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from datetime import datetime

logger = logging.getLogger(__name__)

# Store conversation instances with LangChain memory
conversations: Dict[str, Dict[str, Any]] = {}

def create_memory_components(session_id: str, db_url: str) -> Dict[str, Any]:
    """
    Create memory components for a LangChain conversation.
    
    Args:
        session_id: Unique identifier for the conversation
        db_url: Database URL for storing conversation history
        
    Returns:
        Dictionary containing memory components
    """
    logger.info(f"Creating memory components for session {session_id}")
    
    # Create a SQL-backed chat message history
    message_history = SQLChatMessageHistory(
        session_id=session_id,
        connection_string=db_url
    )
    
    # Create a conversation memory using the message history
    memory = ConversationBufferMemory(
        chat_memory=message_history,
        return_messages=True,
        memory_key="chat_history"
    )
    
    return {
        "memory": memory,
        "message_history": message_history,
        "shared_memory": memory  # Add shared_memory for compatibility
    }

def convert_from_langchain_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """
    Convert LangChain message objects to serializable dictionaries.
    
    Args:
        messages: List of LangChain message objects
        
    Returns:
        List of serializable message dictionaries
    """
    result = []
    for msg in messages:
        message_dict = {
            "content": msg.content,
            "type": "user" if isinstance(msg, HumanMessage) else "bot",
            "timestamp": datetime.now().isoformat()
        }
        result.append(message_dict)
    return result

def extract_context_from_messages(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    Extract context information from message history.
    
    Args:
        messages: List of LangChain message objects
        
    Returns:
        Dictionary of extracted context information
    """
    # Simple implementation - in a real system, this would use NLP to extract entities
    context = {
        "baby_age": None,
        "preferences": {},
        "last_topics": []
    }
    
    # Extract topics from AI messages
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content:
            if "month" in msg.content.lower() and "old" in msg.content.lower():
                # Very simple extraction - would be more sophisticated in production
                context["last_topics"].append("age")
            if "sleep" in msg.content.lower():
                context["last_topics"].append("sleep")
            if "feed" in msg.content.lower():
                context["last_topics"].append("feeding")
    
    # Remove duplicates and keep last 3
    if context["last_topics"]:
        context["last_topics"] = list(dict.fromkeys(context["last_topics"]))[-3:]
    
    return context

async def get_or_create_memory(session_id: str) -> Dict[str, Any]:
    """Get or create LangChain memory components for a thread"""
    if session_id not in conversations:
        logger.info(f"Creating new memory components for thread {session_id}")
        conversations[session_id] = {
            "state": ChatState(
                messages=[],
                thread_id=session_id
            ).dict()
        }
    return conversations[session_id] 