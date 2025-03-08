from src.services.llm_service import LLMService
from src.services.agent_factory import AgentFactory
from src.config import Config
import logging

logger = logging.getLogger(__name__)

class ServiceContainer:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not ServiceContainer._initialized:
            try:
                logger.info("Initializing service container...")
                
                # Validate configuration
                Config.validate()
                logger.info("Configuration validated successfully")
                
                # Initialize LLM service
                logger.info(f"Initializing LLM service with model: {Config.MODEL_NAME}")
                self.llm_service = LLMService(
                    api_key=Config.OPENAI_API_KEY,
                    model=Config.MODEL_NAME
                )
                logger.info("LLM service initialized successfully")
                
                # Initialize agent factory
                logger.info("Initializing agent factory...")
                self.agent_factory = AgentFactory(self.llm_service)
                logger.info("Agent factory initialized successfully")
                
                ServiceContainer._initialized = True
                logger.info("Service container initialization complete")
            except Exception as e:
                logger.error(f"Error initializing service container: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to initialize services: {str(e)}")

# Create a singleton instance
try:
    container = ServiceContainer()
    logger.info("Service container singleton created successfully")
except Exception as e:
    logger.error(f"Error creating service container singleton: {str(e)}", exc_info=True)
    raise 