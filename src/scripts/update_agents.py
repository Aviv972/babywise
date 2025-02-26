import os
import re
from typing import Dict, List
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

AGENT_TEMPLATE = '''from typing import Dict, List, Any, Optional
from src.agents.base_agent import BaseAgent
from src.constants import ResponseTypes, AgentTypes
from langchain_core.prompts import ChatPromptTemplate

class {agent_class_name}(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.{agent_type}
        self.name = "{agent_name}"
        
        # Define expertise
        self.expertise = {expertise}
        
        self.required_context = {required_context}
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """{system_prompt}"""),
            ("human", """{human_prompt}""")
        ])

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process {domain}-related queries using LangChain"""
        try:
            # Extract context information
            gathered_info = context.get('gathered_info', {})
            
            # Format prompt variables
            prompt_vars = {prompt_vars}
            
            # Process through LangGraph
            result = await self.graph.process_message(
                thread_id=context.get('thread_id', 'default'),
                user_input=self.prompt_template.format(**prompt_vars)
            )
            
            # Get updated context
            updated_context = await self.memory.get_context(
                thread_id=context.get('thread_id', 'default')
            )
            
            {additional_processing}
            
            return {
                'type': ResponseTypes.ANSWER,
                'text': result,
                'context': updated_context
            }
            
        except Exception as e:
            print(f"Error in {domain} agent processing: {{str(e)}}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "{error_message}"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is {domain}-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = {primary_terms}
        
        if any(term in query_lower for term in primary_terms):
            print("Found {domain}-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = {secondary_terms}
        
        if any(term in query_lower for term in secondary_terms):
            print("Found {domain}-related terms")
            return 0.7
            
        return 0.0  # Not {domain}-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for {domain} advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        {missing_fields_logic}
        
        return missing
'''

