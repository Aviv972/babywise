class ContextFields:
    GATHERED_INFO = 'gathered_info'
    ORIGINAL_QUERY = 'original_query'
    QUERY_TYPE = 'query_type'
    CURRENT_AGENT = 'current_agent'

class BaseFields:
    """Core fields that are common across many queries"""
    AGE = 'age'
    FREQUENCY = 'frequency'
    DURATION = 'duration'
    TIMING = 'timing'
    CONCERNS = 'concerns'
    PREFERENCES = 'preferences'
    CONSTRAINTS = 'constraints'
    SYMPTOMS = 'symptoms'
    HISTORY = 'history'

class QuestionFields:
    # Generic fields
    BUDGET = 'budget'
    FEATURES = 'features'
    USAGE = 'usage'
    BABY_AGE = 'baby_age'
    
    # Stroller specific fields
    STROLLER_TYPE = 'stroller_type'
    STORAGE_NEEDS = 'storage_needs'
    TERRAIN_USE = 'terrain_use'
    
    # Sleep related fields
    CURRENT_SLEEP_HOURS = 'current_sleep_hours'
    SLEEP_PATTERN = 'sleep_pattern'
    HEALTH_ISSUES = 'health_issues'

class MessageRoles:
    USER = 'user'
    MODEL = 'model'
    SYSTEM = 'system'

class ResponseTypes:
    ANSWER = 'answer'
    ERROR = 'error'
    FOLLOW_UP_QUESTION = 'follow_up_question'

class AgentTypes:
    # Baby Care & Health
    SLEEP_TRAINING = 'sleep_training'
    SLEEP_ROUTINE = 'sleep_routine'
    FEEDING = 'feeding'
    BREASTFEEDING = 'breastfeeding'
    NUTRITION = 'nutrition'
    HYGIENE = 'hygiene'
    
    # Medical & Safety
    MEDICAL_HEALTH = 'medical_health'
    EMERGENCY = 'emergency'
    FIRST_AID = 'first_aid'
    VACCINATION = 'vaccination'
    SAFETY = 'safety'
    
    # Development & Education
    DEVELOPMENT = 'development'
    LANGUAGE_DEVELOPMENT = 'language_development'
    SOCIAL_DEVELOPMENT = 'social_development'
    MILESTONE = 'milestone'
    EDUCATION = 'education'
    
    # Equipment & Resources
    BABY_GEAR = 'baby_gear'
    BUDGET = 'budget'
    TRAVEL = 'travel'
    
    # Parent Support
    MENTAL_HEALTH = 'mental_health'
    POSTPARTUM = 'postpartum'
    PARENTING_CHALLENGES = 'parenting_challenges'
    COMMUNITY_SUPPORT = 'community_support'
    
    # Daily Life
    DAILY_ROUTINE = 'daily_routine'
    ACTIVITY = 'activity'

class FieldMappings:
    """Maps various user inputs and LLM responses to standardized fields"""
    BUDGET_RELATED = [
        'budget', 'price', 'cost', 'money', 'spend',
        'expensive', 'cheap', 'affordable', 'under', 'maximum'
    ]
    
    STROLLER_TYPE_RELATED = [
        'side-by-side', 'tandem', 'inline', 'double',
        'twin stroller', 'style', 'design', 'type'
    ]
    
    STORAGE_RELATED = [
        'storage', 'capacity', 'space', 'basket',
        'compartment', 'carry', 'fit', 'hold'
    ]
    
    TERRAIN_RELATED = [
        'terrain', 'surface', 'road', 'path', 'street',
        'sidewalk', 'park', 'grass', 'beach', 'rough'
    ]
    
    @staticmethod
    def get_field_for_response(response_text: str) -> str:
        """Map a response text to a standardized field"""
        response_lower = response_text.lower()
        
        if any(term in response_lower for term in FieldMappings.BUDGET_RELATED):
            return QuestionFields.BUDGET
            
        if any(term in response_lower for term in FieldMappings.STROLLER_TYPE_RELATED):
            return QuestionFields.STROLLER_TYPE
            
        if any(term in response_lower for term in FieldMappings.STORAGE_RELATED):
            return QuestionFields.STORAGE_NEEDS
            
        if any(term in response_lower for term in FieldMappings.TERRAIN_RELATED):
            return QuestionFields.TERRAIN_USE
            
        return QuestionFields.FEATURES  # Default to features if no specific match

