from typing import List, Dict, Any, Tuple
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.agents.base_agent import BaseAgent
from src.agents.pregnancy_agent import PregnancyAgent
from src.agents.baby_gear_agent import BabyGearAgent
from src.agents.sleep_routine_agent import SleepRoutineAgent
from src.agents.feeding_agent import FeedingAgent
from src.utils.keyword_extractor import extract_keywords

class AgentManager:
    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.current_agent = None
        self.current_query_type = None
        
    def register_agent(self, agent: BaseAgent):
        self.agents.append(agent)
        
    async def process_query(self, query: str) -> str:
        try:
            # Extract keywords from query
            keywords = extract_keywords(query)
            context = {"keywords": keywords}

            print("\n=== Processing Query ===")
            print(f"Query: {query}")
            print(f"Keywords: {keywords}")

            # Find capable agents and their confidence scores
            capable_agents = []
            for agent in self.agents:
                can_handle = await agent.can_handle_query(query, keywords)
                if can_handle:
                    confidence = agent._calculate_confidence(query, keywords)
                    capable_agents.append((agent, confidence))
                    print(f"Agent {agent.name} confidence: {confidence}")

            if not capable_agents:
                return "I couldn't find an expert to handle your question."

            # Sort by confidence
            capable_agents.sort(key=lambda x: x[1], reverse=True)
            selected_agent = capable_agents[0][0]
            
            # Only use the agent if confidence is high enough
            if capable_agents[0][1] < 0.2:  # Minimum confidence threshold
                return "I'm not confident I can provide a good answer to this question. Could you please rephrase or clarify?"

            print(f"Selected agent: {selected_agent.name} with confidence: {capable_agents[0][1]}")
            
            # Use the selected agent
            self.current_agent = selected_agent
            return await selected_agent.process_query(query, context)

        except Exception as e:
            print(f"Error in agent manager: {e}")
            raise 