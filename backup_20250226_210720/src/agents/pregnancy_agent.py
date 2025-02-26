from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
from langchain.prompts import ChatPromptTemplate
import logging
import re

class PregnancyAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Then set agent-specific attributes
        self.agent_type = AgentTypes.PREGNANCY
        self.name = "Pregnancy & Prenatal Care Specialist"
        self.logger = logging.getLogger(__name__)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a comprehensive Pregnancy & Prenatal Care Specialist helping expectant parents navigate their pregnancy journey.

Key Areas of Expertise:

1. Pregnancy Timeline & Development
   - Trimester-specific changes
   - Fetal development stages
   - Expected milestones
   - Normal vs. concerning symptoms
   - Growth tracking
   - Term definitions

2. Physical Health & Medical Care
   - Prenatal care schedule
   - Required screenings & tests
   - Common symptoms management
   - Warning signs
   - Pain management
   - Exercise guidelines
   - Sleep recommendations

3. Nutrition & Wellness
   - Dietary requirements
   - Essential nutrients
   - Food safety
   - Weight gain guidelines
   - Hydration needs
   - Exercise safety
   - Rest requirements

4. Mental & Emotional Health
   - Mood changes
   - Stress management
   - Anxiety support
   - Depression screening
   - Relationship dynamics
   - Support system building
   - Emotional preparation

5. Birth Preparation
   - Birth plan development
   - Hospital checklist
   - Labor signs
   - Pain management options
   - Delivery methods
   - Recovery planning
   - Postpartum preparation

6. Lifestyle Adjustments
   - Work modifications
   - Travel guidelines
   - Activity restrictions
   - Environmental safety
   - Relationship changes
   - Family planning

Always Consider:
- Individual health history
- Risk factors
- Support system
- Cultural preferences
- Previous pregnancies
- Living situation
- Work environment

Provide:
- Evidence-based information
- Clear medical guidance
- Practical solutions
- Warning signs
- Emergency indicators
- Resource referrals
- Follow-up recommendations"""),
            ("human", """Query: {query}
Pregnancy Week: {pregnancy_week}
Current Symptoms: {symptoms}
Medical History: {medical_history}
Current Concerns: {concerns}
Support System: {support}
Previous Pregnancies: {previous_pregnancies}