class RequiredFields:
    BY_AGENT = {
        AgentTypes.BABY_GEAR: [
            QuestionFields.BUDGET,
            QuestionFields.STROLLER_TYPE,
            QuestionFields.STORAGE_NEEDS,
            QuestionFields.TERRAIN_USE
        ],
        AgentTypes.SLEEP_ROUTINE: [
            QuestionFields.BABY_AGE,
            QuestionFields.CURRENT_SLEEP_HOURS,
            QuestionFields.SLEEP_PATTERN,
            QuestionFields.HEALTH_ISSUES
        ]
    }
    
    QUESTIONS = {
        QuestionFields.BUDGET: "What is your budget range?",
        QuestionFields.STROLLER_TYPE: "Do you prefer a side-by-side or tandem (inline) design?",
        QuestionFields.STORAGE_NEEDS: "How much storage capacity do you need?",
        QuestionFields.TERRAIN_USE: "Where will you primarily use the stroller (city streets, parks, rough terrain)?",
        QuestionFields.BABY_AGE: "How old is your baby?",
        QuestionFields.CURRENT_SLEEP_HOURS: "How many hours is your baby currently sleeping?",
        QuestionFields.SLEEP_PATTERN: "What is your baby's current sleep pattern?",
        QuestionFields.HEALTH_ISSUES: "Are there any health issues we should consider?"
    }
    
    MAX_FOLLOWUP_QUESTIONS = 3 

class DynamicFieldDetector:
    """Dynamic approach to field detection using semantic similarity"""
    
    # Core concepts that help identify field types
    TEMPORAL_INDICATORS = {
        'when', 'how often', 'frequency', 'daily', 'weekly', 'monthly',
        'schedule', 'routine', 'pattern', 'timing'
    }
    
    QUANTITY_INDICATORS = {
        'how much', 'how many', 'amount', 'number', 'quantity',
        'size', 'volume', 'duration'
    }
    
    PREFERENCE_INDICATORS = {
        'prefer', 'like', 'want', 'need', 'looking for',
        'interested in', 'would rather'
    }
    
    CONCERN_INDICATORS = {
        'worried', 'concerned', 'issue', 'problem', 'trouble',
        'difficulty', 'challenge', 'risk'
    }
    
    @staticmethod
    def extract_field_type(query: str) -> str:
        """
        Dynamically determine the type of field being discussed.
        This should be replaced with a more sophisticated NLP approach.
        """
        query_lower = query.lower()
        
        # Check temporal aspects
        if any(indicator in query_lower for indicator in DynamicFieldDetector.TEMPORAL_INDICATORS):
            return 'temporal'
            
        # Check quantity aspects
        if any(indicator in query_lower for indicator in DynamicFieldDetector.QUANTITY_INDICATORS):
            return 'quantity'
            
        # Check preferences
        if any(indicator in query_lower for indicator in DynamicFieldDetector.PREFERENCE_INDICATORS):
            return 'preference'
            
        # Check concerns
        if any(indicator in query_lower for indicator in DynamicFieldDetector.CONCERN_INDICATORS):
            return 'concern'
            
        return 'general'

class AgentContext:
    """Context requirements for different agent types"""
    
    @staticmethod
    def get_required_base_fields(agent_type: str) -> list:
        """Get the base fields required for a given agent type"""
        # These should be minimum required fields, not exhaustive
        AGENT_BASE_FIELDS = {
            AgentTypes.SLEEP_ROUTINE: [
                BaseFields.AGE,
                BaseFields.DURATION,
                BaseFields.TIMING
            ],
            AgentTypes.FEEDING: [
                BaseFields.AGE,
                BaseFields.FREQUENCY,
                BaseFields.CONCERNS
            ],
            AgentTypes.BABY_GEAR: [
                BaseFields.CONSTRAINTS,  # includes budget, space, etc.
                BaseFields.PREFERENCES,
                BaseFields.FREQUENCY    # how often they'll use it
            ]
        }
        return AGENT_BASE_FIELDS.get(agent_type, [BaseFields.AGE, BaseFields.CONCERNS])

    @staticmethod
    def should_ask_followup(agent_type: str, field_type: str, context: dict) -> bool:
        """Determine if a follow-up question should be asked based on context"""
        required_fields = AgentContext.get_required_base_fields(agent_type)
        return field_type in required_fields and field_type not in context.get('gathered_info', {}) 