from src.services.llm_service import LLMService
from src.services.agent_factory import AgentFactory
from src.services.semantic_matcher import SemanticMatcher
from src.config import get_settings, Config
from src.langchain.config import create_memory_components
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
import logging
from typing import Dict, Any
from src.services.memory_service import MemoryService

logger = logging.getLogger(__name__)
settings = get_settings()

class ServiceContainer:
    """Container for all service instances."""
    
    def __init__(self):
        """Initialize all services."""
        try:
            # Initialize configuration
            self.config = Config()
            
            # Initialize database
            self.db_url = self.config.get("database", "url")
            
            # Initialize LLM service with API key
            self.llm_service = LLMService(
                api_key=self.config.OPENAI_API_KEY,
                model=self.config.MODEL_NAME
            )
            
            # Initialize agent factory
            self.agent_factory = AgentFactory(llm_service=self.llm_service)
            
            # Initialize memory service
            self.memory_service = MemoryService(self.db_url)
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize services: {str(e)}")
            
    def get_agent_factory(self) -> AgentFactory:
        """Get the agent factory instance."""
        return self.agent_factory
        
    def get_memory_service(self) -> MemoryService:
        """Get the memory service instance."""
        return self.memory_service
        
    def get_llm_service(self) -> LLMService:
        """Get the LLM service instance."""
        return self.llm_service

# Create a singleton instance
container = ServiceContainer() 