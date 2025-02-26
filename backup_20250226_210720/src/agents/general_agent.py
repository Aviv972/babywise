from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from src.langchain.config import BabywiseState, extract_context_from_messages
import re
import logging

logger = logging.getLogger(__name__)

class GeneralAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        # Call parent class initialization first
        super().__init__(agent_type, name, llm_service)
        
        # Define expertise areas for the general agent
        self.expertise_areas = [
            "Sleep schedules and routines",
            "Feeding and nutrition",
            "Baby gear recommendations",
            "Developmental milestones",
            "Health and safety",
            "Parenting techniques",
            "Common baby issues",
            "Daily care routines",
            "Baby products and essentials",
            "Travel with babies",
            "Baby-proofing",
            "First aid basics",
            "Emotional development",
            "Parent self-care",
            "Family dynamics"
        ]
        
        # Then set agent-specific attributes
        self.name = "Baby Care & Parenting Guide"
        self.expertise = self.get_agent_expertise()
        
        self.required_context = [
            'baby_age', 'current_concern', 'parenting_style',
            'family_situation', 'support_system'
        ]
        
        self.logger = logging.getLogger(__name__)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a comprehensive Baby Care & Parenting Guide, serving as the primary coordinator for all baby-related queries.

Key Areas of Expertise:

1. Holistic Baby Care
   - Daily routines and schedules
   - Essential care practices
   - Age-appropriate guidance
   - Common challenges
   - Best practices
   - Cultural considerations

2. Development & Growth
   - Physical milestones
   - Cognitive development
   - Social-emotional progress
   - Language acquisition
   - Red flags to watch
   - Normal variations

3. Health & Safety
   - Preventive care
   - Safety measures
   - Common health issues
   - Emergency situations
   - When to seek help
   - First aid basics

4. Parenting Support
   - Parenting styles
   - Bonding techniques
   - Communication skills
   - Behavior guidance
   - Confidence building
   - Stress management

5. Family Dynamics
   - Sibling relationships
   - Partner involvement
   - Family adjustments
   - Work-life balance
   - Support networks
   - Resource utilization

6. Problem-Solving
   - Common challenges
   - Practical solutions
   - Preventive strategies
   - Troubleshooting
   - Expert referrals
   - Follow-up care

Always Consider:
- Baby's exact age and stage
- Family's unique situation
- Cultural background
- Available resources
- Support system
- Parenting goals
- Environmental factors

Provide:
- Clear, practical advice
- Evidence-based information
- Age-appropriate recommendations
- Safety guidelines
- Warning signs
- Resource referrals
- Follow-up suggestions"""),
            ("human", """Query: {query}
Baby's Age: {baby_age}
Current Concern: {current_concern}
Parenting Style: {parenting_style}
Family Situation: {family_situation}
Support System: {support_system}
Previous Advice: {previous_advice}

