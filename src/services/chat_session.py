from typing import Dict, List, Optional
from src.database.db_manager import DatabaseManager
from src.services.agent_factory import AgentFactory
from src.constants import ContextFields, MessageRoles, ResponseTypes, QuestionFields
from src.models.query_context import QueryContext
from src.constants import AgentTypes
from src.constants import FieldMappings

class ChatSession:
    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory
        self.db = DatabaseManager()
        self.conversation_id = None
        self.context = QueryContext()
        self.current_agent = None

    def _process_answer(self, query: str, response: Dict) -> None:
        """Process and store answer in context"""
        query_lower = query.lower()
        
        # First, try to map the response to a specific field
        field = FieldMappings.get_field_for_response(query_lower)
        
        # Track the original query topic to ensure we stay focused
        original_topic = self.context.original_query.lower() if self.context.original_query else ''
        
        # Extract and store specific types of information while maintaining topic focus
        if 'month' in query_lower or 'year' in query_lower:
            age_info = self._extract_age_from_query(query_lower)
            if age_info:
                self.context.add_clarification(QuestionFields.BABY_AGE, age_info)
                print(f"Extracted and stored age information: {age_info}")
                # Immediately relate this back to original query
                if original_topic:
                    print(f"Maintaining focus on original topic: {original_topic}")

        # Extract budget information with topic focus
        if any(term in query_lower for term in FieldMappings.BUDGET_RELATED):
            budget_info = self._extract_budget(query_lower)
            if budget_info:
                self.context.add_clarification(QuestionFields.BUDGET, budget_info)
                print(f"Extracted and stored budget information: {budget_info}")
                # Validate budget info is relevant to original query
                if original_topic:
                    print(f"Budget information will be used in context of: {original_topic}")

        # Extract sleep duration with context awareness
        if 'hour' in query_lower or 'hr' in query_lower:
            sleep_info = self._extract_sleep_duration(query_lower)
            if sleep_info:
                self.context.add_clarification(QuestionFields.CURRENT_SLEEP_HOURS, sleep_info)
                print(f"Extracted and stored sleep information: {sleep_info}")
                # Ensure sleep info relates to original query
                if original_topic:
                    print(f"Sleep information will be used in context of: {original_topic}")

        # Store the response field if provided, with context validation
        if response.get('previous_field'):
            mapped_field = FieldMappings.get_field_for_response(response['previous_field'])
            # Validate the field is relevant to original query
            if self._is_field_relevant_to_query(mapped_field, original_topic):
                self.context.add_clarification(mapped_field, query)
                print(f"Stored relevant answer for field {mapped_field}: {query}")
            else:
                print(f"Warning: Field {mapped_field} may not be relevant to original query: {original_topic}")
            
        # If this was a direct answer to a previous question, store with context check
        if self.context.get_last_field():
            last_field = self.context.get_last_field()
            if self._is_field_relevant_to_query(last_field, original_topic):
                self.context.add_clarification(last_field, query)
                print(f"Stored relevant answer for last field {last_field}: {query}")
            else:
                print(f"Warning: Last field {last_field} may not be relevant to original query: {original_topic}")

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
            if word.isdigit() and i + 1 < len(words):
                if 'month' in words[i + 1]:
                    return f"{word} months"
                if 'year' in words[i + 1]:
                    return f"{word} years"
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
        words = query.split()
        for i, word in enumerate(words):
            # Handle "under X" or "less than X" format
            if word in ['under', 'below', 'less'] and i + 1 < len(words):
                next_word = words[i + 1].replace('$', '').replace(',', '')
                if next_word.isdigit():
                    return f"Under ${next_word}"
                    
            # Handle "X dollars" or "$X" format
            if word.startswith('$') or word.isdigit():
                amount = word.replace('$', '').replace(',', '')
                if amount.isdigit():
                    return f"${amount}"
        return None

    def _validate_response(self, response: Dict) -> bool:
        """Validate response has required fields"""
        if response.get('type') == ResponseTypes.FOLLOW_UP_QUESTION:
            return 'field' in response and 'question' in response
        return 'text' in response

    def _determine_agent_type(self, query: str) -> str:
        """Determine the most appropriate agent type based on query content"""
        query = query.lower()
        
        # Sleep-related queries
        if any(term in query for term in ['sleep', 'nap', 'bedtime', 'night', 'wake']):
            if 'training' in query:
                print(f"Selected Agent: {AgentTypes.SLEEP_TRAINING} - Query contains sleep training terms")
                return AgentTypes.SLEEP_TRAINING
            print(f"Selected Agent: {AgentTypes.SLEEP_ROUTINE} - Query contains sleep routine terms")
            return AgentTypes.SLEEP_ROUTINE
            
        # Feeding and nutrition
        if any(term in query for term in ['feed', 'eat', 'food', 'nutrition', 'milk']):
            if 'breast' in query:
                print(f"Selected Agent: {AgentTypes.BREASTFEEDING} - Query contains breastfeeding terms")
                return AgentTypes.BREASTFEEDING
            print(f"Selected Agent: {AgentTypes.FEEDING} - Query contains feeding terms")
            return AgentTypes.FEEDING
            
        # Medical and emergency
        if any(term in query for term in ['emergency', 'hospital', 'doctor', 'pain', 'fever']):
            if 'emergency' in query:
                print(f"Selected Agent: {AgentTypes.EMERGENCY} - Query contains emergency terms")
                return AgentTypes.EMERGENCY
            print(f"Selected Agent: {AgentTypes.MEDICAL_HEALTH} - Query contains medical terms")
            return AgentTypes.MEDICAL_HEALTH
            
        # Development and milestones
        if any(term in query for term in ['development', 'milestone', 'grow', 'skill']):
            if 'language' in query:
                print(f"Selected Agent: {AgentTypes.LANGUAGE_DEVELOPMENT} - Query contains language development terms")
                return AgentTypes.LANGUAGE_DEVELOPMENT
            if 'social' in query:
                print(f"Selected Agent: {AgentTypes.SOCIAL_DEVELOPMENT} - Query contains social development terms")
                return AgentTypes.SOCIAL_DEVELOPMENT
            print(f"Selected Agent: {AgentTypes.DEVELOPMENT} - Query contains general development terms")
            return AgentTypes.DEVELOPMENT
            
        # Equipment and gear
        if any(term in query for term in ['stroller', 'crib', 'car seat', 'gear', 'buy']):
            print(f"Selected Agent: {AgentTypes.BABY_GEAR} - Query contains baby gear terms")
            return AgentTypes.BABY_GEAR
            
        # Default to development agent if no specific match
        print(f"Selected Agent: {AgentTypes.DEVELOPMENT} - No specific agent match, using default")
        return AgentTypes.DEVELOPMENT

    async def process_query(self, query: str) -> Dict:
        try:
            # Initialize conversation if new
            if not self.conversation_id:
                self.conversation_id = self.db.create_conversation()
                self.context.original_query = query
                
                # Determine agent type based on query content
                self.context.agent_type = self._determine_agent_type(query)
                self.context.query_type = f"{self.context.agent_type}_query"
                
                print(f"\nNew conversation started:")
                print(f"Original Query: {query}")
                print(f"Agent Type: {self.context.agent_type}")
                print(f"Query Type: {self.context.query_type}")
                
                self.current_agent = await self.agent_factory.get_agent_for_query(
                    query=query,
                    agent_type=self.context.agent_type
                )

            # Print current context state
            print(f"\nCurrent Context State:")
            print(self.context.get_formatted_context())

            # Store user message
            self.db.add_message(conversation_id=self.conversation_id, content=query, role=MessageRoles.USER)
            history = self.db.get_conversation_history(self.conversation_id, limit=10)
            
            # Process the query with context
            response = await self.current_agent.process_query(
                query=query,
                context=self.context.to_dict(),
                chat_history=history
            )

            if not self._validate_response(response):
                return {
                    'type': ResponseTypes.ERROR,
                    'text': 'Invalid response format from agent.'
                }

            # Store model response
            self.db.add_message(
                conversation_id=self.conversation_id,
                content=response.get('text', response.get('question', '')),
                role=MessageRoles.MODEL
            )

            # Process and store the answer
            self._process_answer(query, response)
            
            # Print updated context after processing
            print(f"\nUpdated Context State:")
            print(self.context.get_formatted_context())
            
            # If this is a follow-up question, check if we need to ask it
            if response.get('type') == ResponseTypes.FOLLOW_UP_QUESTION:
                # Get the field this question is asking about
                field = FieldMappings.get_field_for_response(response.get('question', ''))
                
                # If we already have this information, skip the question
                if self.context.is_field_answered(field):
                    print(f"Already have information for field {field}, skipping question")
                    return await self.current_agent.generate_final_response(
                        context=self.context.to_dict(),
                        chat_history=history
                    )
                    
                self.context.increment_question_count()
                print(f"Incremented question count to: {self.context.question_count}")

            # Check if we should generate final response
            if self.context.should_generate_final_response():
                print("\nGenerating final response - all required information gathered or max questions reached")
                return await self.current_agent.generate_final_response(
                    context=self.context.to_dict(),
                    chat_history=history
                )

            return response

        except Exception as e:
            print(f"Error in chat session: {e}")
            return {
                'type': ResponseTypes.ERROR,
                'text': str(e)
            }

    def reset(self) -> None:
        """Reset the session state"""
        self.context = QueryContext()
        self.current_agent = None
        self.conversation_id = None

    def get_state(self) -> Dict:
        """Get current session state"""
        return self.context.to_dict()

    def store_answer(self, field: str, answer: str) -> None:
        """Store an answer for a specific field"""
        self.context.add_clarification(field, answer)

    def get_recent_context(self, limit: int = 5) -> List[Dict]:
        """Get recent conversation history"""
        return self.db.get_conversation_history(
            self.conversation_id,
            limit=limit
        ) 