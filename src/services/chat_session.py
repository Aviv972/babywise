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
        self.logger.info(f"Created new chat session with ID: {self.conversation_id}")

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

    async def process_query(self, message: str) -> Dict[str, Any]:
        """Process a user query and return the response"""
        try:
            # Store user message in both storages
            await self.db.store_message(self.session_id, message, 'user')
            
            # Extract and store context
            context = self._extract_and_store_context(message)
            await self.db.store_context(self.session_id, context)
            
            # Get appropriate agent and process query
            agent = self.agent_factory.get_agent(message)
            
            # Check knowledge base for similar queries
            similar_responses = await self.db.search_knowledge_base(message)
            
            # Process with all available context
            response = await agent.process_query(
                message,
                context=context,
                similar_responses=similar_responses
            )
            
            # Store assistant response
            await self.db.store_message(
                self.session_id, 
                response.get('text', ''), 
                'assistant'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            raise

    async def _evaluate_context_sufficiency(self, query: str, context: Dict) -> bool:
        """Determine if we have sufficient context to provide a meaningful response"""
        evaluation_prompt = f"""
        Based on:
        - Original Query: {context['original_query']}
        - Current Query: {query}
        - Gathered Info: {json.dumps(context['gathered_info'], indent=2)}
        
        Determine if we have sufficient context to provide a meaningful response.
        Consider:
        1. Critical information needed for this type of query
        2. Quality and relevance of gathered information
        3. Relationship between current query and original question
        
        Return ONLY 'true' if we have sufficient context, or 'false' if we need more information.
        """
        
        result = await self.current_agent.llm_service.evaluate_context(evaluation_prompt)
        return result.lower() == 'true'

    async def _generate_follow_up_question(self, query: str, context: Dict) -> Dict:
        """Generate a contextually relevant follow-up question"""
        prompt = f"""
        You are an AI assistant helping with baby-related queries.
        Based on the following context:

        ORIGINAL QUERY: {context['original_query']}

        CURRENT INFORMATION:
        {json.dumps(context['gathered_info'], indent=2)}

        CONVERSATION HISTORY:
        {self.context.get_formatted_conversation_history()}

        Your task is to:
        1. Analyze what critical information is still needed
        2. Consider the natural flow of conversation
        3. Generate ONE follow-up question that:
           - Is most relevant to answering the original query
           - Builds upon existing context
           - Is phrased conversationally
           - Uses the same language as the original query

        The question should feel like a natural part of the conversation, not an interrogation.
        
        Return the question in JSON format:
        {{
            "type": "follow_up_question",
            "field": "the_field_name",
            "question": "your_question_here"
        }}
        """
        
        response = await self.current_agent.llm_service.generate_response(prompt)
        return json.loads(response['text'])

    async def _generate_response(self, query: str, context: Dict) -> Dict:
        """Generate a comprehensive response using all available context"""
        prompt = f"""
        You are a friendly and knowledgeable parenting assistant.
        
        CURRENT QUESTION: {query}
        ORIGINAL QUERY: {context['original_query']}

        WHAT WE KNOW:
        {self._format_gathered_info(context)}

        CONVERSATION HISTORY:
        {self._format_conversation_history(context.get('conversation_history', []))}

        Provide a response that:
        1. Shows empathy and understanding
        2. Directly answers their question first
        3. Gives practical, actionable advice
        4. Uses simple, clear language
        5. Includes helpful tips when relevant
        6. Maintains a warm, supportive tone

        Remember:
        - Parents are often tired and busy
        - Focus on practical solutions
        - Be encouraging and supportive
        - Use the same language as the parent
        - Keep responses concise but complete
        """
        
        response = await self.current_agent.llm_service.generate_response(prompt)
        return {
            'type': ResponseTypes.TEXT,
            'text': response['text']
        }

    def _format_gathered_info(self, context: Dict) -> str:
        """Format gathered information in a clear, readable way"""
        gathered_info = context.get('gathered_info', {})
        if not gathered_info:
            return "No additional context available yet"

        formatted_info = []
        for field, value in gathered_info.items():
            # Make the field name more readable
            readable_field = field.replace('_', ' ').title()
            formatted_info.append(f"- {readable_field}: {value}")
        
        return '\n'.join(formatted_info)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history in a clear, concise way"""
        if not history:
            return "No previous conversation"

        formatted_history = []
        # Only include last 3 exchanges for context
        for exchange in history[-3:]:
            formatted_history.extend([
                f"Parent: {exchange.get('query', '')}",
                f"Assistant: {exchange.get('response', '')}\n"
            ])
        
        return '\n'.join(formatted_history)

    def _prepare_enhanced_context(self, query: str) -> Dict:
        """Prepare enhanced context for LLM processing"""
        return {
            'original_query': self.context.original_query,
            'current_query': query,
            'gathered_info': self.context.gathered_info,
            'conversation_history': self.context.get_recent_history(3),  # Last 3 exchanges
            'agent_type': self.context.agent_type,
            'context_relevance': self.context.context_relevance_scores
        }

    def _process_response(self, query: str, response: Dict) -> None:
        """Process and store response with enhanced context tracking"""
        # Add response to conversation history
        self.context.add_to_history({
            'role': MessageRoles.MODEL,
            'content': response.get('text', response.get('question', '')),
            'metadata': {
                'type': response.get('type'),
                'field': response.get('field'),
                'relevance_score': self.context._calculate_relevance_score(
                    response.get('text', response.get('question', ''))
                )
            }
        })

        # If this was an answer to a specific field, store it
        if response.get('type') == ResponseTypes.FOLLOW_UP_QUESTION:
            self._extract_and_store_field_info(query, response.get('field'))

    def _extract_and_store_field_info(self, query: str, field: str) -> None:
        """Extract and store information for a specific field from the query"""
        if not field:
            return
            
        # Extract information based on field type
        value = None
        if field == 'budget':
            value = self._extract_budget(query)
        elif field == 'baby_age':
            value = self._extract_age_from_query(query)
        elif field == 'preferences':
            value = self._extract_preferences(query)
        elif field == 'usage':
            value = self._extract_usage(query)
            
        if value:
            self.context.add_clarification(field, value)

    def _has_critical_information(self) -> bool:
        """Check if we have enough critical information to provide a meaningful response"""
        if not self.context.agent_type:
            return True  # For general queries, we can always try to provide a response
            
        critical_fields = {
            AgentTypes.BABY_GEAR: ['budget', 'preferences'],  # Only really need budget and preferences
            AgentTypes.SLEEP_ROUTINE: ['baby_age'],  # Just need age for initial sleep advice
            AgentTypes.FEEDING: ['baby_age'],  # Just need age for initial feeding advice
            AgentTypes.MEDICAL_HEALTH: ['symptoms'],  # Need symptoms at minimum
            AgentTypes.DEVELOPMENT: ['baby_age']  # Need age for development advice
        }
        
        required = critical_fields.get(self.context.agent_type, [])
        if not required:
            return True  # If no critical fields defined, we can respond
            
        return any(field in self.context.gathered_info for field in required)

    def _get_missing_critical_fields(self) -> List[str]:
        """Get list of critical fields that are still missing"""
        if not self.context.agent_type:
            return []
            
        critical_fields = {
            AgentTypes.BABY_GEAR: ['budget', 'preferences'],
            AgentTypes.SLEEP_ROUTINE: ['baby_age'],
            AgentTypes.FEEDING: ['baby_age'],
            AgentTypes.MEDICAL_HEALTH: ['symptoms'],
            AgentTypes.DEVELOPMENT: ['baby_age']
        }
        
        required = critical_fields.get(self.context.agent_type, [])
        return [field for field in required if field not in self.context.gathered_info]

    def _extract_query_metadata(self, query: str) -> Dict[str, Any]:
        """Extract metadata from user query to enhance context tracking"""
        metadata = {
            'timestamp': datetime.utcnow().isoformat(),
            'query_length': len(query),
            'identified_topics': self._identify_topics(query),
            'potential_fields': self._identify_potential_fields(query)
        }
        return metadata

    def _extract_response_metadata(self, response: Dict) -> Dict[str, Any]:
        """Extract metadata from model response to enhance context tracking"""
        content = response.get('text', response.get('question', ''))
        metadata = {
            'timestamp': datetime.utcnow().isoformat(),
            'response_type': response.get('type'),
            'identified_topics': self._identify_topics(content),
            'addressed_fields': response.get('addressed_fields', [])
        }
        return metadata

    def _identify_topics(self, text: str) -> List[str]:
        """Identify topics in text for better context tracking"""
        text_lower = text.lower()
        topics = []
        
        topic_indicators = {
            'sleep': ['sleep', 'nap', 'bedtime', 'night', 'wake'],
            'feeding': ['feed', 'eat', 'food', 'nutrition', 'milk'],
            'health': ['health', 'doctor', 'sick', 'fever', 'medicine'],
            'development': ['growth', 'milestone', 'develop', 'skill', 'learn'],
            'gear': ['stroller', 'crib', 'car seat', 'bottle', 'diaper']
        }
        
        for topic, indicators in topic_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                topics.append(topic)
                
        return topics

    def _identify_potential_fields(self, query: str) -> List[str]:
        """Identify potential fields that might need clarification"""
        query_lower = query.lower()
        potential_fields = []
        
        field_indicators = {
            QuestionFields.BUDGET: ['cost', 'price', 'budget', 'afford'],
            QuestionFields.BABY_AGE: ['month', 'year', 'age', 'old'],
            QuestionFields.SLEEP_PATTERN: ['sleep', 'nap', 'night', 'wake'],
            QuestionFields.FEEDING_SCHEDULE: ['feed', 'eat', 'meal', 'time'],
            QuestionFields.HEALTH_ISSUES: ['health', 'sick', 'issue', 'problem']
        }
        
        for field, indicators in field_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                potential_fields.append(field)
                
        return potential_fields

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