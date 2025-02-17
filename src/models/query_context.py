from typing import Dict, Optional, Any, List, Tuple
from src.constants import ContextFields, QuestionFields, AgentTypes, RequiredFields
import json
from datetime import datetime, timedelta

class QueryContext:
    def __init__(self):
        self._data = {
            'original_query': None,
            'gathered_info': {},
            'conversation_history': [],
            'agent_type': None,
            'context_relevance_scores': {},
            'last_question_field': None
        }
        self.question_count: int = 0
        self.query_type: Optional[str] = None
        self._last_field: Optional[str] = None
        self.field_timestamps: Dict[str, str] = {}
        
    def get(self, key, default=None):
        """Get a value from the context data"""
        return self._data.get(key, default)

    def __getitem__(self, key):
        """Allow dictionary-style access to context data"""
        return self._data[key]

    def __setitem__(self, key, value):
        """Allow dictionary-style setting of context data"""
        self._data[key] = value

    @property
    def original_query(self):
        return self._data['original_query']

    @original_query.setter
    def original_query(self, value):
        self._data['original_query'] = value

    @property
    def gathered_info(self):
        return self._data['gathered_info']

    @property
    def conversation_history(self):
        return self._data['conversation_history']

    @property
    def agent_type(self):
        return self._data['agent_type']

    @agent_type.setter
    def agent_type(self, value):
        self._data['agent_type'] = value

    def add_clarification(self, field: str, value: str):
        """Add or update a field in gathered_info"""
        self._data['gathered_info'][field] = value

    def add_to_history(self, message: dict):
        """Add a message to conversation history"""
        self._data['conversation_history'].append(message)

    def get_recent_history(self, limit: int = 3) -> list:
        """Get the most recent conversation history"""
        return self._data['conversation_history'][-limit:]

    def to_dict(self) -> dict:
        """Convert context to dictionary format"""
        return self._data.copy()

    def get_formatted_conversation_history(self) -> str:
        """Format conversation history for prompts"""
        history = []
        for msg in self._data['conversation_history'][-3:]:  # Last 3 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            history.append(f"{role.capitalize()}: {content}")
        return "\n".join(history) if history else "No previous conversation"

    def add_to_history(self, message: Dict[str, Any]) -> None:
        """Add a message to conversation history with enhanced context linking and relevance scoring"""
        if not all(k in message for k in ['role', 'content']):
            print("Warning: Message missing required fields")
            return
            
        # Calculate relevance score based on relation to original query
        relevance_score = self._calculate_relevance_score(message['content'])
        
        # Add enhanced context metadata
        message_with_context = {
            **message,
            'timestamp': datetime.utcnow().isoformat(),
            'context_snapshot': {
                'query_type': self.query_type,
                'gathered_info': self.gathered_info.copy(),
                'question_count': self.question_count,
                'relevance_score': relevance_score,
                'related_fields': self._get_related_fields(message['content'])
            }
        }
        
        self.conversation_history.append(message_with_context)
        self._update_context_relevance(message['content'], relevance_score)
        print(f"Added message to history with context - Role: {message['role']}, Relevance: {relevance_score:.2f}")

    def _calculate_relevance_score(self, content: str, field: Optional[str] = None) -> float:
        """Calculate relevance score for content based on original query and context"""
        if not self.original_query:
            return 1.0  # No context to compare against
            
        # Get base scores
        keyword_overlap = self._calculate_keyword_overlap(content)
        context_overlap = self._calculate_context_overlap(content)
        topic_score = self._calculate_topic_relevance(content)
        field_score = self._calculate_field_relevance(content, field) if field else 0.0
        
        # Get relevant topics for weighting
        relevant_topics = self._get_relevant_topics()
        
        # Adjust weights based on content type
        weights = {
            'keyword': 0.3,
            'context': 0.3,
            'topic': 0.2,
            'field': 0.2
        }
        
        # Boost weights for high-priority fields
        if field in [QuestionFields.BUDGET, QuestionFields.BABY_AGE, QuestionFields.USAGE]:
            weights['field'] = 0.4
            weights['context'] = 0.3
            weights['keyword'] = 0.2
            weights['topic'] = 0.1
            
        # Calculate combined score
        score = (
            weights['keyword'] * keyword_overlap +
            weights['context'] * context_overlap +
            weights['topic'] * topic_score +
            weights['field'] * field_score
        )
        
        # Apply topic-specific boosts
        if 'travel' in relevant_topics and any(term in content.lower() for term in ['travel', 'airplane', 'transport']):
            score *= 1.5
            
        if 'stroller' in relevant_topics and any(term in content.lower() for term in ['stroller', 'wheel', 'fold']):
            score *= 1.3
            
        return min(score, 1.0)  # Cap at 1.0

    def _calculate_keyword_overlap(self, content: str) -> float:
        """Calculate keyword overlap between content and original query"""
        if not self.original_query:
            return 0.0
            
        query_keywords = set(self.original_query.lower().split())
        content_keywords = set(content.lower().split())
        
        overlap = len(query_keywords.intersection(content_keywords))
        return overlap / max(len(query_keywords), 1)

    def _calculate_context_overlap(self, content: str) -> float:
        """Calculate overlap with current context"""
        if not self.gathered_info:
            return 0.0
            
        # Get all values from gathered info
        context_values = ' '.join(str(v) for v in self.gathered_info.values()).lower()
        content_lower = content.lower()
        
        # Split into words and calculate overlap
        context_words = set(context_values.split())
        content_words = set(content_lower.split())
        
        overlap = len(context_words.intersection(content_words))
        return overlap / max(len(context_words), 1)

    def _calculate_topic_relevance(self, content: str) -> float:
        """Calculate relevance to current topics"""
        relevant_topics = self._get_relevant_topics()
        if not relevant_topics:
            return 0.0
            
        content_lower = content.lower()
        topic_matches = sum(1 for topic in relevant_topics if topic in content_lower)
        return topic_matches / len(relevant_topics)

    def _calculate_field_relevance(self, content: str, field: Optional[str] = None) -> float:
        """Calculate relevance score for a specific field"""
        if not field:
            return 0.0
            
        # Get field indicators
        indicators = self._get_field_indicators(field)
        if not indicators:
            return 0.0
            
        # Check for indicator presence
        content_lower = content.lower()
        matches = sum(1 for indicator in indicators if indicator in content_lower)
        
        # Calculate base score
        base_score = matches / len(indicators)
        
        # Apply field-specific boosts
        if field == QuestionFields.BUDGET and any(term in content_lower for term in ['$', 'cost', 'price']):
            base_score *= 1.5
        elif field == QuestionFields.BABY_AGE and any(term in content_lower for term in ['month', 'year', 'old']):
            base_score *= 1.5
        elif field == QuestionFields.USAGE and any(term in content_lower for term in ['travel', 'walk', 'use']):
            base_score *= 1.5
            
        return min(base_score, 1.0)

    def _get_field_indicators(self, field: str) -> List[str]:
        """Get indicator terms for a specific field"""
        indicators = {
            QuestionFields.BUDGET: ['cost', 'price', 'budget', '$', 'afford', 'spend'],
            QuestionFields.BABY_AGE: ['month', 'year', 'old', 'age', 'baby'],
            QuestionFields.USAGE: ['use', 'travel', 'walk', 'need', 'purpose'],
            QuestionFields.FEATURES: ['feature', 'lightweight', 'fold', 'storage'],
            QuestionFields.STROLLER_TYPE: ['type', 'brand', 'model', 'stroller']
        }
        return indicators.get(field, [])

    def _is_field_relevant_to_topic(self, field: str, topic: str) -> bool:
        """Check if a field is relevant to the given topic"""
        field_topic_map = {
            QuestionFields.BUDGET: ['stroller', 'gear', 'buy', 'cost', 'purchase'],
            QuestionFields.BABY_AGE: ['*'],  # Age is always relevant
            QuestionFields.SLEEP_PATTERN: ['sleep', 'routine', 'schedule'],
            QuestionFields.FEATURES: ['stroller', 'gear', 'equipment'],
            QuestionFields.USAGE: ['stroller', 'gear', 'equipment', 'travel']
        }
        
        # Age is always relevant
        if field == QuestionFields.BABY_AGE:
            return True
            
        # Check topic relevance
        relevant_topics = field_topic_map.get(field, [])
        return any(t in topic for t in relevant_topics)

    def _get_relevant_topics(self) -> List[str]:
        """Get topics relevant to the current conversation"""
        if not self.original_query:
            return []
            
        query_lower = self.original_query.lower()
        topics = []
        
        # Map common topics
        topic_indicators = {
            'stroller': ['stroller', 'gear', 'equipment', 'travel'],
            'sleep': ['sleep', 'nap', 'bedtime', 'night'],
            'feeding': ['feed', 'eat', 'food', 'milk'],
            'health': ['health', 'doctor', 'medical'],
            'development': ['growth', 'milestone', 'skill']
        }
        
        for topic, indicators in topic_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                topics.append(topic)
                
        return topics

    def _get_related_fields(self, content: str) -> List[str]:
        """Identify fields related to the message content"""
        content_lower = content.lower()
        related_fields = []
        
        # Map common phrases to fields
        field_indicators = {
            QuestionFields.BUDGET: ['cost', 'price', 'budget', 'afford'],
            QuestionFields.BABY_AGE: ['month', 'year', 'age', 'old'],
            QuestionFields.SLEEP_PATTERN: ['sleep', 'nap', 'night', 'wake'],
            # Add more field mappings as needed
        }
        
        for field, indicators in field_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                related_fields.append(field)
                
        return related_fields

    def _update_context_relevance(self, content: str, score: float) -> None:
        """Update context relevance scores with enhanced topic tracking"""
        # Get relevant topics for this content
        topics = self._get_relevant_topics()
        content_lower = content.lower()
        
        # Update scores for each topic
        for topic in topics:
            # Get field indicators for this topic
            field_indicators = self._get_field_indicators(topic)
            
            # Check if content matches any field indicators
            if any(term in content_lower for term in field_indicators):
                # Apply a higher base score for direct matches
                base_score = 0.5
                
                # Boost score for important topics
                if topic in ['stroller', 'sleep', 'feeding']:
                    base_score = 0.7
                
                # Update the score, keeping the higher value
                self.context_relevance_scores[topic] = max(
                    base_score + score,  # Combine base score with content relevance
                    self.context_relevance_scores.get(topic, 0.0)
                )
        
        # Special handling for important content types
        if any(term in content_lower for term in ['travel', 'airplane', 'transport']):
            self.context_relevance_scores['travel'] = max(
                0.7 + score,  # Higher base score for travel
                self.context_relevance_scores.get('travel', 0.0)
            )
            
        if any(term in content_lower for term in ['budget', 'cost', 'price', '$']):
            self.context_relevance_scores['budget'] = max(
                0.8 + score,  # Very high base score for budget
                self.context_relevance_scores.get('budget', 0.0)
            )
            
        if any(term in content_lower for term in ['month', 'year', 'age']):
            self.context_relevance_scores['age'] = max(
                0.8 + score,  # Very high base score for age
                self.context_relevance_scores.get('age', 0.0)
            )
            
        # Ensure scores don't exceed 1.0
        for topic in self.context_relevance_scores:
            self.context_relevance_scores[topic] = min(self.context_relevance_scores[topic], 1.0)

    def update_from_response(self, response: Dict) -> None:
        """Update context based on response with history tracking"""
        if response.get('previous_field'):
            self._last_field = response['previous_field']
            
        # Track response in history
        if 'text' in response:
            self.add_to_history({
                'role': response.get('role', 'assistant'),
                'content': response['text']
            })
            
    def add_clarification(self, field: str, value: str) -> None:
        """Add a clarification with enhanced context tracking"""
        if not field or not value:
            return
            
        # Calculate relevance score for this clarification
        relevance_score = self._calculate_relevance_score(value, field)
        
        # Store the value in gathered_info
        self.gathered_info[field] = value
        
        # Update relevance scores with a higher base score for clarifications
        self.context_relevance_scores[field] = max(
            0.5 + relevance_score,  # Add base score to ensure minimum relevance
            self.context_relevance_scores.get(field, 0.0)
        )
        
        # Add to history for tracking
        self.add_to_history({
            'role': 'system',
            'content': f"Clarification added - {field}: {value}",
            'metadata': {
                'field': field,
                'value': value,
                'relevance_score': relevance_score,
                'type': 'clarification'
            }
        })
        
        # Update last field
        self._last_field = field
        
        print(f"Added new clarification - Field: {field}, Value: {value}")
        
        # Update context relevance with the new information
        self._update_context_relevance(value, relevance_score)
        
        # Validate context integrity
        if not self._validates_context_integrity(field, value):
            print(f"Warning: Clarification may not be relevant to current context - Field: {field}, Value: {value}")
        
        # Update question count if this was an answer to a question
        if field in self.get_missing_required_fields():
            self.increment_question_count()
        
    def _validates_context_integrity(self, field: str, value: str) -> bool:
        """Validate that new information maintains context integrity"""
        if not self.original_query:
            return True  # No context to validate against
            
        # Define stroller-specific validation rules
        stroller_validation = {
            'relevant_fields': [
                'budget', 'stroller_type', 'storage_needs', 'terrain_use', 
                'age', 'weight', 'preferences', 'features'
            ],
            'feature_mapping': {
                'lightweight': ['weight', 'portability'],
                'compact': ['folding', 'storage'],
                'travel': ['portability', 'durability'],
                'jogging': ['wheels', 'suspension'],
                'storage': ['capacity', 'basket_size']
            },
            'budget_related': ['cost', 'price', 'under', 'within', 'range'],
            'always_relevant': ['age', 'weight', 'special_needs', 'preferences']
        }
        
        query_lower = self.original_query.lower()
        if 'stroller' in query_lower:
            # For stroller queries, strictly validate fields
            if field in stroller_validation['always_relevant']:
                return True
                
            if field in stroller_validation['relevant_fields']:
                return True
                
            # Check if the field maps to a relevant stroller feature
            value_lower = value.lower()
            for feature, related_terms in stroller_validation['feature_mapping'].items():
                if feature in value_lower or any(term in value_lower for term in related_terms):
                    return True
                    
            # Check if it's budget related
            if any(term in value_lower for term in stroller_validation['budget_related']):
                return True
                
            print(f"Warning: Field '{field}' with value '{value}' may not be relevant to stroller query")
            return False
            
        return True  # For non-stroller queries, be more permissive
        
    def get_last_field(self) -> Optional[str]:
        """Get the last field that was clarified"""
        return self._last_field
        
    def is_field_answered(self, field: str) -> bool:
        """Check if a field has been answered"""
        return field in self.gathered_info and bool(self.gathered_info[field])
        
    def get_missing_required_fields(self) -> List[str]:
        """Get list of required fields that haven't been answered"""
        if not self.agent_type or self.agent_type not in RequiredFields.BY_AGENT:
            return []
            
        required_fields = RequiredFields.BY_AGENT[self.agent_type]
        missing = [field for field in required_fields if not self.is_field_answered(field)]
        print(f"Missing required fields for {self.agent_type}: {missing}")
        return missing
        
    def should_generate_final_response(self) -> bool:
        """Determine if we should generate a final response"""
        missing_fields = self.get_missing_required_fields()
        max_questions_reached = self.question_count >= RequiredFields.MAX_FOLLOWUP_QUESTIONS
        
        if not missing_fields:
            print("Generating final response: All required fields collected")
            return True
        if max_questions_reached:
            print(f"Generating final response: Max questions ({RequiredFields.MAX_FOLLOWUP_QUESTIONS}) reached")
            return True
        return False
        
    def increment_question_count(self) -> None:
        """Increment the number of questions asked"""
        self.question_count += 1
        print(f"Incremented question count to {self.question_count}")
        
    def merge_history_with_context(self) -> Dict[str, Any]:
        """Merge conversation history with current context using relevance-based filtering"""
        relevant_history = self.get_recent_history()
        
        # Extract most relevant fields based on context scores
        relevant_fields = {
            field: value for field, value in self.gathered_info.items()
            if self.context_relevance_scores.get(field, 0.0) > 0.3  # Relevance threshold
        }
        
        return {
            ContextFields.ORIGINAL_QUERY: self.original_query,
            ContextFields.QUERY_TYPE: self.query_type,
            ContextFields.GATHERED_INFO: relevant_fields,
            ContextFields.CONVERSATION_HISTORY: relevant_history,
            ContextFields.AGENT_TYPE: self.agent_type,
            'context_relevance': self.context_relevance_scores
        }
        
    def get_formatted_context(self) -> str:
        """Get a formatted string of the current context with history"""
        history_str = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in self.get_recent_history(5)  # Show last 5 messages
        ])
        
        return f"""Original Query: {self.original_query}

Current conversation context:
- Query Type: {self.query_type}
- Agent Type: {self.agent_type}

Information gathered so far:
{json.dumps(self.gathered_info, indent=2)}

Recent conversation history:
{history_str}"""

    def get_formatted_conversation_history(self, limit: int = 5) -> str:
        """Format recent conversation history for LLM prompts"""
        history = self.get_recent_history(limit)
        formatted_history = []
        
        for msg in history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted_history.append(f"{role}: {content}")
            
        return "\n".join(formatted_history)

    def merge_with_current_query(self, query: str) -> Dict:
        """Merge current query with existing context"""
        return {
            'original_query': self.original_query,
            'current_query': query,
            'gathered_info': self.gathered_info,
            'conversation_history': self.get_recent_history(),
            'agent_type': self.agent_type,
            'context_relevance': self.context_relevance_scores
        }

    def update_context_relevance(self, field: str, value: str, score: float) -> None:
        """Update relevance score for a specific field"""
        self.context_relevance_scores[field] = min(score, 1.0)
        print(f"Updated relevance score for {field}: {score}")

    def get_missing_critical_fields(self) -> List[str]:
        """Get list of critical fields that are still missing"""
        if not self.agent_type or self.agent_type not in RequiredFields.BY_AGENT:
            return []
            
        required_fields = RequiredFields.BY_AGENT[self.agent_type]
        missing = [field for field in required_fields if not self.is_field_answered(field)]
        print(f"Missing critical fields for {self.agent_type}: {missing}")
        return missing

    def has_sufficient_context(self) -> bool:
        """Check if we have sufficient context to provide a meaningful response"""
        missing_fields = self.get_missing_critical_fields()
        
        # If no missing required fields, we have sufficient context
        if not missing_fields:
            return True
            
        # If we've asked too many questions, proceed anyway
        if self.question_count >= RequiredFields.MAX_FOLLOWUP_QUESTIONS:
            return True
            
        return False

    def get_field_relevance(self, field: str) -> float:
        """Get relevance score for a specific field"""
        return self.context_relevance_scores.get(field, 0.0)

    def cleanup_outdated_context(self, max_age_hours: int = 24) -> None:
        """Remove outdated context information"""
        current_time = datetime.utcnow()
        max_age = timedelta(hours=max_age_hours)
        
        # Clean up conversation history
        self.conversation_history = [
            msg for msg in self.conversation_history
            if (current_time - datetime.fromisoformat(msg['timestamp'])).total_seconds() / 3600 < max_age_hours
        ]
        
        # Clean up relevance scores
        for field in list(self.context_relevance_scores.keys()):
            if self.get_field_relevance(field) < 0.3:  # Remove low relevance fields
                del self.context_relevance_scores[field]
                if field in self.gathered_info:
                    del self.gathered_info[field]

    def get_context_summary(self) -> str:
        """Get a human-readable summary of current context state"""
        return f"""Context Summary:
Original Query: {self.original_query}
Agent Type: {self.agent_type}
Question Count: {self.question_count}

Gathered Information:
{json.dumps(self.gathered_info, indent=2)}

Recent Conversation:
{self.get_formatted_conversation_history(3)}

Missing Critical Fields:
{', '.join(self.get_missing_critical_fields()) or 'None'}
""" 