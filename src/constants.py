from typing import List, Dict, Any

class ContextFields:
    GATHERED_INFO = 'gathered_info'
    ORIGINAL_QUERY = 'original_query'
    QUERY_TYPE = 'query_type'
    CURRENT_AGENT = 'current_agent'
    AGENT_TYPE = 'agent_type'
    CONVERSATION_HISTORY = 'conversation_history'

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
    BABY_WEIGHT = 'baby_weight'
    BABY_HEIGHT = 'baby_height'
    CONCERNS = 'concerns'
    SYMPTOMS = 'symptoms'
    PREFERENCES = 'preferences'
    FREQUENCY = 'frequency'
    DURATION = 'duration'
    TIMING = 'timing'
    
    # Stroller specific fields
    STROLLER_TYPE = 'stroller_type'
    STORAGE_NEEDS = 'storage_needs'
    TERRAIN_USE = 'terrain_use'
    
    # Sleep related fields
    CURRENT_SLEEP_HOURS = 'current_sleep_hours'
    SLEEP_PATTERN = 'sleep_pattern'
    SLEEP_ENVIRONMENT = 'sleep_environment'
    SLEEP_ROUTINE = 'sleep_routine'
    SLEEP_TRAINING_METHOD = 'sleep_training_method'
    NAP_SCHEDULE = 'nap_schedule'
    NIGHT_WAKINGS = 'night_wakings'
    
    # Health related fields
    HEALTH_ISSUES = 'health_issues'
    MEDICATIONS = 'medications'
    ALLERGIES = 'allergies'
    VACCINATION_HISTORY = 'vaccination_history'
    TEMPERATURE = 'temperature'
    MEDICAL_HISTORY = 'medical_history'
    
    # Feeding related fields
    FEEDING_SCHEDULE = 'feeding_schedule'
    FEEDING_TYPE = 'feeding_type'
    FEEDING_AMOUNT = 'feeding_amount'
    FEEDING_FREQUENCY = 'feeding_frequency'
    BREAST_FEEDING_ISSUES = 'breast_feeding_issues'
    BOTTLE_PREFERENCES = 'bottle_preferences'
    SOLID_FOODS = 'solid_foods'
    FOOD_ALLERGIES = 'food_allergies'
    
    # Development related fields
    MILESTONES = 'milestones'
    MOTOR_SKILLS = 'motor_skills'
    LANGUAGE_SKILLS = 'language_skills'
    SOCIAL_SKILLS = 'social_skills'
    COGNITIVE_DEVELOPMENT = 'cognitive_development'
    PLAYTIME_ACTIVITIES = 'playtime_activities'
    
    # Parent related fields
    PARENT_CONCERNS = 'parent_concerns'
    PARENT_HEALTH = 'parent_health'
    SUPPORT_SYSTEM = 'support_system'
    WORK_SCHEDULE = 'work_schedule'
    CHILDCARE_ARRANGEMENT = 'childcare_arrangement'
    
    # Environment related fields
    HOME_ENVIRONMENT = 'home_environment'
    SIBLINGS = 'siblings'
    PETS = 'pets'
    CLIMATE = 'climate'
    LIVING_SPACE = 'living_space'

class MessageRoles:
    USER = 'user'
    MODEL = 'assistant'
    SYSTEM = 'system'

class ResponseTypes:
    TEXT = 'text'
    ANSWER = 'answer'
    ERROR = 'error'
    FOLLOW_UP_QUESTION = 'follow_up_question'

