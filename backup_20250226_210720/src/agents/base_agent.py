from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from src.constants import ResponseTypes, AgentTypes, ContextFields
from src.docs.common_questions import COMMON_QUESTIONS, RESPONSE_GUIDELINES
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, Runnable
from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool
from src.langchain.config import BabywiseState, extract_context_from_messages, update_metadata
import logging
import re

logger = logging.getLogger(__name__)

class BaseAgent(Runnable[BabywiseState, BabywiseState], ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        """Initialize the base agent."""
        self.agent_type = agent_type
        self.name = name
        self.llm_service = llm_service
        self.required_context = []
        
        # Initialize memory components
        self.agent_memory = ConversationBufferWindowMemory(
            k=5,
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize expertise after memory components
        self.expertise = self.get_agent_expertise()
        
        self.shared_memory = ConversationBufferMemory(
            memory_key="shared_context",
            return_messages=True,
            output_key="output"
        )
        
        self.structured_memory = {}
        self.logger = logging.getLogger(f"agent.{self.agent_type.lower()}")

    @abstractmethod
    def get_agent_prompt(self) -> str:
        """Get the agent's system prompt."""
        pass

    @abstractmethod
    def get_agent_expertise(self) -> List[str]:
        """Get the agent's areas of expertise."""
        pass

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Each agent must specify its required context fields"""
        pass

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Common context extraction logic"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        try:
            # Process messages in reverse order (most recent first)
            for message in reversed(messages):
                content = message.content.lower()
                self.logger.debug(f"Processing message for context: {content}")
                
                # Extract age information
                month_patterns = [
                    r'have\s+a\s+(\d+)[\s-]month[\s-]old',  # Most specific pattern first
                    r'(\d+)[\s-]months[\s-]old',
                    r'(\d+)[\s-]month[\s-]old',
                    r'(\d+)[\s-]month',
                    r'(\d+)[\s-]months'
                ]
                
                for pattern in month_patterns:
                    self.logger.debug(f"Trying pattern: {pattern}")
                    match = re.search(pattern, content)
                    if match:
                        age_value = int(match.group(1))
                        self.logger.debug(f"Pattern '{pattern}' matched with value {age_value} in content: {content}")
                        gathered_info["baby_age"] = {
                            "value": age_value,
                            "unit": "months",
                            "original": f"{age_value} months"
                        }
                        self.logger.debug(f"Updated gathered_info with baby_age: {gathered_info['baby_age']}")
                        return gathered_info  # Return immediately after finding age in most recent message
                
                # Extract budget information
                if any(word in content for word in ['budget', 'cost', 'spend', '$', '₪']):
                    currency_matches = re.findall(r'[\$₪](\d+)', content)
                    if currency_matches:
                        value = int(currency_matches[0])
                        currency = 'USD' if '$' in content else 'ILS'
                        gathered_info["budget_range"] = {
                            "value": value,
                            "currency": currency,
                            "original": content
                        }
                
                # Extract timeframe
                if 'per month' in content or 'monthly' in content:
                    gathered_info["timeframe"] = {
                        'period': 'monthly',
                        'description': content
                    }
                elif 'per year' in content or 'yearly' in content:
                    gathered_info["timeframe"] = {
                        'period': 'yearly',
                        'description': content
                    }
                
                # Extract priority needs
                priority_keywords = {
                    'immediate': ['urgent', 'immediate', 'now', 'דחוף', 'מיידי'],
                    'essential': ['need', 'must have', 'essential', 'חייב', 'הכרחי'],
                    'optional': ['want', 'like', 'optional', 'רוצה', 'אופציונלי']
                }
                
                for priority, keywords in priority_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        if "priority_needs" not in gathered_info:
                            gathered_info["priority_needs"] = []
                        gathered_info["priority_needs"].append({
                            'priority': priority,
                            'description': content
                        })
            
            # Add agent-specific context extraction
            agent_context = self.extract_agent_specific_context(content)
            if agent_context:
                gathered_info.update(agent_context)
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {str(e)}")
            return {}

    def extract_agent_specific_context(self, content: str) -> Dict[str, Any]:
        """Override this method to add agent-specific context extraction"""
        return {}

    async def invoke(self, state: BabywiseState) -> BabywiseState:
        """Process input through agent"""
        try:
            # Extract context from messages
            context = self._extract_context_from_messages(state["messages"])
            
            # Update state metadata with extracted context
            state = self._update_metadata(state, {"extracted_context": context})
            
            # Check for required fields
            missing_fields = self._check_required_fields(context)
            if missing_fields:
                response = self._create_field_request_response(missing_fields)
                state["messages"].append({"role": "assistant", "content": response["text"]})
                return state
            
            # Generate response using LLM
            prompt = self.get_agent_prompt()
            response = await self.llm_service.agenerate_response(
                messages=state["messages"],
                system_prompt=prompt,
                context=context
            )
            
            # Update state
            state["messages"].append({"role": "assistant", "content": response})
            state["agent_type"] = self.agent_type.value
            
            return state
            
        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
            error_msg = "I apologize, but I encountered an error. Let me try to help you in a simpler way."
            state["messages"].append({"role": "assistant", "content": error_msg})
            return state

    def _extract_context_from_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract context from messages"""
        context = {}
        for message in messages:
            if isinstance(message, HumanMessage) or (isinstance(message, dict) and message.get("role") == "user"):
                content = message.content if isinstance(message, HumanMessage) else message["content"]
                # Add context extraction logic here
                pass
        return context

    def _update_metadata(self, state: BabywiseState, metadata: Dict[str, Any]) -> BabywiseState:
        """Update state metadata"""
        if "metadata" not in state:
            state["metadata"] = {}
        state["metadata"].update(metadata)
        return state

    def _check_required_fields(self, context: Dict[str, Any]) -> List[str]:
        """Check for required fields in context"""
        missing_fields = []
        for field in self.required_context:
            if field not in context:
                missing_fields.append(field)
        return missing_fields

    def _calculate_domain_relevance(self, query: str) -> float:
        """Calculate relevance based on agent expertise"""
        query_lower = query.lower()
        expertise = self.get_agent_expertise()
        
        # Primary terms (exact matches)
        if any(term in query_lower for term in expertise):
            return 1.0
        
        # Secondary terms (partial matches)
        if any(term in query_lower for term in [word for exp in expertise for word in exp.split()]):
            return 0.7
        
        return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Check for missing required fields"""
        gathered_info = context.get('gathered_info', {})
        required_fields = self.get_required_fields()
        return [field for field in required_fields if field not in gathered_info]

    def _get_system_prompt(self) -> str:
        """Override this method in specific agents to provide custom system prompts"""
        return """You are a helpful baby care assistant. Always be supportive and informative.
                 If you need any critical information, ask for it politely."""

    def _get_context_prompt(self) -> str:
        """Generate context-aware system prompt"""
        return """Use the following context in your response:
                 1. Shared Context: General information shared across all agents
                 2. Agent Context: Specialized information for current domain
                 3. Structured Data: Specific fields like baby age, preferences
                 
                 Always maintain consistency with previous context."""

    def _update_structured_memory(self, new_context: Dict[str, Any]):
        """Update structured memory with new context"""
        for key, value in new_context.items():
            if value is not None:  # Only update if we have a value
                self.structured_memory[key] = value
                self.logger.debug(f"Updated structured memory: {key}={value}")

    def get_structured_memory(self) -> Dict[str, Any]:
        """Get all structured memory data"""
        return self.structured_memory

    def share_context_with(self, other_agent: 'BaseAgent'):
        """Share relevant context with another agent"""
        # Share structured memory
        for key, value in self.structured_memory.items():
            other_agent.structured_memory[key] = value
        
        # Share relevant conversation context
        shared_context = self.shared_memory.load_memory_variables({})
        other_agent.shared_memory.chat_memory.messages.extend(
            shared_context.get("shared_context", [])
        )
        
        self.logger.info(f"Shared context with {other_agent.name}")

    def _validate_context(self, context: Dict[str, Any]) -> bool:
        """Validate that all required fields are present"""
        gathered_info = context[ContextFields.GATHERED_INFO]
        
        # Check for baby age first as it's critical
        if 'baby_age' in self.required_context:
            age_info = gathered_info.get('baby_age')
            if not age_info:
                return False
            
            # Validate age format
            if isinstance(age_info, dict):
                if not age_info.get('original'):
                    return False
            elif not str(age_info).strip():
                return False
        
        # Check other required fields
        for field in self.required_context:
            if field != 'baby_age' and field not in gathered_info:
                return False
        
        return True

    def _create_field_request_response(self, missing_fields: List[str]) -> Dict[str, Any]:
        """Create a response requesting missing fields"""
        from src.constants import RequiredFields
        
        if 'baby_age' in missing_fields:
            return {
                'type': ResponseTypes.QUERY,
                'text': RequiredFields.QUESTIONS['baby_age'],
                'needs_age': True
            }
        
        questions = [RequiredFields.QUESTIONS[field] for field in missing_fields if field in RequiredFields.QUESTIONS]
        return {
            'type': ResponseTypes.QUERY,
            'text': "\n".join(questions),
            'missing_fields': missing_fields
        }