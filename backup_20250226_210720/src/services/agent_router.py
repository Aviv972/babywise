from typing import Dict, Any, Optional
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from src.langchain.config import BabywiseState, merge_messages
from src.constants import AgentTypes
from src.services.agent_factory import AgentFactory
import logging
import traceback

logger = logging.getLogger(__name__)

class AgentRouter:
    def __init__(self, agent_factory: AgentFactory, session_id: str = "global"):
        self.agent_factory = agent_factory
        self.session_id = session_id
        self.graph = self._create_agent_graph()
        
    def _create_agent_graph(self) -> StateGraph:
        """Create a graph for agent routing and execution"""
        workflow = StateGraph(state_schema=BabywiseState)
        
        # Add agent selection node
        async def select_agent(state: BabywiseState) -> Dict[str, Any]:
            messages = state["messages"]
            if not messages:
                return {"agent_type": AgentTypes.GENERAL.value}
            
            last_message = messages[-1].content
            agent_type = self.agent_factory.determine_agent_type(last_message)
            return {"agent_type": agent_type}
        
        workflow.add_node("agent_selector", RunnableLambda(select_agent))
        
        # Create agents
        agents = {
            AgentTypes.SLEEP.value: self.agent_factory.create_agent(AgentTypes.SLEEP, "global"),
            AgentTypes.FEEDING.value: self.agent_factory.create_agent(AgentTypes.FEEDING, "global"),
            AgentTypes.HEALTH.value: self.agent_factory.create_agent(AgentTypes.HEALTH, "global"),
            AgentTypes.DEVELOPMENT.value: self.agent_factory.create_agent(AgentTypes.DEVELOPMENT, "global"),
            AgentTypes.GENERAL.value: self.agent_factory.create_agent(AgentTypes.GENERAL, "global"),
            # Add other agents as needed
        }
        
        # Define agent invoke function
        async def agent_invoke(state: BabywiseState, agent) -> BabywiseState:
            return await agent.invoke(state)
            
        # Add agent nodes
        for agent_type, agent in agents.items():
            workflow.add_node(agent_type, RunnableLambda(lambda x, a=agent: agent_invoke(x, a)))
        
        # Define condition function
        def make_route_condition(target_type: str):
            def condition(x: Dict) -> bool:
                return x["agent_type"] == target_type
            condition.__name__ = f"route_to_{target_type}"
            return condition
        
        # Add routing edges
        for agent_type in agents:
            workflow.add_conditional_edges(
                "agent_selector",
                RunnableLambda(make_route_condition(agent_type)),
                {agent_type: agent_type}
            )
        
        # Set the entry point
        workflow.set_entry_point("agent_selector")
        
        return workflow.compile()
    
    def select_agent(self, query: str) -> AgentTypes:
        """Select the appropriate agent type based on the query."""
        # For now, just return general agent
        return AgentTypes.GENERAL

    async def route_and_execute(self, state: BabywiseState) -> BabywiseState:
        """Route the query to the appropriate agent and execute it."""
        try:
            # Get the agent type from the state or select a new one
            agent_type = state.get('agent_type')
            if not agent_type:
                agent_type = self.select_agent(state['messages'][-1].content)
                state['agent_type'] = agent_type

            # Create or get the agent
            agent = self.agent_factory.create_agent(agent_type, self.session_id)
            
            # Execute the agent
            result = await agent.invoke(state)
            
            # Merge messages from result with existing messages
            if result.get('messages'):
                state['messages'] = merge_messages(state.get('messages', []), result['messages'])
            
            return state
            
        except Exception as e:
            logger.error(f"Error in route_and_execute: {str(e)}")
            logger.error(traceback.format_exc())
            raise 