class AgentTypes:
    # General
    GENERAL = 'general'
    
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
            QuestionFields.PREFERENCES,  # For features like electric/manual, noise level, etc.
            QuestionFields.USAGE,        # How often they'll use it
            QuestionFields.FEATURES      # Specific features they need
        ],
        AgentTypes.SLEEP_ROUTINE: [
            QuestionFields.BABY_AGE,
            QuestionFields.CURRENT_SLEEP_HOURS,
            QuestionFields.SLEEP_PATTERN,
            QuestionFields.SLEEP_ENVIRONMENT,
            QuestionFields.NAP_SCHEDULE
        ],
        AgentTypes.FEEDING: [
            QuestionFields.BABY_AGE,
            QuestionFields.FEEDING_TYPE,
            QuestionFields.FEEDING_FREQUENCY,
            QuestionFields.FEEDING_AMOUNT
        ],
        AgentTypes.MEDICAL_HEALTH: [
            QuestionFields.BABY_AGE,
            QuestionFields.SYMPTOMS,
            QuestionFields.TEMPERATURE,
            QuestionFields.MEDICAL_HISTORY,
            QuestionFields.MEDICATIONS
        ],
        AgentTypes.DEVELOPMENT: [
            QuestionFields.BABY_AGE,
            QuestionFields.MILESTONES,
            QuestionFields.MOTOR_SKILLS,
            QuestionFields.LANGUAGE_SKILLS,
            QuestionFields.SOCIAL_SKILLS
        ],
        AgentTypes.MENTAL_HEALTH: [
            QuestionFields.PARENT_CONCERNS,
            QuestionFields.SUPPORT_SYSTEM,
            QuestionFields.WORK_SCHEDULE,
            QuestionFields.SLEEP_PATTERN
        ]
    }
    
    QUESTIONS = {
        # Generic questions
        QuestionFields.BABY_AGE: "How old is your baby?",
        QuestionFields.BABY_WEIGHT: "What is your baby's current weight?",
        QuestionFields.CONCERNS: "What specific concerns do you have?",
        
        # Sleep related questions
        QuestionFields.CURRENT_SLEEP_HOURS: "How many hours is your baby currently sleeping in total?",
        QuestionFields.SLEEP_PATTERN: "What is your baby's current sleep schedule like?",
        QuestionFields.NIGHT_WAKINGS: "How often does your baby wake up during the night?",
        QuestionFields.NAP_SCHEDULE: "What is your baby's current nap schedule?",
        
        # Feeding related questions
        QuestionFields.FEEDING_TYPE: "How are you currently feeding your baby (breast, bottle, solids)?",
        QuestionFields.FEEDING_FREQUENCY: "How often do you feed your baby?",
        QuestionFields.FEEDING_AMOUNT: "How much does your baby typically eat per feeding?",
        
        # Health related questions
        QuestionFields.SYMPTOMS: "What symptoms has your baby been experiencing?",
        QuestionFields.TEMPERATURE: "Does your baby have a fever? What is their temperature?",
        QuestionFields.MEDICATIONS: "Is your baby currently taking any medications?",
        
        # Development related questions
        QuestionFields.MILESTONES: "What milestones has your baby reached so far?",
        QuestionFields.MOTOR_SKILLS: "What physical activities can your baby do?",
        QuestionFields.LANGUAGE_SKILLS: "How does your baby communicate currently?",
        
        # Parent related questions
        QuestionFields.PARENT_CONCERNS: "What are your main concerns or challenges?",
        QuestionFields.SUPPORT_SYSTEM: "What support system do you have available?",
        QuestionFields.WORK_SCHEDULE: "What is your typical daily schedule like?",
        
        # Environment questions
        QuestionFields.HOME_ENVIRONMENT: "Can you describe your home environment?",
        QuestionFields.SIBLINGS: "Does your baby have any siblings?",
        QuestionFields.CLIMATE: "What's the typical climate where you live?"
    }
    
    MAX_FOLLOWUP_QUESTIONS = 5  # Increased from 3 to allow for more complex topics

