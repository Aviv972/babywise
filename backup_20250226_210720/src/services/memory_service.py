import logging
from typing import Dict, Any
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory

logger = logging.getLogger(__name__)

class MemoryService:
    """Service for managing conversation memory."""
    
    def __init__(self, db_url: str = None):
        """Initialize the memory service."""
        self.db_url = db_url
        self.shared_memory = ConversationBufferMemory()
        self.logger = logging.getLogger(__name__)
        
    async def get_or_create_memory(self, session_id: str) -> Dict[str, Any]:
        """Get or create memory components for a session."""
        try:
            # Create SQL message history
            message_history = SQLChatMessageHistory(
                session_id=session_id,
                connection_string=self.db_url
            )
            
            # Create memory components
            memory = {
                "chat_memory": ConversationBufferMemory(
                    chat_memory=message_history,
                    return_messages=True
                ),
                "state": {
                    "gathered_info": {}
                }
            }
            
            self.logger.info(f"Memory components created for session {session_id}")
            return memory
            
        except Exception as e:
            self.logger.error(f"Error creating memory components: {str(e)}")
            raise 