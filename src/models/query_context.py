from typing import Dict, Optional, Any, List
from src.constants import ContextFields, QuestionFields, AgentTypes, RequiredFields
import json

class QueryContext:
    def __init__(self):
        self.original_query: Optional[str] = None
        self.query_type: Optional[str] = None
        self.gathered_info: Dict[str, Any] = {}
        self._last_field: Optional[str] = None
        self.question_count: int = 0
        self.agent_type: Optional[str] = None
        
    def update_from_response(self, response: Dict) -> None:
        """Update context based on response"""
        if response.get('previous_field'):
            self._last_field = response['previous_field']
            
    def add_clarification(self, field: str, value: str) -> None:
        """Add or update a clarification with context validation"""
        # Don't overwrite existing values unless they're empty or None
        if field not in self.gathered_info or not self.gathered_info[field]:
            self.gathered_info[field] = value
            self._last_field = field
            print(f"Added new clarification - Field: {field}, Value: {value}")
        else:
            print(f"Skipped overwriting existing value - Field: {field}, Current: {self.gathered_info[field]}, New: {value}")
        
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
        
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            ContextFields.ORIGINAL_QUERY: self.original_query,
            ContextFields.QUERY_TYPE: self.query_type,
            ContextFields.GATHERED_INFO: self.gathered_info
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueryContext':
        """Create instance from dictionary"""
        context = cls()
        context.original_query = data.get(ContextFields.ORIGINAL_QUERY)
        context.query_type = data.get(ContextFields.QUERY_TYPE)
        context.gathered_info = data.get(ContextFields.GATHERED_INFO, {})
        return context
        
    def get_formatted_context(self) -> str:
        """Get a formatted string of the current context"""
        return f"""Original Query: {self.original_query}

Current conversation context:
- Query Type: {self.query_type}
- Agent Type: {self.agent_type}

Information gathered so far:
{json.dumps(self.gathered_info, indent=2)}""" 