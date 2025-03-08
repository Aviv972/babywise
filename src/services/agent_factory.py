from typing import Dict, Optional, List
from src.constants import AgentTypes
from src.agents.mental_health_agent import MentalHealthAgent
from src.agents.general_agent import GeneralAgent
from src.agents.baby_gear_agent import BabyGearAgent
from src.services.llm_service import LLMService
from src.agents.base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class AgentFactory:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all available agents"""
        self.agents = {
            'general': GeneralAgent(self.llm_service),
            'baby_gear': BabyGearAgent(self.llm_service)
        }
        
    def get_agent(self, message: str) -> BaseAgent:
        """Get the appropriate agent based on the message content"""
        # Simple keyword-based routing for now
        if any(keyword in message.lower() for keyword in ['stroller', 'crib', 'car seat', 'bottle', 'diaper']):
            logger.info("Selected baby gear agent")
            return self.agents['baby_gear']
        
        logger.info("Selected general agent")
        return self.agents['general']

    async def get_agent_for_query(self, query: str, agent_type: Optional[str] = None) -> object:
        """Get or create appropriate agent based on query and/or specified type"""
        # First determine agent type from query if not specified
        agent_type = agent_type or self._determine_agent_type(query)
        print(f"Selected agent type: {agent_type}")
        
        # Create agent if not exists
        if agent_type not in self.agents:
            self.agents[agent_type] = self._create_agent(agent_type)
            print(f"Created new agent of type: {agent_type}")
        
        return self.agents[agent_type]

    def _determine_agent_type(self, query: str) -> str:
        """Determine the most appropriate agent type based on query content"""
        query = query.lower()
        
        # Emergency/Safety queries (highest priority)
        if any(term in query for term in ['emergency', 'choking', 'breathing', 'accident', 'hurt', 'injury', 'danger']):
            print(f"Selected Agent: {AgentTypes.EMERGENCY} - Query contains emergency terms")
            return AgentTypes.EMERGENCY
        
        # Mental Health and Postpartum queries
        mental_health_terms = [
            'depression', 'anxiety', 'stress', 'mood', 'emotional', 'feeling',
            'mental', 'therapy', 'postpartum', 'baby blues', 'sad', 'crying',
            'overwhelmed', 'lonely', 'isolated'
        ]
        if any(term in query for term in mental_health_terms):
            print(f"Selected Agent: {AgentTypes.MENTAL_HEALTH} - Query contains mental health terms")
            return AgentTypes.MENTAL_HEALTH
        
        # Baby gear related queries
        if any(term in query for term in ['stroller', 'crib', 'car seat', 'gear', 'buy', 'product']):
            print(f"Selected Agent: {AgentTypes.BABY_GEAR} - Query contains baby gear terms")
            return AgentTypes.BABY_GEAR
            
        # Default to general agent
        print(f"Selected Agent: {AgentTypes.GENERAL} - No specific terms matched")
        return AgentTypes.GENERAL

    def _create_agent(self, agent_type: str) -> object:
        """Create a new agent instance of the specified type"""
        agent_map = {
            AgentTypes.MENTAL_HEALTH: MentalHealthAgent,
            AgentTypes.BABY_GEAR: BabyGearAgent,
            AgentTypes.GENERAL: GeneralAgent
        }
        
        agent_class = agent_map.get(agent_type)
        if agent_class is None:
            print(f"Warning: No agent class found for type {agent_type}, defaulting to GeneralAgent")
            agent_class = GeneralAgent
            
        return agent_class(self.llm_service)

    def _calculate_confidence(self, query: str, agent_type: str) -> float:
        """Calculate confidence for an agent handling this query"""
        query_lower = query.lower()
        keywords = self.agent_keywords.get(agent_type, [])
        matches = sum(1 for keyword in keywords if keyword in query_lower)
        return min(matches / max(len(keywords), 1), 1.0)

    def calculate_confidence(self, query: str, expertise: List[str]) -> float:
        query_lower = query.lower()
        matches = sum(1 for keyword in expertise if keyword.lower() in query_lower)
        return min(matches / len(expertise), 1.0)

    def determine_query_type(self, query: str) -> str:
        query_lower = query.lower()
        if 'twins' in query_lower and 'stroller' in query_lower:
            return 'twin_stroller'
        elif 'stroller' in query_lower:
            return 'stroller'
        return 'general' 