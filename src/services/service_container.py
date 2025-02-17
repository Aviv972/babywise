from src.services.llm_service import LLMService
from src.services.agent_factory import AgentFactory
from src.config import Config

class ServiceContainer:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not ServiceContainer._initialized:
            print("Initializing service container...")
            Config.validate()
            self.llm_service = LLMService(
                api_key=Config.OPENAI_API_KEY,
                model=Config.MODEL_NAME
            )
            self.agent_factory = AgentFactory(self.llm_service)
            ServiceContainer._initialized = True

# Create a singleton instance
container = ServiceContainer() 