Please provide:
1. Initial assessment
2. Practical guidance
3. Age-appropriate recommendations
4. Safety considerations
5. Support strategies
6. Resource suggestions
7. Follow-up recommendations""")
        ])
        
        logger.info(f"Initialized {self.name} with expertise in: {', '.join(self.get_agent_expertise())}")

    def get_agent_prompt(self) -> str:
        """Get the agent's system prompt."""
        return f"""You are {self.name}, a knowledgeable and empathetic baby care expert. 
        Your expertise covers: {', '.join(self.expertise_areas)}.
        
        Guidelines:
        1. Provide clear, practical advice based on current best practices
        2. Consider the baby's age and developmental stage when giving advice
        3. Emphasize safety and well-being in all recommendations
        4. Be empathetic and supportive of parents' concerns
        5. Clarify any ambiguities by asking specific questions
        6. Maintain consistency with previous advice and context
        7. Cite reliable sources when appropriate
        8. Encourage consultation with healthcare providers for medical issues
        
        Remember to:
        - Keep responses concise but informative
        - Use simple, clear language
        - Break down complex topics into manageable steps
        - Acknowledge parental concerns and emotions
        - Stay within your expertise areas
        - Ask for clarification when needed"""

    def get_agent_expertise(self) -> List[str]:
        """Get the agent's areas of expertise."""
        return [
            # Daily Care
            'baby care', 'routine', 'schedule', 'daily needs',
            'essentials', 'basics', 'general advice', 'tips',
            # Development & Growth
            'growth', 'development', 'milestones', 'stages',
            'age-appropriate', 'normal', 'typical', 'progress',
            # Health & Safety
            'health', 'safety', 'well-being', 'protection',
            'prevention', 'risk', 'emergency', 'first aid',
            # Parenting Skills
            'parenting', 'bonding', 'attachment', 'interaction',
            'communication', 'guidance', 'discipline', 'habits'
        ]

    def get_required_fields(self) -> List[str]:
        return self.required_context

    def extract_agent_specific_context(self, content: str) -> Dict[str, Any]:
        """Add general context extraction"""
        context = {}
        
        # Extract parenting style
        if any(word in content for word in ['style', 'approach', 'method', 'philosophy']):
            context["parenting_style"] = content
        
        # Extract daily routine
        if any(word in content for word in ['routine', 'schedule', 'daily', 'pattern']):
            context["daily_routine"] = {
                "type": "general",
                "description": content
            }
        
        # Extract specific challenges
        if any(word in content for word in ['challenge', 'difficult', 'struggle', 'issue']):
            context["specific_challenges"] = content
        
        return context

    def _extract_context_from_history(self) -> Dict[str, Any]:
        gathered_info = {}
        try:
            for message in self.shared_memory.chat_memory.messages:
                content = message.content.lower()
                
                # Extract age information
                month_patterns = [
                    r'(\d+)[\s-]month[\s-]old',
                    r'(\d+)[\s-]months[\s-]old',
                    r'(\d+)[\s-]month',
                    r'(\d+)[\s-]months'
                ]
                
                for pattern in month_patterns:
                    match = re.search(pattern, content)
                    if match:
                        age_value = int(match.group(1))
                        gathered_info["baby_age"] = {
                            "value": age_value,
                            "unit": "months",
                            "original": f"{age_value} months"
                        }
                        break
                
                # Extract current concerns with categorization
                concern_categories = {
                    'health': ['sick', 'fever', 'symptoms', 'pain', 'doctor'],
                    'development': ['milestone', 'growth', 'skill', 'progress'],
                    'behavior': ['crying', 'sleep', 'feeding', 'fussy'],
                    'safety': ['safety', 'accident', 'injury', 'risk'],
                    'parenting': ['routine', 'schedule', 'advice', 'help']
                }
                
                for category, keywords in concern_categories.items():
                    if any(keyword in content for keyword in keywords):
                        if "current_concern" not in gathered_info:
                            gathered_info["current_concern"] = {}
                        gathered_info["current_concern"][category] = content
                
                # Extract parenting style
                parenting_styles = {
                    'attachment': ['attachment', 'responsive', 'gentle'],
                    'structured': ['schedule', 'routine', 'structured'],
                    'traditional': ['traditional', 'conventional', 'strict'],
                    'mixed': ['flexible', 'balanced', 'combination']
                }
                
                for style, keywords in parenting_styles.items():
                    if any(keyword in content for keyword in keywords):
                        gathered_info["parenting_style"] = {
                            'style': style,
                            'description': content
                        }
                        break
                
                # Extract family situation
                family_keywords = {
                    'structure': ['single', 'married', 'partner', 'divorced'],
                    'siblings': ['sibling', 'brother', 'sister', 'older', 'younger'],
                    'living': ['live', 'home', 'apartment', 'house'],
                    'work': ['work', 'job', 'career', 'stay at home']
                }
                
                for aspect, keywords in family_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        if "family_situation" not in gathered_info:
                            gathered_info["family_situation"] = {}
                        gathered_info["family_situation"][aspect] = content
                
                # Extract support system
                support_keywords = ['help', 'support', 'family', 'friend', 'community']
                if any(keyword in content for keyword in support_keywords):
                    gathered_info["support_system"] = content
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting general context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process general queries and coordinate with other agents as needed."""
        try:
            # Extract and update context
            new_context = self._extract_context_from_history()
            if new_context:
                context[ContextFields.GATHERED_INFO].update(new_context)
            
            # Check for missing critical information
            missing_fields = self._get_missing_critical_fields(context)
            if missing_fields:
                return {
                    "type": ResponseTypes.QUERY,
                    "text": "To help you better, could you tell me your baby's age and what specific concerns you have?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                    current_concern=gathered_info.get("current_concern", {}),
                    parenting_style=gathered_info.get("parenting_style", {}).get("description", "Not specified"),
                    family_situation=gathered_info.get("family_situation", "Not specified"),
                    support_system=gathered_info.get("support_system", "Not specified"),
                    previous_advice=gathered_info.get("previous_advice", "None")
                )
            )
            
            # Add general guidance disclaimer
            disclaimer = "\n\nNote: This is general guidance based on common parenting practices. Always consult with your pediatrician for medical advice and adjust recommendations to fit your family's unique needs."
            
            result.content += disclaimer
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in general agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your question. Could you please try rephrasing it?"
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Calculate relevance for general baby care queries"""
        query_lower = query.lower()
        
        # Primary domain terms (general baby care)
        primary_terms = [
            'baby', 'infant', 'child', 'care', 'help', 'advice',
            'תינוק', 'פעוט', 'ילד', 'טיפול', 'עזרה', 'ייעוץ'
        ]
        
        if any(term in query_lower for term in primary_terms):
            return 1.0
            
        # Secondary domain terms
        secondary_terms = [
            'routine', 'schedule', 'question', 'concern', 'normal',
            'שגרה', 'לוח זמנים', 'שאלה', 'דאגה', 'רגיל'
        ]
        
        if any(term in query_lower for term in secondary_terms):
            return 0.7
            
        return 0.0

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'current_concern' not in gathered_info:
            missing.append('current_concern')
            return missing  # Get current concern next
            
        if 'parenting_style' not in gathered_info:
            missing.append('parenting_style')
            
        if 'family_situation' not in gathered_info:
            missing.append('family_situation')
        
        return missing

    async def invoke(self, state: BabywiseState) -> BabywiseState:
        """Process input through agent"""
        try:
            # Extract context from messages
            extracted_context = extract_context_from_messages(state["messages"])
            
            # Update state metadata with extracted context
            if "metadata" not in state:
                state["metadata"] = {}
            if "extracted_context" not in state["metadata"]:
                state["metadata"]["extracted_context"] = {}
            state["metadata"]["extracted_context"].update(extracted_context)
            
            # Generate response using LLM
            prompt = self.get_agent_prompt()
            response = await self.llm_service.agenerate_response(
                messages=state["messages"],
                system_prompt=prompt,
                context=state["metadata"]["extracted_context"]
            )
            
            # Add response to messages
            state["messages"].append(response)
            state["agent_type"] = self.agent_type.value
            
            return state
            
        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
            error_msg = "I apologize, but I encountered an error. Let me try to help you in a simpler way."
            state["messages"].append(AIMessage(content=error_msg))
            return state
