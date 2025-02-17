from typing import Dict, List, Optional
from src.agents.base_agent import BaseAgent
from src.constants import ResponseTypes, AgentTypes

def _set_role_boundaries(self):
    self.role_boundaries = {
        "can_do": [
            "emotional support guidance",
            "stress management tips",
            "self-care suggestions",
            "parenting anxiety support",
            "work-life balance advice",
            "relationship adjustment tips"
        ],
        "cannot_do": [
            "mental health diagnosis",
            "therapy services",
            "medication advice",
            "crisis intervention",
            "trauma counseling",
            "psychiatric treatment"
        ],
        "refer_to": {
            "mental_health": "mental health professional",
            "crisis": "emergency mental health services",
            "therapy": "licensed therapist",
            "medication": "psychiatrist",
            "relationships": "family counselor",
            "postpartum_depression": "mental health specialist"
        }
    } 

class MentalHealthAgent(BaseAgent):
    """Agent specialized in handling mental health related queries with appropriate care and boundaries"""
    
    def __init__(self, llm_service):
        super().__init__(llm_service)
        self.agent_type = AgentTypes.MENTAL_HEALTH
        self.name = "Mental Health Support Agent"
        self.expertise = [
            "postpartum depression",
            "baby blues",
            "maternal mental health",
            "emotional support",
            "stress management",
            "self-care",
            "parenting anxiety"
        ]
        
        # Define medical disclaimer
        self.medical_disclaimer = (
            "⚠️ Important: I want to clarify that I'm not a medical professional. "
            "This information is for educational purposes only. "
            "For medical advice, diagnosis, or treatment, please consult with your healthcare provider."
        )
        
        # Define emergency resources
        self.emergency_resources = """
        If you're having thoughts of harming yourself or your baby, please:
        - Call 988 (US Suicide & Crisis Lifeline) - Available 24/7
        - Contact your healthcare provider immediately
        - Go to the nearest emergency room
        - Call 911 if you're in immediate danger
        
        Additional Resources:
        - Postpartum Support International Helpline: 1-800-944-4773
        - Text "HOME" to 741741 to connect with a Crisis Counselor
        """
        
        self._set_role_boundaries()

    async def process_query(self, query: str, context: Optional[Dict] = None, chat_history: Optional[List[Dict]] = None) -> Dict:
        """Process mental health related queries with appropriate care and support"""
        try:
            # Start with the medical disclaimer
            response_parts = [self.medical_disclaimer, ""]
            
            # Check for emergency keywords
            emergency_terms = ['suicidal', 'harm', 'hurt', 'kill', 'die', 'end it']
            if any(term in query.lower() for term in emergency_terms):
                response_parts.append("\n⚠️ This sounds like an emergency situation.\n")
                response_parts.append(self.emergency_resources)
                return {
                    'type': ResponseTypes.ANSWER,
                    'text': "\n".join(response_parts)
                }
            
            # Process specific mental health topics
            if 'baby blues' in query.lower() or 'postpartum depression' in query.lower():
                response_parts.extend([
                    "Let me explain the difference between baby blues and postpartum depression:",
                    
                    "🔹 Baby Blues:",
                    "- Very common, affecting up to 80% of new mothers",
                    "- Usually starts 2-3 days after delivery",
                    "- Typically lasts for a few days up to two weeks",
                    "- Symptoms include:",
                    "  • Mood swings",
                    "  • Crying spells",
                    "  • Anxiety",
                    "  • Difficulty sleeping",
                    "  • Feeling overwhelmed",
                    "",
                    "🔸 Postpartum Depression (PPD):",
                    "- More serious condition affecting about 1 in 7 new mothers",
                    "- Can develop anytime within the first year after birth",
                    "- Lasts longer than two weeks",
                    "- Symptoms include:",
                    "  • Persistent sadness or emptiness",
                    "  • Loss of interest in activities",
                    "  • Changes in sleep and appetite",
                    "  • Difficulty bonding with the baby",
                    "  • Feelings of worthlessness or guilt",
                    "  • Thoughts of harming yourself or the baby",
                    "",
                    "🚨 Important: If you're experiencing symptoms of postpartum depression, please:",
                    "1. Talk to your healthcare provider",
                    "2. Reach out to loved ones for support",
                    "3. Remember that this is not your fault and help is available",
                    "",
                    "📞 Resources:",
                    "- Postpartum Support International Helpline: 1-800-944-4773",
                    "- National Crisis Hotline: 988",
                    "- Text 'HOME' to 741741 to connect with a Crisis Counselor"
                ])
            
            return {
                'type': ResponseTypes.ANSWER,
                'text': "\n".join(response_parts)
            }
            
        except Exception as e:
            print(f"Error in mental health agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I apologize, but I'm having trouble processing your request. If you're experiencing a mental health emergency, please contact emergency services or call 988 for immediate support."
            } 