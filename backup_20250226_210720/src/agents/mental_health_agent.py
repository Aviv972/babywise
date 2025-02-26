from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
import re

class MentalHealthAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        super().__init__(agent_type, name, llm_service)

    def get_agent_expertise(self) -> List[str]:
        return [
            'mental health', 'emotional', 'stress', 'anxiety', 'depression',
            'overwhelm', 'support', 'cope', 'feel', 'mood', 'therapy',
            'counseling', 'self-care', 'burnout', 'exhaustion',
            'בריאות נפשית', 'רגשי', 'לחץ', 'חרדה', 'דיכאון',
            'תמיכה', 'התמודדות', 'מצב רוח', 'טיפול', 'ייעוץ'
        ]

    def get_required_fields(self) -> List[str]:
        return ["baby_age", "specific_challenges"]

    def get_agent_prompt(self) -> str:
        return """You are a Mental Health Support Specialist helping parents navigate the emotional challenges of parenting.

Your expertise includes:
1. Identifying signs of parental stress and anxiety
2. Providing coping strategies and self-care tips
3. Suggesting resources for professional help
4. Supporting emotional well-being
5. Addressing common mental health concerns

When responding:
1. Be empathetic and supportive
2. Validate feelings and experiences
3. Provide practical coping strategies
4. Suggest professional help when needed
5. Focus on both parent and baby well-being
6. Consider cultural sensitivity
7. Maintain appropriate boundaries

If you don't have enough information about the parent's specific challenges or the baby's age, ask for clarification."""

    def extract_agent_specific_context(self, message: str, gathered_info: Dict[str, Any]) -> Dict[str, Any]:
        # Extract emotional state and stress levels
        emotional_patterns = {
            "stress_level": r"(?i)(very|extremely|somewhat|mildly)\s+(stressed|anxious|overwhelmed|tired)",
            "mood": r"(?i)feeling\s+(sad|happy|angry|frustrated|hopeless|exhausted)",
            "sleep_quality": r"(?i)(not\s+)?sleeping\s+(well|poorly|badly|good|better)",
            "support_system": r"(?i)(no|limited|good|great)\s+support(\s+system)?"
        }
        
        context = {}
        
        for key, pattern in emotional_patterns.items():
            match = re.search(pattern, message)
            if match:
                context[key] = match.group(0)
        
        # Extract specific concerns
        concerns = []
        concern_keywords = [
            "worried about", "concerned about", "anxious about",
            "struggling with", "having trouble with", "difficulty with"
        ]
        
        for keyword in concern_keywords:
            if keyword in message.lower():
                # Get the text after the keyword
                start_idx = message.lower().find(keyword) + len(keyword)
                end_idx = message.find(".", start_idx)
                if end_idx == -1:
                    end_idx = len(message)
                concerns.append(message[start_idx:end_idx].strip())
        
        if concerns:
            context["specific_concerns"] = concerns
            
        # Update gathered_info with any found context
        if context:
            gathered_info.update(context)
            
        return gathered_info

    def _get_system_prompt(self) -> str:
        return """You are a mental health support specialist focused on helping parents navigate the emotional challenges of parenthood.
                 
                 Key Responsibilities:
                 1. Provide emotional support and validation
                 2. Offer practical coping strategies
                 3. Help identify support resources
                 4. Recognize signs that need professional attention
                 
                 Always:
                 - Be empathetic and non-judgmental
                 - Validate feelings and experiences
                 - Emphasize self-care and support-seeking
                 - Recommend professional help when needed
                 - Maintain appropriate boundaries
                 
                 IMPORTANT: You are not a substitute for professional mental health care.
                 Always encourage seeking professional help for serious concerns."""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract mental health-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        for message in messages:
            content = message.content.lower()
            
            # Extract current concerns
            concern_keywords = ['worried', 'anxious', 'stressed', 'overwhelmed', 'sad', 'depressed']
            if any(keyword in content for keyword in concern_keywords):
                gathered_info["current_concerns"] = content
            
            # Extract support system information
            support_keywords = ['help', 'support', 'partner', 'family', 'friends', 'therapist']
            if any(keyword in content for keyword in support_keywords):
                gathered_info["support_system"] = content
            
            # Extract sleep information (often related to mental health)
            if any(word in content for word in ['sleep', 'tired', 'exhausted', 'rest']):
                gathered_info["sleep_status"] = content
            
            # Extract postpartum period
            if "postpartum" in content or "after birth" in content:
                gathered_info["postpartum_period"] = content
            
            # Extract previous mental health history
            if "history" in content and any(term in content for term in ['anxiety', 'depression', 'mental health']):
                gathered_info["mental_health_history"] = content
        
        return gathered_info

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process mental health-related queries with appropriate support and resources"""
        try:
            # Prepare prompt with context
            prompt_response = await self.llm_service.generate_response(
                prompt=self.prompt.format(
                    chat_history=context["chat_history"],
                    agent_history=context["agent_history"],
                    input=query
                )
            )
            
            response_text = prompt_response.content
            
            # Check for emergency keywords
            emergency_keywords = ['suicide', 'hurt', 'harm', 'end it', 'can\'t go on']
            if any(keyword in query.lower() for keyword in emergency_keywords):
                emergency_resources = """
                IMMEDIATE SUPPORT AVAILABLE:
                - National Crisis Hotline (24/7): 988
                - Postpartum Support International: 1-800-944-4773
                - Text 'HOME' to 741741 to connect with a Crisis Counselor
                
                Please reach out for professional help immediately. You don't have to face this alone."""
                response_text = emergency_resources + "\n\n" + response_text
            
            # Add general mental health resources
            response_text += """
            
            Additional Support Resources:
            1. Postpartum Support International: www.postpartum.net
            2. National Alliance on Mental Illness: www.nami.org
            3. Consider speaking with your healthcare provider about your feelings
            4. Local parent support groups can provide community connection"""
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": response_text
            }
            
        except Exception as e:
            self.logger.error(f"Error in mental health agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your question. If you're experiencing a crisis, please call 988 for immediate support."
            }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is mental_health-related"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = ['anxiety', 'depression', 'stress', 'mood', 'חרדה', 'דיכאון', 'לחץ', 'מצב רוח']
        
        if any(term in query_lower for term in primary_terms):
            print("Found mental_health-specific terms")
            return 1.0
            
        # Secondary domain terms
        secondary_terms = ['worry', 'sad', 'overwhelm', 'cope', 'support', 'דאגה', 'עצוב', 'להתמודד', 'תמיכה']
        
        if any(term in query_lower for term in secondary_terms):
            print("Found mental_health-related terms")
            return 0.7
            
        return 0.0  # Not mental_health-related

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields for mental_health advice"""
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'symptoms' not in gathered_info:
            missing.append('symptoms')
            return missing  # Get symptoms first
            
        if 'duration' not in gathered_info:
            missing.append('duration')
        
        return missing