class DynamicFieldDetector:
    """Dynamic approach to field detection using semantic similarity"""
    
    # Core concepts that help identify field types
    TEMPORAL_INDICATORS = {
        'when', 'how often', 'frequency', 'daily', 'weekly', 'monthly',
        'schedule', 'routine', 'pattern', 'timing', 'during', 'night',
        'morning', 'evening', 'afternoon', 'between', 'hours'
    }
    
    QUANTITY_INDICATORS = {
        'how much', 'how many', 'amount', 'number', 'quantity',
        'size', 'volume', 'duration', 'weight', 'height', 'long',
        'frequently', 'times', 'ounces', 'ml', 'grams', 'pounds'
    }
    
    PREFERENCE_INDICATORS = {
        'prefer', 'like', 'want', 'need', 'looking for',
        'interested in', 'would rather', 'favorite', 'best',
        'recommend', 'suggest', 'better', 'ideal', 'suitable'
    }
    
    CONCERN_INDICATORS = {
        'worried', 'concerned', 'issue', 'problem', 'trouble',
        'difficulty', 'challenge', 'risk', 'afraid', 'anxious',
        'scared', 'unsure', 'help', 'advice', 'normal', 'wrong'
    }
    
    HEALTH_INDICATORS = {
        'sick', 'fever', 'temperature', 'symptoms', 'pain',
        'doctor', 'medicine', 'medication', 'allergy', 'allergic',
        'rash', 'cough', 'cold', 'flu', 'vaccine', 'shot'
    }
    
    DEVELOPMENT_INDICATORS = {
        'milestone', 'development', 'grow', 'skill', 'learn',
        'crawl', 'walk', 'talk', 'roll', 'sit', 'stand',
        'play', 'social', 'interact', 'respond', 'understand'
    }
    
    FEEDING_INDICATORS = {
        'feed', 'eat', 'food', 'milk', 'formula', 'breast',
        'bottle', 'solid', 'puree', 'hungry', 'appetite',
        'nutrition', 'diet', 'meal', 'snack', 'drink'
    }
    
    SLEEP_INDICATORS = {
        'sleep', 'nap', 'bedtime', 'night', 'wake', 'tired',
        'drowsy', 'routine', 'schedule', 'rest', 'dream',
        'cry', 'comfort', 'soothe', 'pacifier', 'swaddle'
    }
    
    ENVIRONMENT_INDICATORS = {
        'room', 'house', 'apartment', 'space', 'temperature',
        'noise', 'light', 'dark', 'quiet', 'loud', 'weather',
        'climate', 'outdoor', 'indoor', 'travel', 'car'
    }
    
    SOCIAL_INDICATORS = {
        'family', 'parent', 'mother', 'father', 'sibling',
        'daycare', 'babysitter', 'nanny', 'friend', 'support',
        'community', 'group', 'class', 'activity', 'play'
    }
    
    @staticmethod
    def extract_field_type(query: str) -> str:
        """
        Dynamically determine the type of field being discussed.
        Returns a tuple of (field_type, confidence_score)
        """
        query_lower = query.lower()
        
        # Define field type detection with confidence scores
        field_detectors = {
            'temporal': (DynamicFieldDetector.TEMPORAL_INDICATORS, 0.8),
            'quantity': (DynamicFieldDetector.QUANTITY_INDICATORS, 0.7),
            'preference': (DynamicFieldDetector.PREFERENCE_INDICATORS, 0.6),
            'concern': (DynamicFieldDetector.CONCERN_INDICATORS, 0.8),
            'health': (DynamicFieldDetector.HEALTH_INDICATORS, 0.9),
            'development': (DynamicFieldDetector.DEVELOPMENT_INDICATORS, 0.8),
            'feeding': (DynamicFieldDetector.FEEDING_INDICATORS, 0.8),
            'sleep': (DynamicFieldDetector.SLEEP_INDICATORS, 0.8),
            'environment': (DynamicFieldDetector.ENVIRONMENT_INDICATORS, 0.7),
            'social': (DynamicFieldDetector.SOCIAL_INDICATORS, 0.7)
        }
        
        # Calculate matches for each field type
        matches = {}
        for field_type, (indicators, base_confidence) in field_detectors.items():
            match_count = sum(1 for indicator in indicators if indicator in query_lower)
            if match_count > 0:
                # Calculate confidence based on number of matches and base confidence
                confidence = min(base_confidence * (1 + 0.2 * match_count), 1.0)
                matches[field_type] = confidence
        
        if not matches:
            return 'general'
            
        # Return the field type with highest confidence
        return max(matches.items(), key=lambda x: x[1])[0]
        
    @staticmethod
    def get_required_fields(field_type: str) -> List[str]:
        """Get the required fields for a given field type"""
        field_requirements = {
            'temporal': [QuestionFields.TIMING, QuestionFields.FREQUENCY],
            'quantity': [QuestionFields.BABY_AGE, QuestionFields.BABY_WEIGHT],
            'health': [QuestionFields.SYMPTOMS, QuestionFields.TEMPERATURE],
            'development': [QuestionFields.BABY_AGE, QuestionFields.MILESTONES],
            'feeding': [QuestionFields.FEEDING_TYPE, QuestionFields.FEEDING_FREQUENCY],
            'sleep': [QuestionFields.SLEEP_PATTERN, QuestionFields.NIGHT_WAKINGS],
            'environment': [QuestionFields.HOME_ENVIRONMENT, QuestionFields.CLIMATE],
            'social': [QuestionFields.SIBLINGS, QuestionFields.SUPPORT_SYSTEM]
        }
        return field_requirements.get(field_type, [QuestionFields.BABY_AGE, QuestionFields.CONCERNS])

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