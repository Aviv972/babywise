"""
Babywise Chatbot - Workflow

This module implements the LangGraph workflow for the Babywise Chatbot,
connecting all workflow nodes and providing functions for workflow management.
"""

import logging
from typing import Dict, Any, List, Set, TypedDict
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.graph import END
from langgraph.checkpoint.memory import MemorySaver
from backend.workflow.extract_context import extract_context
from backend.workflow.select_domain import select_domain
from backend.workflow.generate_response import generate_response
from backend.workflow.post_process import post_process

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the state type for the graph
class GraphState(TypedDict):
    messages: List[Any]
    context: Dict[str, Any]
    domain: str
    extracted_entities: Set[str]
    language: str
    metadata: Dict[str, Any]
    user_context: Dict[str, Any]
    routines: Dict[str, List[Dict[str, Any]]]

# Create the workflow
def create_workflow():
   """Create the LangGraph workflow"""
   # Initialize the graph with the state type
   workflow = StateGraph(GraphState)
   
   # Add nodes
   workflow.add_node("extract_context", extract_context)
   workflow.add_node("select_domain", select_domain)
   workflow.add_node("generate_response", generate_response)
   workflow.add_node("post_process", post_process)
  
   # Add edges
   workflow.add_edge("extract_context", "select_domain")
   workflow.add_edge("select_domain", "generate_response")
   workflow.add_edge("generate_response", "post_process")
   
   # Add a conditional edge from post_process back to itself to avoid the dead-end error
   workflow.add_edge("post_process", END)
  
   # Set entry point
   workflow.set_entry_point("extract_context")
   
   # Compile the workflow
   memory = MemorySaver()
   return workflow.compile(checkpointer=memory)


# Global memory store for all workflows
memory_saver = MemorySaver()
# Global workflow instance
_workflow = None
# Thread state cache
thread_states = {}


def get_workflow():
   """Get or create the workflow"""
   global _workflow
   if _workflow is None:
       # Initialize the graph with the state type
       workflow = StateGraph(GraphState)
      
       # Add nodes
       workflow.add_node("extract_context", extract_context)
       workflow.add_node("select_domain", select_domain)
       workflow.add_node("generate_response", generate_response)
       workflow.add_node("post_process", post_process)
      
       # Add edges
       workflow.add_edge("extract_context", "select_domain")
       workflow.add_edge("select_domain", "generate_response")
       workflow.add_edge("generate_response", "post_process")
       
       # Add a conditional edge from post_process to END
       workflow.add_edge("post_process", END)
      
       # Set entry point
       workflow.set_entry_point("extract_context")
       
       # Compile the workflow with the global memory saver
       _workflow = workflow.compile(checkpointer=memory_saver)
  
   return _workflow


# Helper functions
def get_default_state() -> Dict[str, Any]:
   """Get the default state"""
   return {
       "messages": [],
       "context": {},
       "domain": "general",
       "extracted_entities": set(),
       "language": "en",
       "metadata": {
           "created_at": datetime.utcnow().isoformat(),
           "language": "en"
       },
       "user_context": {},
       "routines": {"sleep": [], "feeding": [], "diaper": []}
   } 