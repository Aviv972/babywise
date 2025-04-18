"""
Babywise Chatbot - Workflow

This module implements the LangGraph workflow for the Babywise Chatbot,
connecting all workflow nodes and providing functions for workflow management.
"""

import logging
import traceback
from typing import Dict, Any, List, Set, TypedDict, Optional
from datetime import datetime
import asyncio
from backend.models.message_types import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.workflow.extract_context import extract_context
from backend.workflow.select_domain import select_domain
from backend.workflow.generate_response import generate_response
from backend.workflow.post_process import post_process
from backend.workflow.command_processor import CommandProcessor
from backend.services.redis_service import get_thread_state, save_thread_state
import json
import time
import copy

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

# Workflow class to provide invoke() method
class WorkflowInvoker:
    def __init__(self, runner_func):
        self.runner_func = runner_func
        
    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the workflow to process user input and generate a response.
        
        Args:
            state: The current conversation state
            
        Returns:
            The updated state
        """
        start_time = time.time()
        logger.info(f"Starting workflow execution for thread {state.get('metadata', {}).get('thread_id', 'unknown')}")
        
        if state is None:
            state = self.get_default_state()
            logger.warning("No state provided, using default state")

        # Ensure state has basic structure before processing
        if "context" not in state or not state["context"]:
            logger.info("Initializing empty context in workflow with default structure")
            state["context"] = {
                "thread_id": state.get("metadata", {}).get("thread_id", ""),
                "user_timezone": state.get("metadata", {}).get("timezone", "UTC"),
                "last_updated": datetime.utcnow().isoformat(),
                "baby_info": {},
                "routines": {
                    "sleep": [],
                    "feeding": []
                }
            }
        
        if "user_context" not in state:
            state["user_context"] = {}
        
        # Ensure metadata exists
        if "metadata" not in state:
            state["metadata"] = {}
        
        # Store original context to prevent accidental loss
        original_context = copy.deepcopy(state.get("context", {}))
        original_user_context = copy.deepcopy(state.get("user_context", {}))
        
        # Ensure messages list exists
        if "messages" not in state:
            state["messages"] = []
        
        try:
            # Process the message to determine the domain
            state = await select_domain(state)
            logger.info(f"Domain classification: {state.get('domain', 'unknown')}")
            
            # Generate a response based on the domain and other state information
            state = await generate_response(state)
            logger.info(f"Response generated for domain: {state.get('domain', 'unknown')}")
            
            # Post-process the response to handle tracking commands, etc.
            state = await post_process(state)
            logger.info(f"Post-processing completed")
            
            # Check if context was lost during processing and restore it
            if not state.get("context") and original_context:
                logger.warning("Context was lost during processing, restoring from backup")
                state["context"] = original_context
                
            if not state.get("user_context") and original_user_context:
                logger.warning("User context was lost during processing, restoring from backup")
                state["user_context"] = original_user_context
            
            # Calculate and log execution time
            execution_time = time.time() - start_time
            logger.info(f"Workflow execution completed in {execution_time:.2f} seconds")
            
            # Log final context summary
            context_size = len(json.dumps(state.get("context", {})))
            user_context_size = len(json.dumps(state.get("user_context", {})))
            logger.info(f"Final context size: {context_size} bytes, user context size: {user_context_size} bytes")
            
            return state
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}", exc_info=True)
            
            # If an error occurred, try to preserve context
            if not state.get("context") and original_context:
                state["context"] = original_context
            
            if not state.get("user_context") and original_user_context:
                state["user_context"] = original_user_context
                
            # Add error message to state
            state["error"] = str(e)
            
            # Add error response to messages
            if "messages" in state:
                state["messages"].append(AIMessage(content="I'm sorry, I encountered an error processing your request. Please try again."))
            
            return state

# Initialize global variables
_workflow = None
memory_saver = MemorySaver()
command_processor = CommandProcessor()

async def process_input(state: GraphState) -> Dict[str, Any]:
    """Process input and determine if it should go to chat or command workflow"""
    try:
        # Get the latest message
        message = state["messages"][-1]
        
        # Get thread_id from metadata
        thread_id = state.get("metadata", {}).get("thread_id", "default")
        language = state.get("language", state.get("metadata", {}).get("language", "en"))
        
        logger.info(f"Processing input for thread {thread_id}, language: {language}")
        logger.info(f"Message content: '{message.content}'")
        
        # Try to process as command
        result = await command_processor.process_command(message.content, thread_id)
        
        if result["success"]:
            # Command was processed successfully
            logger.info(f"Command processed successfully: {result['response_type']}")
            state["skip_chat"] = True
            state["command_result"] = result
            # Add AI response message
            state["messages"].append(AIMessage(content=result["message"]))
            logger.info(f"Added AI response: '{result['message']}'")
        else:
            # Not a command, proceed with chat
            logger.info("Not a command, proceeding with chat workflow")
            state["skip_chat"] = False
            
        return state
    except Exception as e:
        logger.error(f"Error in process_input: {str(e)}")
        logger.error(traceback.format_exc())
        state["skip_chat"] = False
        # Add error message to state
        state["messages"].append(AIMessage(content="I apologize, but I encountered an error processing your request. Could you please try again?"))
        return state

def should_proceed_to_chat(state: GraphState) -> bool:
    """Determine if we should proceed to chat workflow"""
    return not state.get("skip_chat", False)

async def create_workflow():
    """Create the LangGraph workflow"""
    # Initialize the graph with the state type
    workflow = StateGraph(GraphState)
    
    # Define async wrapper for nodes
    async def async_process_input(state):
        return await process_input(state)
        
    async def async_extract_context(state):
        try:
            return await extract_context(state)
        except Exception as e:
            logger.error(f"Error in extract_context: {str(e)}")
            logger.error(traceback.format_exc())
            # Return original state if there's an error
            return state
        
    async def async_select_domain(state):
        try:
            return await select_domain(state)
        except Exception as e:
            logger.error(f"Error in select_domain: {str(e)}")
            logger.error(traceback.format_exc())
            # Set a default domain if there's an error
            state["domain"] = "general"
            return state
        
    async def async_generate_response(state):
        try:
            return await generate_response(state)
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}")
            logger.error(traceback.format_exc())
            # Add a fallback response if there's an error
            state["messages"].append(AIMessage(content="I apologize, but I encountered an error generating a response. Could you please try again?"))
            return state
        
    async def async_post_process(state):
        try:
            return await post_process(state)
        except Exception as e:
            logger.error(f"Error in post_process: {str(e)}")
            logger.error(traceback.format_exc())
            # Return state as is if there's an error
            return state
    
    # Add nodes
    workflow.add_node("process_input", async_process_input)
    workflow.add_node("extract_context", async_extract_context)
    workflow.add_node("select_domain", async_select_domain)
    workflow.add_node("generate_response", async_generate_response)
    workflow.add_node("post_process", async_post_process)
    
    # Define conditional edges
    workflow.add_conditional_edges(
        "process_input",
        should_proceed_to_chat,
        {
            True: "extract_context",
            False: END
        }
    )
    
    # Add remaining edges
    workflow.add_edge("extract_context", "select_domain")
    workflow.add_edge("select_domain", "generate_response")
    workflow.add_edge("generate_response", "post_process")
    workflow.add_edge("post_process", END)
    
    # Set entry point
    workflow.set_entry_point("process_input")
    
    # Compile the workflow
    compiled = workflow.compile(checkpointer=memory_saver)
    
    # Create an async callable wrapper
    async def workflow_runner(state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Run each node in sequence manually to ensure async execution
            current_state = state.copy()
            current_node = "process_input"
            
            # Process input
            logger.info("Starting workflow execution at node: process_input")
            current_state = await async_process_input(current_state)
            
            # Check if we should proceed to chat
            if should_proceed_to_chat(current_state):
                # Extract context
                current_node = "extract_context"
                logger.info("Proceeding to node: extract_context")
                current_state = await async_extract_context(current_state)
                
                # Select domain
                current_node = "select_domain"
                logger.info("Proceeding to node: select_domain")
                current_state = await async_select_domain(current_state)
                
                # Generate response
                current_node = "generate_response"
                logger.info("Proceeding to node: generate_response")
                current_state = await async_generate_response(current_state)
                
                # Post process
                current_node = "post_process"
                logger.info("Proceeding to node: post_process")
                current_state = await async_post_process(current_state)
            else:
                logger.info("Skipping chat workflow, command was processed")
            
            logger.info("Workflow execution completed successfully")
            
            # Ensure required fields exist before saving
            if "context" not in current_state:
                current_state["context"] = {}
                
            if "user_context" not in current_state:
                current_state["user_context"] = {}
                
            if "metadata" not in current_state:
                current_state["metadata"] = {}
            
            # Save the final state to Redis
            thread_id = current_state.get("metadata", {}).get("thread_id")
            if thread_id:
                try:
                    # Convert set to list for JSON serialization
                    if "extracted_entities" in current_state and isinstance(current_state["extracted_entities"], set):
                        current_state["extracted_entities"] = list(current_state["extracted_entities"])
                    
                    # Log the context that will be saved
                    logger.info(f"Saving context to Redis: {json.dumps(current_state.get('context', {}), default=str)}")
                    logger.info(f"Saving user_context to Redis: {json.dumps(current_state.get('user_context', {}), default=str)}")
                    
                    await save_thread_state(thread_id, current_state)
                    logger.info(f"Saved workflow state to Redis for thread {thread_id}")
                except Exception as e:
                    logger.error(f"Error saving workflow state to Redis: {str(e)}")
            
            return current_state
        except Exception as e:
            logger.error(f"Error in workflow execution at node {current_node}: {str(e)}")
            logger.error(traceback.format_exc())
            # Add a default AI response in case of error
            if "messages" in state:
                state["messages"].append(AIMessage(content="I apologize, but I encountered an error processing your request. Could you please try again?"))
            return state
    
    # Wrap the runner function in a class with invoke method
    return WorkflowInvoker(workflow_runner)

async def get_workflow():
    """Get or create the workflow"""
    global _workflow
    if _workflow is None:
        logger.info("Creating new workflow instance")
        try:
            _workflow = await create_workflow()
            logger.info("Workflow created successfully")
        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    return _workflow

def get_default_state() -> Dict[str, Any]:
    """
    Get a default state for a new conversation.
    
    Returns:
        A default state dictionary
    """
    return {
        "messages": [],
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        },
        # Initialize empty context with default structure
        "context": {
            "baby_info": {},
            "routines": {
                "sleep": [],
                "feeding": []
            },
            "last_updated": datetime.utcnow().isoformat()
        },
        "user_context": {}
    } 