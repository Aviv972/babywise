from typing import Dict, List
from src.services.llm_service import LLMService
from src.agents.base_agent import BaseAgent
from src.agents.baby_gear_agent import BabyGearAgent
from src.agents.general_agent import GeneralAgent

class AgentFactory:
    def __init__(self):
        self.llm_service = LLMService()
        self.agents = {}
        
        # Define agent mappings
        self.agent_keywords = {
            'baby_gear': [
                "stroller", "car seat", "crib", "bassinet",
                "עגלה", "כיסא בטיחות", "מיטת תינוק", "עריסה"
            ]
        }

    async def get_agent_for_query(self, query: str) -> BaseAgent:
        """Get or create appropriate agent based on query"""
        agent_type = self._determine_agent_type(query)
        
        if agent_type not in self.agents:
            self.agents[agent_type] = self._create_agent(agent_type)
        
        return self.agents[agent_type]

    def _determine_agent_type(self, query: str) -> str:
        """Determine agent type from query"""
        query_lower = query.lower()
        
        for agent_type, keywords in self.agent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return agent_type
                
        return 'general'

    def _create_agent(self, agent_type: str) -> BaseAgent:
        """Create new agent instance"""
        agents = {
            'baby_gear': BabyGearAgent,
            'general': GeneralAgent
        }
        
        agent_class = agents.get(agent_type, GeneralAgent)
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