Please provide:
1. Week-specific guidance
2. Symptom management
3. Next milestones/changes
4. Safety considerations
5. Lifestyle recommendations
6. Warning signs to watch
7. When to contact healthcare provider""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Return the agent's areas of expertise."""
        return [
            # Pregnancy Stages
            'pregnancy', 'trimester', 'prenatal', 'gestation',
            'conception', 'fetal', 'development', 'birth',
            # Physical Changes
            'symptoms', 'morning sickness', 'fatigue', 'pain',
            'weight gain', 'body changes', 'discomfort',
            # Medical Care
            'checkup', 'ultrasound', 'screening', 'test',
            'doctor', 'midwife', 'hospital', 'birth plan',
            # Nutrition & Wellness
            'nutrition', 'diet', 'exercise', 'vitamins',
            'supplements', 'rest', 'sleep', 'health',
            # Mental Health
            'emotions', 'stress', 'anxiety', 'depression',
            'support', 'relationship', 'partner', 'family',
            # Preparation
            'planning', 'registry', 'nursery', 'gear',
            'classes', 'education', 'support group',
            # Hebrew
            'הריון', 'לידה', 'טיפול', 'בדיקות', 'תזונה',
            'תסמינים', 'רופא', 'מיילדת', 'הכנה'
        ]

    def get_required_fields(self) -> List[str]:
        """Return the required fields for pregnancy-related queries."""
        return [
            'pregnancy_week',
            'symptoms',
            'medical_history',
            'current_concerns'
        ]

    def get_agent_prompt(self) -> str:
        """Return the agent's system prompt."""
        return """You are a comprehensive Pregnancy & Prenatal Care Specialist helping expectant parents navigate their pregnancy journey.

Key Areas of Expertise:

1. Pregnancy Timeline & Development
   - Trimester-specific changes
   - Fetal development stages
   - Expected milestones
   - Normal vs. concerning symptoms
   - Growth tracking
   - Term definitions

2. Physical Health & Medical Care
   - Prenatal care schedule
   - Required screenings & tests
   - Common symptoms management
   - Warning signs
   - Pain management
   - Exercise guidelines
   - Sleep recommendations

3. Nutrition & Wellness
   - Dietary requirements
   - Essential nutrients
   - Food safety
   - Weight gain guidelines
   - Hydration needs
   - Exercise safety
   - Rest requirements

4. Mental & Emotional Health
   - Mood changes
   - Stress management
   - Anxiety support
   - Depression screening
   - Relationship dynamics
   - Support system building
   - Emotional preparation

5. Birth Preparation
   - Birth plan development
   - Hospital checklist
   - Labor signs
   - Pain management options
   - Delivery methods
   - Recovery planning
   - Postpartum preparation

6. Lifestyle Adjustments
   - Work modifications
   - Travel guidelines
   - Activity restrictions
   - Environmental safety
   - Relationship changes
   - Family planning

Always Consider:
- Individual health history
- Risk factors
- Support system
- Cultural preferences
- Previous pregnancies
- Living situation
- Work environment

Provide:
- Evidence-based information
- Clear medical guidance
- Practical solutions
- Warning signs
- Emergency indicators
- Resource referrals
- Follow-up recommendations"""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        gathered_info = {}
        try:
            for message in self.shared_memory.chat_memory.messages:
                content = message.content.lower()
                
                # Extract pregnancy week
                week_patterns = [
                    r'(\d+)\s*weeks?\s*pregnant',
                    r'(\d+)\s*weeks?\s*along',
                    r'(\d+)\s*weeks?\s*gestation',
                    r'week\s*(\d+)'
                ]
                
                for pattern in week_patterns:
                    match = re.search(pattern, content)
                    if match:
                        week_value = int(match.group(1))
                        trimester = 1 if week_value <= 13 else (2 if week_value <= 26 else 3)
                        gathered_info["pregnancy_week"] = {
                            "value": week_value,
                            "trimester": trimester,
                            "original": f"Week {week_value}"
                        }
                        break
                
                # Extract symptoms with categorization
                symptom_categories = {
                    'nausea': ['nausea', 'morning sickness', 'vomiting', 'sick'],
                    'pain': ['pain', 'ache', 'cramp', 'sore', 'discomfort'],
                    'fatigue': ['tired', 'exhausted', 'fatigue', 'sleepy'],
                    'mood': ['emotional', 'mood', 'anxious', 'stressed'],
                    'physical': ['swelling', 'bleeding', 'spotting', 'discharge']
                }
                
                for category, keywords in symptom_categories.items():
                    if any(keyword in content for keyword in keywords):
                        if "symptoms" not in gathered_info:
                            gathered_info["symptoms"] = {}
                        gathered_info["symptoms"][category] = content
                
                # Extract medical history
                medical_conditions = [
                    'diabetes', 'hypertension', 'thyroid', 'asthma',
                    'previous miscarriage', 'previous cesarean', 'complications'
                ]
                if any(condition in content for condition in medical_conditions):
                    if "medical_history" not in gathered_info:
                        gathered_info["medical_history"] = []
                    gathered_info["medical_history"].append(content)
                
                # Extract current concerns
                concern_keywords = ['worried', 'concerned', 'afraid', 'unsure', 'question']
                if any(keyword in content for keyword in concern_keywords):
                    if "current_concerns" not in gathered_info:
                        gathered_info["current_concerns"] = []
                    gathered_info["current_concerns"].append(content)
                
                # Extract support system
                support_keywords = ['partner', 'family', 'doctor', 'midwife', 'doula', 'friend']
                if any(keyword in content for keyword in support_keywords):
                    gathered_info["support_system"] = content
                
                # Extract previous pregnancies
                if any(term in content for term in ['previous pregnancy', 'last time', 'before']):
                    gathered_info["previous_pregnancies"] = content
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting pregnancy context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Check for emergency symptoms first
            emergency_symptoms = [
                'severe pain', 'heavy bleeding', 'no movement',
                'water broke', 'contractions', 'severe headache'
            ]
            if any(symptom in query.lower() for symptom in emergency_symptoms):
                return {
                    "type": ResponseTypes.EMERGENCY,
                    "text": """CONTACT YOUR HEALTHCARE PROVIDER IMMEDIATELY

These symptoms require immediate medical attention. While waiting:
1. Stay calm and sit or lie down
2. Note when symptoms started
3. Document any changes
4. Have someone available to drive you
5. Keep your medical information handy

Do not delay seeking emergency care."""
                }
            
            # Extract and update context
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To provide appropriate pregnancy guidance, I need to know how many weeks pregnant you are. Could you share this information?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    pregnancy_week=gathered_info.get("pregnancy_week", {}).get("original", "Not specified"),
                    symptoms=gathered_info.get("symptoms", {}),
                    medical_history=gathered_info.get("medical_history", []),
                    concerns=gathered_info.get("current_concerns", []),
                    support=gathered_info.get("support_system", "Not specified"),
                    previous_pregnancies=gathered_info.get("previous_pregnancies", "Not specified")
                )
            )
            
            # Add medical disclaimer
            disclaimer = "\n\nIMPORTANT: This information is for educational purposes only and not a substitute for professional medical care. Always consult your healthcare provider for medical advice, especially during pregnancy."
            
            result.content += disclaimer
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in pregnancy agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your pregnancy-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        query_lower = query.lower()
        if any(term in query_lower for term in ['pregnant', 'pregnancy', 'trimester']):
            return 1.0
        if any(term in query_lower for term in ['baby', 'ultrasound', 'checkup']):
            return 0.7
        return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'pregnancy_week' not in gathered_info:
            missing.append('pregnancy_week')
            return missing  # Get pregnancy week first
            
        if 'symptoms' not in gathered_info:
            missing.append('symptoms')
            return missing  # Get symptoms next
            
        if 'current_concerns' not in gathered_info:
            missing.append('current_concerns')
            
        if 'medical_history' not in gathered_info:
            missing.append('medical_history')
        
        return missing 