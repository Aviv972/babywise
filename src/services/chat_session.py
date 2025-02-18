from typing import Dict, List, Optional, Any
from src.database.db_manager import DatabaseManager
from src.services.agent_factory import AgentFactory
from src.constants import (
    ContextFields, 
    MessageRoles, 
    ResponseTypes, 
    QuestionFields,
    AgentTypes,
    FieldMappings,
    RequiredFields
)
from src.models.query_context import QueryContext
from datetime import datetime
import json
import re
import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from src.exceptions import ModelProcessingError, DatabaseError, ValidationError

logger = logging.getLogger(__name__)

class ChatSession:
    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory
        self.db = DatabaseManager()
        self.session_id = str(uuid.uuid4())
        self._initialize_session()
        self.context = QueryContext()
        self.conversation_history = []
        self.current_agent = None
        # Initialize a new conversation in the database
        self.conversation_id = self.db.create_conversation()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Created new chat session with ID: {self.session_id}")

    def _initialize_session(self):
        """Initialize a new chat session in the database"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_sessions (session_id) VALUES (?)",
            (self.session_id,)
        )
        conn.commit()

    def _process_answer(self, query: str, response: Dict) -> None:
        """Process and store the answer in the context"""
        if not response:
            return

        # Extract field and value from the response
        if response.get('type') == 'follow_up_question':
            # Store the last asked field for context
            self.context._last_field = response.get('field')
            return

        # If this is an answer to a previous question, store it
        if self.context._last_field:
            self.context.add_clarification(
                self.context._last_field,
                query
            )
            self.context._last_field = None  # Reset after storing

        # Update context with any additional information from the response
        if response.get('addressed_fields'):
            for field in response['addressed_fields']:
                if field not in self.context.gathered_info:
                    self.context.add_clarification(field, query)

    def _is_field_relevant_to_query(self, field: str, original_topic: str) -> bool:
        """Validate if a field is relevant to the original query topic"""
        # Map fields to relevant topics
        field_topic_map = {
            QuestionFields.BUDGET: ['stroller', 'gear', 'buy', 'cost', 'purchase'],
            QuestionFields.STROLLER_TYPE: ['stroller', 'gear', 'transport'],
            QuestionFields.STORAGE_NEEDS: ['stroller', 'gear', 'storage'],
            QuestionFields.TERRAIN_USE: ['stroller', 'gear', 'transport'],
            QuestionFields.BABY_AGE: ['*'],  # Age is relevant to all topics
            QuestionFields.CURRENT_SLEEP_HOURS: ['sleep', 'routine', 'schedule'],
            QuestionFields.SLEEP_PATTERN: ['sleep', 'routine', 'schedule'],
            QuestionFields.HEALTH_ISSUES: ['health', 'medical', 'sleep', 'feeding']
        }
        
        # If field isn't in our map, assume it's relevant
        if field not in field_topic_map:
            return True
            
        # Age is always relevant
        if field == QuestionFields.BABY_AGE:
            return True
            
        # Check if any relevant topics are in the original query
        relevant_topics = field_topic_map.get(field, [])
        return any(topic in original_topic for topic in relevant_topics)

    def _extract_age_from_query(self, query: str) -> Optional[str]:
        """Extract age information from query"""
        words = query.split()
        for i, word in enumerate(words):
            if word.isdigit():
                if i + 1 < len(words):
                    next_word = words[i + 1].lower()
                    if 'month' in next_word:
                        return f"{word} months"
                    if 'year' in next_word:
                        return f"{word} years"
            elif word.lower() == 'baby' and i + 3 < len(words):
                if words[i + 1] == 'is' and words[i + 2].isdigit():
                    next_word = words[i + 3].lower()
                    if 'month' in next_word:
                        return f"{words[i + 2]} months"
                    if 'year' in next_word:
                        return f"{words[i + 2]} years"
        return None

    def _extract_sleep_duration(self, query: str) -> Optional[str]:
        """Extract sleep duration from query"""
        words = query.split()
        for i, word in enumerate(words):
            if word.isdigit() or word.replace('/', '').isdigit():
                if i + 1 < len(words) and ('hour' in words[i + 1] or 'hr' in words[i + 1]):
                    return f"{word} hours"
        return None

    def _extract_budget(self, query: str) -> Optional[str]:
        """Extract budget information from query"""
        # Look for currency amounts
        import re
        currency_pattern = r'\$?\d+(?:,\d{3})*(?:\.\d{2})?'
        budget_keywords = ['under', 'below', 'within', 'budget', 'cost', 'price']
        
        query_lower = query.lower()
        
        # First look for explicit budget mentions
        for keyword in budget_keywords:
            if keyword in query_lower:
                matches = re.findall(currency_pattern, query)
                if matches:
                    amount = matches[0].replace('$', '')
                    return f"${amount}"
        
        # Then look for any currency amounts
        matches = re.findall(currency_pattern, query)
        if matches:
            amount = matches[0].replace('$', '')
            return f"${amount}"
        
        return None

    def _extract_preferences(self, query: str) -> Optional[str]:
        """Extract preferences and requirements from the query"""
        preference_indicators = [
            'want', 'need', 'looking for', 'must have',
            'important', 'prefer', 'should be', 'feature'
        ]
        
        for indicator in preference_indicators:
            if indicator in query:
                # Extract the part of the query after the indicator
                parts = query.split(indicator)
                if len(parts) > 1:
                    return parts[1].strip()
        
        return None

    def _extract_usage(self, query: str) -> Optional[str]:
        """Extract usage information from the query"""
        usage_indicators = [
            'use for', 'using for', 'will use', 'plan to use',
            'need it for', 'mainly for', 'primarily for'
        ]
        
        for indicator in usage_indicators:
            if indicator in query:
                parts = query.split(indicator)
                if len(parts) > 1:
                    return parts[1].strip()
        
        return None

    def _validate_response(self, response: Dict) -> bool:
        """Validate response has required fields"""
        if response.get('type') == ResponseTypes.FOLLOW_UP_QUESTION:
            return 'field' in response and 'question' in response
        return 'text' in response

    def _determine_agent_type(self, query: str) -> str:
        """Determine which agent should handle the query"""
        query_lower = query.lower()
        
        # Check for product-related keywords
        product_keywords = [
            'stroller', 'car seat', 'crib', 'monitor', 'carrier',
            'bottle', 'pump', 'diaper', 'clothes', 'toys',
            'price', 'cost', 'buy', 'purchase', 'recommend'
        ]
        
        if any(keyword in query_lower for keyword in product_keywords):
            return "baby_gear"
            
        # Add other agent type determinations here
        return "general"

    def _validate_message(self, message: str) -> bool:
        """Validate incoming message format and content"""
        if not message or not isinstance(message, str):
            return False
        if len(message.strip()) == 0:
            return False
        # Add more validation as needed
        return True

    def _create_error_response(self, error_message: str) -> Dict:
        """Create a standardized error response"""
        return {
            'type': 'error',
            'text': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'role': 'assistant'
        }

    def _create_message_object(self, content: str, role: str) -> Dict:
        """Create a standardized message object for storage"""
        return {
            'content': content,
            'role': role,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': self.session_id,
            'metadata': {
                'agent_type': self.current_agent.__class__.__name__ if self.current_agent else None
            }
        }

    @asynccontextmanager
    async def _get_db_transaction(self):
        """Context manager for database transactions"""
        try:
            # Start transaction
            yield
        except Exception as e:
            logger.error(f"Database transaction failed: {str(e)}")
            raise DatabaseError("Failed to store conversation data")

    async def process_query(self, message: str) -> Dict[str, Any]:
        """Process a user query and return the response"""
        try:
            # 1. Validate message
            if not self._validate_message(message):
                return self._create_error_response(
                    "Please provide a valid message"
                )

            # 2. Get appropriate agent and process query
            try:
                self.current_agent = self.agent_factory.get_agent(message)
                logger.info(f"Selected agent: {self.current_agent.__class__.__name__}")
                
                # Get context state safely
                try:
                    context_state = self.context.get_state()
                except AttributeError:
                    logger.warning("Context get_state not available, initializing empty context")
                    context_state = {
                        'original_query': message,
                        'gathered_info': {},
                        'conversation_history': [],
                        'agent_type': None,
                        'last_question': None
                    }
                
                # Process with context
                response = await self.current_agent.process_query(
                    message,
                    context=context_state
                )
                
                if not response or 'text' not in response:
                    raise ModelProcessingError("Invalid response from model")
                    
            except Exception as e:
                logger.error(f"Model processing error: {str(e)}")
                raise ModelProcessingError(str(e))

            # 3. Store conversation data in transaction
            try:
                async with self._get_db_transaction():
                    # Store user message
                    user_message = self._create_message_object(message, 'user')
                    await self.db.store_message(self.session_id, user_message)

                    # Store assistant response
                    assistant_message = self._create_message_object(response['text'], 'assistant')
                    await self.db.store_message(self.session_id, assistant_message)

                    # Extract and store context
                    if context := self._extract_and_store_context(message):
                        await self.db.store_context(self.session_id, context)
                        
                    logger.info("Successfully stored conversation data")
                    
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                # Continue with response even if storage fails
                logger.warning("Continuing with response despite storage failure")

            # 4. Format and return response
            formatted_response = {
                'type': response.get('type', 'answer'),
                'text': response['text'],
                'timestamp': datetime.utcnow().isoformat(),
                'role': 'assistant',
                'metadata': {
                    'agent_type': self.current_agent.__class__.__name__,
                    'confidence': response.get('confidence', 1.0)
                }
            }

            return formatted_response

        except ModelProcessingError as e:
            logger.error(f"Model processing error: {str(e)}")
            return self._create_error_response(
                "I'm having trouble processing your request. Please try again."
            )
            
        except DatabaseError as e:
            logger.error(f"Database error: {str(e)}")
            # If we have a response, return it despite DB error
            if 'formatted_response' in locals():
                return formatted_response
            return self._create_error_response(
                "I processed your request but couldn't save the conversation."
            )
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return self._create_error_response(
                "An unexpected error occurred. Please try again."
            )

    def reset(self) -> None:
        """Reset the session state and start a new conversation"""
        self.context = QueryContext()
        self.current_agent = None
        self.conversation_history = []
        # Create a new conversation in the database
        self.conversation_id = self.db.create_conversation()
        self.logger.info(f"Reset session: Created new conversation with ID: {self.conversation_id}")

    async def get_state(self) -> Dict[str, Any]:
        """Get the current state of the chat session"""
        try:
            # Get messages from both storages
            messages = await self.db.get_conversation_history(self.session_id)
            
            # Get context from persistent storage
            context = await self.db.get_context(self.session_id)
            
            return {
                'session_id': self.session_id,
                'messages': messages,
                'context': context
            }
        except Exception as e:
            logger.error(f"Error getting session state: {str(e)}")
            return {
                'session_id': self.session_id,
                'messages': [],
                'context': {}
            }

    def store_answer(self, field: str, answer: str) -> None:
        """Store an answer for a specific field in both memory and database"""
        self.context.add_clarification(field, answer)
        self.db.add_context_info(self.conversation_id, field, answer)

    def get_recent_context(self, limit: int = 5) -> List[Dict]:
        """Get recent conversation history from database"""
        history = self.db.get_conversation_history(self.conversation_id, limit)
        context_info = self.db.get_context_info(self.conversation_id)
        return {
            'history': history,
            'context': context_info
        }

    def _extract_and_store_context(self, query: str) -> Dict[str, str]:
        """Extract context from query and store it"""
        extracted_context = {}
        
        # Extract budget information
        budget = self._extract_budget(query)
        if budget:
            extracted_context['budget'] = budget
            self.context.gathered_info['budget'] = budget
            
        # Extract age information
        age = self._extract_age_from_query(query)
        if age:
            extracted_context['baby_age'] = age
            self.context.gathered_info['baby_age'] = age
            
        # Extract preferences
        preferences = self._extract_preferences(query)
        if preferences:
            extracted_context['preferences'] = preferences
            self.context.gathered_info['preferences'] = preferences
            
        # Extract usage information
        usage = self._extract_usage(query)
        if usage:
            extracted_context['usage'] = usage
            self.context.gathered_info['usage'] = usage
            
        # Extract sleep duration if relevant
        sleep_duration = self._extract_sleep_duration(query)
        if sleep_duration:
            extracted_context['sleep_duration'] = sleep_duration
            self.context.gathered_info['sleep_duration'] = sleep_duration
            
        # Extract location information
        location = self._extract_location(query)
        if location:
            extracted_context['location'] = location
            self.context.gathered_info['location'] = location
            
        print(f"\nExtracted context: {extracted_context}")
        return extracted_context

    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location information from query"""
        # List of known cities and locations
        locations = ["tel aviv", "jerusalem", "haifa", "eilat"]
        query_lower = query.lower()
        
        # Check for direct location mentions
        for location in locations:
            if location in query_lower:
                return location
                
        # Check for location indicators
        location_indicators = ["in", "at", "near", "around"]
        words = query_lower.split()
        for i, word in enumerate(words):
            if word in location_indicators and i + 1 < len(words):
                potential_location = words[i + 1]
                if potential_location in locations:
                    return potential_location
                
        return None

    def _update_context_from_response(self, response: Dict):
        """Update context based on agent response"""
        if response.get('type') == ResponseTypes.FOLLOW_UP_QUESTION:
            self.context.last_question_field = response.get('field', '')
        elif response.get('type') == ResponseTypes.ANSWER:
            # Clear the last question field since we got an answer
            self.context.last_question_field = None 