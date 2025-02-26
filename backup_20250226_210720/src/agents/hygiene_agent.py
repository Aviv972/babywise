from typing import Dict, List, Any, Optional
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage

class HygieneAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Then set agent-specific attributes
        self.agent_type = AgentTypes.HYGIENE
        self.name = "Baby Hygiene Specialist"
        self.expertise = [
            'hygiene', 'cleanliness', 'bath', 'diaper', 'skincare',
            'grooming', 'washing', 'cleaning', 'care', 'routine',
            'products', 'rash', 'infection', 'sanitize', 'sterilize',
            'היגיינה', 'ניקיון', 'אמבטיה', 'חיתול', 'טיפוח',
            'רחצה', 'ניקוי', 'טיפול', 'שגרה', 'מוצרים'
        ]
        self.required_context = ['baby_age', 'hygiene_concern', 'current_routine']
        
        # Care type specific questions
        self.context_questions_map = {
            "bathing": [
                "water_temperature",
                "bath_frequency",
                "skin_reactions",
                "current_products",
                "bath_time_routine"
            ],
            "diapering": [
                "diaper_type",
                "change_frequency",
                "rash_history",
                "current_products",
                "skin_sensitivity"
            ],
            "skincare": [
                "skin_condition",
                "problem_areas",
                "current_products",
                "allergies",
                "weather_effects"
            ],
            "oral": [
                "teeth_status",
                "cleaning_routine",
                "products_used",
                "gum_health",
                "feeding_habits"
            ]
        }

    def _get_system_prompt(self) -> str:
        return """You are a baby hygiene specialist helping parents maintain proper cleanliness and care.
                 
                 Key Responsibilities:
                 1. Guide on proper hygiene practices
                 2. Recommend appropriate products
                 3. Address common hygiene issues
                 4. Establish care routines
                 
                 Always:
                 - Consider age-specific hygiene needs
                 - Emphasize safety in care practices
                 - Recommend gentle, baby-safe products
                 - Include preventive measures
                 - Address skin sensitivities
                 
                 Remember: Baby skin is delicate and requires special care.
                 Focus on gentle, effective hygiene practices that protect
                 the baby's sensitive skin and natural barriers."""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract hygiene-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        for message in messages:
            content = message.content.lower()
            
            # Extract age information
            if "month" in content and any(str(i) for i in range(1, 37)):
                for i in range(1, 37):
                    if f"{i} month" in content:
                        gathered_info["baby_age"] = {
                            "value": i,
                            "unit": "months",
                            "original": f"{i} months"
                        }
                        break
            
            # Extract hygiene concerns
            hygiene_keywords = ['rash', 'irritation', 'dry', 'dirty', 'smell']
            if any(keyword in content for keyword in hygiene_keywords):
                gathered_info["hygiene_concern"] = content
            
            # Extract current routine
            if any(word in content for word in ['routine', 'schedule', 'usually', 'normally']):
                gathered_info["current_routine"] = content
            
            # Extract product information
            if any(word in content for word in ['product', 'soap', 'cream', 'lotion']):
                gathered_info["current_products"] = content
            
            # Extract skin conditions
            if any(word in content for word in ['sensitive', 'allergy', 'reaction', 'eczema']):
                gathered_info["skin_conditions"] = content
        
        return gathered_info

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process hygiene-related queries with age-appropriate guidance"""
        try:
            # Check for urgent concerns
            urgent_keywords = ['severe rash', 'bleeding', 'infection', 'fever', 'pus']
            if any(keyword in query.lower() for keyword in urgent_keywords):
                return {
                    "type": ResponseTypes.EMERGENCY,
                    "text": """CONTACT YOUR HEALTHCARE PROVIDER
                    
                    These symptoms may require medical attention:
                    - Document when symptoms started
                    - Take photos of affected areas
                    - Note any recent changes in routine
                    - Watch for fever or behavior changes
                    
                    In the meantime:
                    - Keep area clean and dry
                    - Avoid new products
                    - Use gentle, fragrance-free products
                    - Monitor for worsening symptoms"""
                }
            
            # Prepare prompt with context
            prompt_response = await self.llm_service.generate_response(
                prompt=self.prompt.format(
                    chat_history=context["chat_history"],
                    agent_history=context["agent_history"],
                    input=query
                )
            )
            
            response_text = prompt_response.content
            
            # Add age-specific hygiene guidance
            gathered_info = context[ContextFields.GATHERED_INFO]
            baby_age = gathered_info.get("baby_age", {}).get("value", 0)
            
            if baby_age > 0:
                response_text += f"""
                
                Hygiene Guidelines ({baby_age} months):
                1. Daily Care Routine:
                   - Gentle cleansing practices
                   - Appropriate product selection
                   - Frequency recommendations
                   - Special attention areas
                
                2. Common Concerns:
                   - Age-specific issues to watch
                   - Prevention strategies
                   - Normal vs. concerning signs
                   - When to seek medical advice
                
                3. Product Recommendations:
                   - Age-appropriate products
                   - Ingredient considerations
                   - Application guidelines
                   - Storage and safety tips
                
                Remember: Every baby's skin is unique. Observe reactions to
                products and adjust routine as needed. When in doubt,
                consult your pediatrician."""
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": response_text
            }
            
        except Exception as e:
            self.logger.error(f"Error in hygiene agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your hygiene-related question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is hygiene-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = ['hygiene', 'bath', 'diaper', 'clean', 'היגיינה', 'אמבטיה', 'חיתול', 'ניקיון']
        
        if any(term in query_lower for term in primary_terms):
            print("Found hygiene-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = ['wash', 'wipe', 'cream', 'rash', 'לרחוץ', 'מגבון', 'קרם', 'פריחה']
        
        if any(term in query_lower for term in secondary_terms):
            print("Found hygiene-related terms")
            return 0.7
            
        return 0.0  # Not hygiene-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for hygiene advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'hygiene_concern' not in gathered_info:
            missing.append('hygiene_concern')
            return missing  # Get hygiene concern next
            
        if 'current_routine' not in gathered_info:
            missing.append('current_routine')
        
        return missing

    def _prepare_prompt(self, query: str) -> str:
        return f"""As a baby hygiene and care expert, provide detailed guidance about: {query}

              Analysis Framework:
              1. Daily Care Routine
                 - Step-by-step procedures
                 - Frequency recommendations
                 - Age-specific considerations
                 - Best practices
              
              2. Diapering
                 - Proper technique
                 - Rash prevention
                 - Product selection
                 - Change frequency
                 - Warning signs
              
              3. Bathing & Skincare
                 - Bath safety measures
                 - Water temperature
                 - Product recommendations
                 - Skin condition monitoring
                 - Special care areas
              
              4. Health & Safety
                 - Hygiene best practices
                 - Infection prevention
                 - Environmental factors
                 - When to seek medical help
                 - Emergency situations
              
              5. Equipment & Supplies
                 - Essential items
                 - Product safety
                 - Storage requirements
                 - Travel considerations
                 - Cost-effective options
              
              Important Guidelines:
              - Prioritize baby's comfort
              - Maintain proper sanitation
              - Monitor skin reactions
              - Follow safety protocols
              - Consider environmental impact
              
              Medical Note: For persistent skin issues or health concerns, consult a healthcare provider.
              Respond in the same language as the question."""

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        confidence = self._calculate_confidence(query, keywords)
        print(f"Hygiene confidence for '{query}': {confidence}")
        return confidence > 0.2

    def _identify_care_type(self, query: str) -> Optional[str]:
        care_keywords = {
            "bathing": ["bath", "wash", "clean", "אמבטיה", "רחצה", "ניקיון"],
            "diapering": ["diaper", "change", "rash", "חיתול", "החלפה", "תפרחת"],
            "skincare": ["skin", "cream", "lotion", "עור", "קרם", "תחליב"],
            "oral": ["teeth", "gums", "mouth", "שיניים", "חניכיים", "פה"]
        }
        
        query_lower = query.lower()
        for ctype, keywords in care_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return ctype
        return None 

    def _set_role_boundaries(self):
        self.role_boundaries = {
            "can_do": [
                "basic hygiene guidance",
                "bathing instructions",
                "diapering tips",
                "skincare routines",
                "oral care basics",
                "grooming advice"
            ],
            "cannot_do": [
                "medical skin conditions",
                "infection treatment",
                "medication recommendations",
                "dental procedures",
                "medical diagnoses",
                "prescription advice"
            ],
            "refer_to": {
                "skin_conditions": "pediatrician/dermatologist",
                "infections": "healthcare provider",
                "dental_issues": "pediatric dentist",
                "severe_rashes": "dermatologist",
                "oral_problems": "pediatric dentist",
                "persistent_issues": "healthcare provider"
            }
        } 