# Agent-specific configurations
AGENT_CONFIGS = {
    'sleep_routine_agent': {
        'class_name': 'SleepRoutineAgent',
        'agent_type': 'SLEEP_ROUTINE',
        'agent_name': 'Sleep Routine Expert',
        'expertise': [
            "sleep", "routine", "schedule", "nap",
            "bedtime", "night", "wake", "שינה",
            "לילה", "שעות שינה", "הרדמה"
        ],
        'required_context': ["baby_age", "current_schedule"],
        'system_prompt': """You are a sleep routine expert specializing in baby sleep patterns.
            Consider these key aspects:
            1. Age-appropriate sleep needs
            2. Circadian rhythm development
            3. Sleep environment and safety
            4. Routine consistency
            Always emphasize safe sleep practices and age-appropriate recommendations.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Current Schedule: {current_schedule}
            Additional Context: {context}
            
            Please provide a comprehensive response that:
            1. Addresses the specific sleep concern
            2. Provides age-appropriate recommendations
            3. Suggests practical implementation steps
            4. Includes safety considerations
            5. Acknowledges common challenges""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'current_schedule': 'gathered_info.get("current_schedule", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add safety reminder for sleep-related advice\nsafety_reminder = "\\n\\nRemember: Always follow safe sleep guidelines - place baby on their back in a clear crib or bassinet."\nresult = f"{result}{safety_reminder}"',
        'error_message': "I'm having trouble processing your sleep-related question. Could you please provide your baby's age and current sleep schedule?",
        'primary_terms': [
            "sleep", "nap", "bedtime", "night", "routine",
            "שינה", "לילה", "שעות שינה", "הרדמה"
        ],
        'secondary_terms': [
            "tired", "wake", "schedule", "cry", "fussy",
            "עייף", "ער", "בוכה", "סדר יום"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')  # Age is critical for sleep recommendations
            return missing  # Get age first before asking other questions
            
        if 'current_schedule' not in gathered_info:
            missing.append('current_schedule')'''
    },
    'baby_gear_agent': {
        'class_name': 'BabyGearAgent',
        'agent_type': 'BABY_GEAR',
        'agent_name': 'Baby Gear Expert',
        'expertise': [
            "stroller", "car seat", "crib", "carrier",
            "high chair", "playpen", "monitor", "breast pump",
            "עגלה", "כיסא בטיחות", "מיטת תינוק", "מנשא"
        ],
        'required_context': ["budget", "preferences"],
        'system_prompt': """You are a baby gear expert specializing in product recommendations.
            Consider these key aspects:
            1. Safety standards and certifications
            2. Age-appropriate features
            3. Value for money and durability
            4. Practical usability
            Always prioritize safety and provide current market options.""",
        'human_prompt': """Query: {query}
            Budget: {budget}
            Preferences: {preferences}
            Usage: {usage}
            Additional Context: {context}
            
            Please provide:
            1. 2-3 specific product recommendations within budget
            2. Key features and benefits
            3. Current price points
            4. Where to buy
            5. Important safety considerations""",
        'prompt_vars': {
            'query': 'query',
            'budget': 'gathered_info.get("budget", "Not specified")',
            'preferences': 'gathered_info.get("preferences", [])',
            'usage': 'gathered_info.get("usage", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '',
        'error_message': "I'm having trouble processing your request. Could you please specify your budget and any specific features you're looking for?",
        'primary_terms': [
            "stroller", "car seat", "crib", "carrier",
            "עגלה", "כיסא בטיחות", "מיטת תינוק", "מנשא"
        ],
        'secondary_terms': [
            "gear", "equipment", "product", "buy", "purchase",
            "ציוד", "מוצר", "לקנות", "רכישה"
        ],
        'missing_fields_logic': '''if 'budget' not in gathered_info:
            missing.append('budget')
            return missing  # Get budget first
            
        if 'preferences' not in gathered_info:
            missing.append('preferences')'''
    },
    'feeding_agent': {
        'class_name': 'FeedingAgent',
        'agent_type': 'FEEDING',
        'agent_name': 'Feeding Expert',
        'expertise': [
            "feeding", "breastfeeding", "bottle", "formula",
            "solids", "weaning", "nutrition", "schedule",
            "האכלה", "הנקה", "בקבוק", "תמ״ל", "מזון"
        ],
        'required_context': ["baby_age", "feeding_type", "current_schedule"],
        'system_prompt': """You are a feeding expert specializing in infant nutrition.
            Consider these key aspects:
            1. Age-appropriate feeding methods
            2. Nutritional requirements
            3. Safe feeding practices
            4. Common challenges
            Always emphasize safety and consult healthcare providers for medical concerns.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Feeding Type: {feeding_type}
            Current Schedule: {current_schedule}
            Additional Context: {context}
            
            Please provide:
            1. Age-appropriate recommendations
            2. Safe feeding guidelines
            3. Practical implementation steps
            4. Common challenges and solutions
            5. When to seek professional help""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'feeding_type': 'gathered_info.get("feeding_type", "Not specified")',
            'current_schedule': 'gathered_info.get("current_schedule", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add feeding safety reminder\nsafety_reminder = "\\n\\nRemember: Always supervise feeding and follow safe preparation guidelines for formula or expressed milk."\nresult = f"{result}{safety_reminder}"',
        'error_message': "I'm having trouble processing your feeding-related question. Could you please provide your baby's age and current feeding method?",
        'primary_terms': [
            "feed", "breast", "bottle", "formula", "solid",
            "האכלה", "הנקה", "בקבוק", "תמ״ל", "מזון"
        ],
        'secondary_terms': [
            "milk", "hunger", "schedule", "wean", "nutrition",
            "חלב", "רעב", "גמילה", "תזונה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'feeding_type' not in gathered_info:
            missing.append('feeding_type')
            return missing  # Get feeding type next
            
        if 'current_schedule' not in gathered_info:
            missing.append('current_schedule')'''
    },
    'mental_health_agent': {
        'class_name': 'MentalHealthAgent',
        'agent_type': 'MENTAL_HEALTH',
        'agent_name': 'Mental Health Expert',
        'expertise': [
            "anxiety", "depression", "stress", "emotions",
            "postpartum", "mental health", "mood", "support",
            "חרדה", "דיכאון", "לחץ", "רגשות", "תמיכה"
        ],
        'required_context': ["symptoms", "duration", "support_system"],
        'system_prompt': """You are a mental health expert specializing in parental mental health.
            Consider these key aspects:
            1. Common parental mental health challenges
            2. Support strategies and coping mechanisms
            3. Warning signs and red flags
            4. Available resources and support systems
            Always emphasize seeking professional help when needed.""",
        'human_prompt': """Query: {query}
            Symptoms: {symptoms}
            Duration: {duration}
            Support System: {support_system}
            Additional Context: {context}
            
            Please provide:
            1. Supportive and empathetic response
            2. Practical coping strategies
            3. Self-care recommendations
            4. Available support resources
            5. When to seek professional help""",
        'prompt_vars': {
            'query': 'query',
            'symptoms': 'gathered_info.get("symptoms", "Not specified")',
            'duration': 'gathered_info.get("duration", "Not specified")',
            'support_system': 'gathered_info.get("support_system", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add mental health disclaimer\ndisclaimer = "\\n\\nRemember: This advice is for informational purposes only. If you\'re experiencing severe symptoms or having thoughts of self-harm, please contact a mental health professional or emergency services immediately."\nresult = f"{result}{disclaimer}"',
        'error_message': "I'm having trouble understanding your situation. Could you please describe what you're experiencing and how long it's been going on?",
        'primary_terms': [
            "anxiety", "depression", "stress", "mood",
            "חרדה", "דיכאון", "לחץ", "מצב רוח"
        ],
        'secondary_terms': [
            "worry", "sad", "overwhelm", "cope", "support",
            "דאגה", "עצוב", "להתמודד", "תמיכה"
        ],
        'missing_fields_logic': '''if 'symptoms' not in gathered_info:
            missing.append('symptoms')
            return missing  # Get symptoms first
            
        if 'duration' not in gathered_info:
            missing.append('duration')'''
    },
    'general_agent': {
        'class_name': 'GeneralAgent',
        'agent_type': 'GENERAL',
        'agent_name': 'General Parenting Expert',
        'expertise': [
            "parenting", "development", "behavior", "routine",
            "milestones", "activities", "discipline", "education",
            "הורות", "התפתחות", "התנהגות", "חינוך"
        ],
        'required_context': ["baby_age", "situation"],
        'system_prompt': """You are a general parenting expert.
            Consider these key aspects:
            1. Age-appropriate guidance
            2. Child development principles
            3. Positive parenting strategies
            4. Family dynamics
            Always provide evidence-based advice while being supportive.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Situation: {situation}
            Additional Context: {context}
            
            Please provide:
            1. Age-appropriate advice
            2. Practical strategies
            3. Common challenges and solutions
            4. Developmental considerations
            5. Additional resources if needed""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'situation': 'gathered_info.get("situation", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '',
        'error_message': "I'm having trouble providing specific advice. Could you please tell me your baby's age and describe the situation?",
        'primary_terms': [
            "parent", "child", "baby", "toddler",
            "הורה", "ילד", "תינוק", "פעוט"
        ],
        'secondary_terms': [
            "advice", "help", "question", "how to",
            "עצה", "עזרה", "שאלה", "איך"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'situation' not in gathered_info:
            missing.append('situation')'''
    },
    'breastfeeding_agent': {
        'class_name': 'BreastfeedingAgent',
        'agent_type': 'BREASTFEEDING',
        'agent_name': 'Breastfeeding Expert',
        'expertise': [
            "breastfeeding", "nursing", "lactation", "milk supply",
            "pumping", "latching", "feeding positions",
            "הנקה", "חלב אם", "שאיבה", "אחיזה"
        ],
        'required_context': ["baby_age", "feeding_concern"],
        'system_prompt': """You are a breastfeeding expert.
            Consider these key aspects:
            1. Proper latch and positioning
            2. Milk supply management
            3. Common challenges and solutions
            4. Pumping and storage guidelines
            Always emphasize seeking professional help when needed.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Feeding Concern: {feeding_concern}
            Additional Context: {context}
            
            Please provide:
            1. Specific guidance for the concern
            2. Practical tips and techniques
            3. Signs of success/improvement
            4. Common challenges and solutions
            5. When to seek professional help""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'feeding_concern': 'gathered_info.get("feeding_concern", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add breastfeeding disclaimer\ndisclaimer = "\\n\\nRemember: While this advice is based on common experiences, every mother and baby pair is unique. If you\'re experiencing persistent difficulties, please consult with a lactation consultant or healthcare provider."\nresult = f"{result}{disclaimer}"',
        'error_message': "I'm having trouble providing specific breastfeeding advice. Could you please tell me your baby's age and describe your specific concern?",
        'primary_terms': [
            "breastfeed", "nurse", "latch", "milk",
            "הנקה", "חלב", "אחיזה", "שד"
        ],
        'secondary_terms': [
            "pump", "supply", "position", "pain",
            "שאיבה", "אספקה", "תנוחה", "כאב"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'feeding_concern' not in gathered_info:
            missing.append('feeding_concern')'''
    },
    'emergency_agent': {
        'class_name': 'EmergencyAgent',
        'agent_type': 'EMERGENCY',
        'agent_name': 'Emergency Response Expert',
        'expertise': [
            "emergency", "first aid", "urgent care", "safety",
            "injury", "accident", "medical", "choking",
            "חירום", "עזרה ראשונה", "פציעה", "חנק"
        ],
        'required_context': ["emergency_type", "baby_age"],
        'system_prompt': """You are an emergency response expert.
            Consider these key aspects:
            1. Immediate safety measures
            2. Emergency response steps
            3. When to call emergency services
            4. Prevention guidelines
            Always prioritize safety and emergency services when needed.""",
        'human_prompt': """Query: {query}
            Emergency Type: {emergency_type}
            Baby's Age: {baby_age}
            Additional Context: {context}
            
            Provide IMMEDIATE guidance:
            1. Immediate safety steps
            2. Emergency response actions
            3. When to call emergency services
            4. What NOT to do
            5. Follow-up care needed""",
        'prompt_vars': {
            'query': 'query',
            'emergency_type': 'gathered_info.get("emergency_type", "Not specified")',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add emergency disclaimer\ndisclaimer = "\\n\\n⚠️ IMPORTANT: This is general guidance only. In any emergency situation, call emergency services (911) immediately. Do not delay seeking professional medical help."\nresult = f"{result}{disclaimer}"',
        'error_message': "This sounds like an emergency situation. Please call emergency services (911) immediately if you haven't already.",
        'primary_terms': [
            "emergency", "urgent", "help", "911",
            "חירום", "דחוף", "עזרה", "100"
        ],
        'secondary_terms': [
            "hurt", "injury", "accident", "pain",
            "פציעה", "תאונה", "כאב", "נפילה"
        ],
        'missing_fields_logic': '''if 'emergency_type' not in gathered_info:
            missing.append('emergency_type')
            return missing  # Get emergency type first
            
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')'''
    },
    'sleep_training_agent': {
        'class_name': 'SleepTrainingAgent',
        'agent_type': 'SLEEP_TRAINING',
        'agent_name': 'Sleep Training Expert',
        'expertise': [
            "sleep training", "self soothing", "bedtime routine",
            "night wakings", "sleep regression", "nap transition",
            "אימון שינה", "הרדמה עצמית", "שגרת שינה", "רגרסיית שינה"
        ],
        'required_context': ["baby_age", "current_sleep_pattern", "training_method"],
        'system_prompt': """You are a sleep training expert specializing in gentle, evidence-based methods.
            Consider these key aspects:
            1. Age-appropriate sleep training methods
            2. Family sleep goals and preferences
            3. Consistent routines and schedules
            4. Emotional well-being of baby and parents
            Always emphasize safety and parental comfort with chosen methods.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Current Sleep Pattern: {current_sleep_pattern}
            Training Method: {training_method}
            Additional Context: {context}
            
            Please provide:
            1. Method-specific guidance
            2. Step-by-step implementation plan
            3. Expected timeline and milestones
            4. Common challenges and solutions
            5. Signs of progress/success""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'current_sleep_pattern': 'gathered_info.get("current_sleep_pattern", "Not specified")',
            'training_method': 'gathered_info.get("training_method", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add sleep training disclaimer\ndisclaimer = "\\n\\nRemember: Every baby is unique, and what works for one may not work for another. Always follow safe sleep guidelines and adjust methods based on your baby\'s needs and your comfort level."\nresult = f"{result}{disclaimer}"',
        'error_message': "I need more information to provide appropriate sleep training advice. Could you tell me your baby's age and current sleep patterns?",
        'primary_terms': [
            "sleep train", "self sooth", "cry", "bedtime",
            "אימון שינה", "הרדמה", "בכי", "שינה"
        ],
        'secondary_terms': [
            "routine", "schedule", "method", "night",
            "שגרה", "לוח זמנים", "שיטה", "לילה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'current_sleep_pattern' not in gathered_info:
            missing.append('current_sleep_pattern')
            return missing  # Get sleep pattern next
            
        if 'training_method' not in gathered_info:
            missing.append('training_method')'''
    },
    'medical_health_agent': {
        'class_name': 'MedicalHealthAgent',
        'agent_type': 'MEDICAL_HEALTH',
        'agent_name': 'Medical Health Expert',
        'expertise': [
            "health", "illness", "symptoms", "medication",
            "fever", "rash", "cough", "allergies",
            "בריאות", "מחלה", "תסמינים", "תרופות", "חום"
        ],
        'required_context': ["baby_age", "symptoms", "duration"],
        'system_prompt': """You are a medical information provider.
            Consider these key aspects:
            1. Common childhood conditions
            2. Warning signs and red flags
            3. Home care guidelines
            4. Prevention measures
            Always emphasize consulting healthcare providers for medical advice.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Symptoms: {symptoms}
            Duration: {duration}
            Additional Context: {context}
            
            Please provide:
            1. General information about the condition
            2. Home care guidelines
            3. Prevention measures
            4. When to seek medical attention
            5. Questions to ask healthcare provider""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'symptoms': 'gathered_info.get("symptoms", "Not specified")',
            'duration': 'gathered_info.get("duration", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add medical disclaimer\ndisclaimer = "\\n\\n⚠️ IMPORTANT: This information is for educational purposes only and should not replace professional medical advice. Always consult with your healthcare provider for diagnosis and treatment."\nresult = f"{result}{disclaimer}"',
        'error_message': "To provide appropriate health information, I need to know your baby's age and the symptoms you're concerned about.",
        'primary_terms': [
            "sick", "health", "doctor", "medicine",
            "חולה", "בריאות", "רופא", "תרופה"
        ],
        'secondary_terms': [
            "fever", "cough", "rash", "symptoms",
            "חום", "שיעול", "פריחה", "תסמינים"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'symptoms' not in gathered_info:
            missing.append('symptoms')
            return missing  # Get symptoms next
            
        if 'duration' not in gathered_info:
            missing.append('duration')'''
    },
    'development_agent': {
        'class_name': 'DevelopmentAgent',
        'agent_type': 'DEVELOPMENT',
        'agent_name': 'Development Expert',
        'expertise': [
            "development", "milestones", "growth", "skills",
            "motor", "cognitive", "social", "language",
            "התפתחות", "אבני דרך", "גדילה", "כישורים"
        ],
        'required_context': ["baby_age", "development_area", "current_skills"],
        'system_prompt': """You are a child development expert.
            Consider these key aspects:
            1. Age-appropriate milestones
            2. Developmental domains
            3. Individual variations
            4. Supportive activities
            Always emphasize normal developmental ranges and variations.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Development Area: {development_area}
            Current Skills: {current_skills}
            Additional Context: {context}
            
            Please provide:
            1. Age-appropriate expectations
            2. Development-promoting activities
            3. Next milestones to watch for
            4. Red flags to monitor
            5. Ways to support development""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'development_area': 'gathered_info.get("development_area", "Not specified")',
            'current_skills': 'gathered_info.get("current_skills", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add development disclaimer\ndisclaimer = "\\n\\nRemember: Every child develops at their own pace. If you have concerns about your child\'s development, consult with your healthcare provider."\nresult = f"{result}{disclaimer}"',
        'error_message': "To provide appropriate developmental guidance, I need to know your baby's age and which area of development you're interested in.",
        'primary_terms': [
            "development", "milestone", "skill", "growth",
            "התפתחות", "אבן דרך", "כישור", "גדילה"
        ],
        'secondary_terms': [
            "motor", "cognitive", "social", "language",
            "מוטורי", "קוגניטיבי", "חברתי", "שפה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'development_area' not in gathered_info:
            missing.append('development_area')
            return missing  # Get development area next
            
        if 'current_skills' not in gathered_info:
            missing.append('current_skills')'''
    },
    'safety_agent': {
        'class_name': 'SafetyAgent',
        'agent_type': 'SAFETY',
        'agent_name': 'Safety Expert',
        'expertise': [
            "safety", "childproofing", "prevention", "risks",
            "home safety", "car safety", "first aid", "emergency",
            "בטיחות", "מניעה", "סכנות", "עזרה ראשונה"
        ],
        'required_context': ["baby_age", "environment", "specific_concern"],
        'system_prompt': """You are a child safety expert.
            Consider these key aspects:
            1. Age-specific safety risks
            2. Prevention strategies
            3. Environmental modifications
            4. Emergency preparedness
            Always prioritize prevention and emergency readiness.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Environment: {environment}
            Specific Concern: {specific_concern}
            Additional Context: {context}
            
            Please provide:
            1. Safety assessment
            2. Prevention strategies
            3. Required safety measures
            4. Emergency procedures
            5. Additional precautions""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'environment': 'gathered_info.get("environment", "Not specified")',
            'specific_concern': 'gathered_info.get("specific_concern", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add safety disclaimer\ndisclaimer = "\\n\\n⚠️ IMPORTANT: This safety information is general guidance. Always follow product safety instructions and local safety regulations. In emergencies, call emergency services immediately."\nresult = f"{result}{disclaimer}"',
        'error_message': "To provide appropriate safety guidance, I need to know your baby's age and the specific environment or safety concern you're asking about.",
        'primary_terms': [
            "safety", "danger", "risk", "prevent",
            "בטיחות", "סכנה", "סיכון", "מניעה"
        ],
        'secondary_terms': [
            "protect", "secure", "childproof", "safe",
            "הגנה", "אבטחה", "מוגן", "בטוח"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'environment' not in gathered_info:
            missing.append('environment')
            return missing  # Get environment next
            
        if 'specific_concern' not in gathered_info:
            missing.append('specific_concern')'''
    },
    'nutrition_agent': {
        'class_name': 'NutritionAgent',
        'agent_type': 'NUTRITION',
        'agent_name': 'Nutrition Expert',
        'expertise': [
            "nutrition", "food", "diet", "feeding", "solids",
            "allergies", "meal planning", "snacks",
            "תזונה", "אוכל", "דיאטה", "האכלה", "מוצקים"
        ],
        'required_context': ["baby_age", "feeding_stage", "dietary_restrictions"],
        'system_prompt': """You are a pediatric nutrition expert.
            Consider these key aspects:
            1. Age-appropriate nutrition needs
            2. Safe food introduction
            3. Balanced diet planning
            4. Allergy awareness
            Always emphasize food safety and age-appropriate guidelines.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Feeding Stage: {feeding_stage}
            Dietary Restrictions: {dietary_restrictions}
            Additional Context: {context}
            
            Please provide:
            1. Age-appropriate nutrition guidance
            2. Food safety guidelines
            3. Meal/snack suggestions
            4. Portion size guidance
            5. Warning signs to watch for""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'feeding_stage': 'gathered_info.get("feeding_stage", "Not specified")',
            'dietary_restrictions': 'gathered_info.get("dietary_restrictions", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add nutrition disclaimer\ndisclaimer = "\\n\\nRemember: Always introduce new foods one at a time and watch for allergic reactions. Consult with your pediatrician about your baby\'s specific nutritional needs."\nresult = f"{result}{disclaimer}"',
        'error_message': "To provide appropriate nutrition advice, I need to know your baby's age and current feeding stage.",
        'primary_terms': [
            "food", "eat", "nutrition", "diet",
            "אוכל", "תזונה", "דיאטה", "מזון"
        ],
        'secondary_terms': [
            "meal", "snack", "solid", "allergy",
            "ארוחה", "חטיף", "מוצקים", "אלרגיה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'feeding_stage' not in gathered_info:
            missing.append('feeding_stage')
            return missing  # Get feeding stage next
            
        if 'dietary_restrictions' not in gathered_info:
            missing.append('dietary_restrictions')'''
    },
    'milestone_agent': {
        'class_name': 'MilestoneAgent',
        'agent_type': 'MILESTONE',
        'agent_name': 'Milestone Expert',
        'expertise': [
            "milestones", "development", "skills", "progress",
            "physical", "cognitive", "social", "emotional",
            "אבני דרך", "התפתחות", "כישורים", "התקדמות"
        ],
        'required_context': ["baby_age", "milestone_area", "current_abilities"],
        'system_prompt': """You are a developmental milestone expert.
            Consider these key aspects:
            1. Age-specific milestones
            2. Individual development patterns
            3. Supportive activities
            4. Progress monitoring
            Always emphasize the range of normal development.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Milestone Area: {milestone_area}
            Current Abilities: {current_abilities}
            Additional Context: {context}
            
            Please provide:
            1. Expected milestones for age
            2. Development-supporting activities
            3. Progress indicators
            4. Red flags to watch for
            5. Next milestones to expect""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'milestone_area': 'gathered_info.get("milestone_area", "Not specified")',
            'current_abilities': 'gathered_info.get("current_abilities", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add milestone disclaimer\ndisclaimer = "\\n\\nRemember: Every child develops at their own pace. This is a general guide, not a strict timeline. If you have concerns about your child\'s development, consult with your healthcare provider."\nresult = f"{result}{disclaimer}"',
        'error_message': "To provide appropriate milestone guidance, I need to know your baby's age and which area of development you're asking about.",
        'primary_terms': [
            "milestone", "development", "skill", "ability",
            "אבן דרך", "התפתחות", "כישור", "יכולת"
        ],
        'secondary_terms': [
            "progress", "achieve", "learn", "master",
            "התקדמות", "הישג", "למידה", "שליטה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'milestone_area' not in gathered_info:
            missing.append('milestone_area')
            return missing  # Get milestone area next
            
        if 'current_abilities' not in gathered_info:
            missing.append('current_abilities')'''
    },
    'travel_agent': {
        'class_name': 'TravelAgent',
        'agent_type': 'TRAVEL',
        'agent_name': 'Baby Travel Expert',
        'expertise': [
            "travel", "flight", "vacation", "trip", "journey",
            "packing", "car", "plane", "hotel", "accommodation",
            "טיול", "טיסה", "חופשה", "נסיעה", "מזוודה", "מלון"
        ],
        'required_context': ["baby_age", "travel_type", "destination", "duration"],
        'system_prompt': """You are a baby travel expert specializing in family travel advice.
            Consider these key aspects:
            1. Age-appropriate travel planning
            2. Safety during travel
            3. Essential packing lists
            4. Travel logistics with babies
            5. Accommodation requirements
            Always prioritize baby's comfort and safety while making travel manageable for parents.""",
        'human_prompt': """Query: {query}
            Baby's Age: {baby_age}
            Travel Type: {travel_type}
            Destination: {destination}
            Duration: {duration}
            Additional Context: {context}
            
            Please provide:
            1. Travel preparation advice
            2. Essential packing list
            3. Safety considerations
            4. Travel schedule recommendations
            5. Accommodation tips
            6. Location-specific guidance""",
        'prompt_vars': {
            'query': 'query',
            'baby_age': 'gathered_info.get("baby_age", "Not specified")',
            'travel_type': 'gathered_info.get("travel_type", "Not specified")',
            'destination': 'gathered_info.get("destination", "Not specified")',
            'duration': 'gathered_info.get("duration", "Not specified")',
            'context': 'self._format_context(gathered_info)'
        },
        'additional_processing': '# Add travel safety reminder\nsafety_reminder = "\\n\\nRemember: Always check with your pediatrician before long-distance travel, and ensure you have necessary medical information and supplies readily available."\nresult = f"{result}{safety_reminder}"',
        'error_message': "I need more information about your travel plans. Could you please tell me your baby's age and where you're planning to travel?",
        'primary_terms': [
            "travel", "flight", "trip", "vacation", "journey",
            "טיול", "טיסה", "חופשה", "נסיעה"
        ],
        'secondary_terms': [
            "pack", "hotel", "car", "plane", "accommodation",
            "לארוז", "מלון", "רכב", "מטוס", "לינה"
        ],
        'missing_fields_logic': '''if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'travel_type' not in gathered_info:
            missing.append('travel_type')
            return missing  # Get travel type next
            
        if 'destination' not in gathered_info:
            missing.append('destination')
            
        if 'duration' not in gathered_info:
            missing.append('duration')'''
    }
}

def update_agent(agent_file: str, config: Dict) -> None:
    """Update an agent file with the new LangChain structure"""
    print(f"\nUpdating {agent_file}...")
    
    try:
        # Read the current file to extract any custom methods
        with open(agent_file, 'r') as f:
            current_content = f.read()
            print(f"Successfully read {agent_file}")
        
        # Extract any custom methods (those not in the template)
        custom_methods = re.findall(r'    def ([^_]\w+.*?):\n.*?(?=\n    def|\Z)', current_content, re.DOTALL)
        print(f"Found {len(custom_methods)} custom methods")
        
        # Format the template with the configuration
        domain = config['agent_type'].lower()
        
        # Create the content directly
        new_content = f'''from typing import Dict, List, Any, Optional
from src.agents.base_agent import BaseAgent
from src.constants import ResponseTypes, AgentTypes
from langchain_core.prompts import ChatPromptTemplate

class {config['class_name']}(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.{config['agent_type']}
        self.name = "{config['agent_name']}"
        
        # Define expertise
        self.expertise = {config['expertise']}
        
        self.required_context = {config['required_context']}
        
        # Define LangChain prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """{config['system_prompt']}"""),
            ("human", """{config['human_prompt']}""")
        ])

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process {domain}-related queries using LangChain"""
        try:
            # Extract context information
            gathered_info = context.get('gathered_info', {{}})
            
            # Format prompt variables
            prompt_vars = {config['prompt_vars']}
            
            # Process through LangGraph
            result = await self.graph.process_message(
                thread_id=context.get('thread_id', 'default'),
                user_input=self.prompt_template.format(**prompt_vars)
            )
            
            # Get updated context
            updated_context = await self.memory.get_context(
                thread_id=context.get('thread_id', 'default')
            )
            
            {config['additional_processing']}
            
            return {{
                'type': ResponseTypes.ANSWER,
                'text': result,
                'context': updated_context
            }}
            
        except Exception as e:
            print(f"Error in {domain} agent processing: {{str(e)}}")
            return {{
                'type': ResponseTypes.ERROR,
                'text': "{config['error_message']}"
            }}

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is {domain}-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = {config['primary_terms']}
        
        if any(term in query_lower for term in primary_terms):
            print("Found {domain}-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = {config['secondary_terms']}
        
        if any(term in query_lower for term in secondary_terms):
            print("Found {domain}-related terms")
            return 0.7
            
        return 0.0  # Not {domain}-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for {domain} advice"""
        gathered_info = context.get('gathered_info', {{}})
        missing = []
        
        {config['missing_fields_logic']}
        
        return missing
'''
        
        # Add any custom methods back
        if custom_methods:
            for method in custom_methods:
                method_match = re.search(f'    def {method}.*?(?=\n    def|\Z)', current_content, re.DOTALL)
                if method_match and method_match.group(0) not in new_content:
                    new_content += f"\n{method_match.group(0)}\n"
        
        # Write the updated content
        with open(agent_file, 'w') as f:
            f.write(new_content)
            print(f"Successfully updated {agent_file}")
            
    except Exception as e:
        print(f"Error updating {agent_file}: {str(e)}")

def main():
    """Update all agents in the src/agents directory"""
    agents_dir = os.path.join(project_root, 'src', 'agents')
    print(f"Looking for agents in: {agents_dir}")
    
    # Get all agent files
    agent_files = [f for f in os.listdir(agents_dir) 
                  if f.endswith('_agent.py') and f != 'base_agent.py']
    print(f"Found {len(agent_files)} agent files")
    
    for agent_file in agent_files:
        agent_name = agent_file[:-3]  # Remove .py
        if agent_name in AGENT_CONFIGS:
            update_agent(
                os.path.join(agents_dir, agent_file),
                AGENT_CONFIGS[agent_name]
            )
        else:
            print(f"No configuration found for {agent_file}, skipping...")

if __name__ == '__main__':
    main() 