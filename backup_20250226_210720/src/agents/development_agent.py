from typing import Dict, List, Any
from src.constants import AgentTypes, ResponseTypes, ContextFields
from .base_agent import BaseAgent
from langchain_core.messages import BaseMessage
import logging
import re
from langchain.prompts import ChatPromptTemplate

class DevelopmentAgent(BaseAgent):
    def __init__(self, agent_type: AgentTypes, name: str, llm_service=None):
        super().__init__(agent_type, name, llm_service)
        
        self.agent_type = AgentTypes.DEVELOPMENT
        self.name = "Child Development & Milestones Specialist"
        self.logger = logging.getLogger(__name__)
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a comprehensive Child Development & Milestones Specialist helping parents understand and support their baby's development.

Key Areas of Expertise:

1. Physical Development
   - Gross Motor Skills
     * Head/neck control
     * Rolling, sitting, crawling
     * Standing, walking, climbing
     * Balance and coordination
   - Fine Motor Skills
     * Grasping and reaching
     * Hand-eye coordination
     * Manipulation of objects
     * Pre-writing skills

2. Cognitive Development
   - Learning and Memory
   - Problem-solving abilities
   - Attention and focus
   - Cause and effect understanding
   - Object permanence
   - Spatial awareness
   - Pattern recognition

3. Language Development
   - Pre-verbal communication
   - Receptive language
   - Expressive language
   - Babbling and first words
   - Gesture development
   - Language milestones
   - Bilingual development

4. Social-Emotional Development
   - Attachment and bonding
   - Emotional expression
   - Social interaction
   - Self-awareness
   - Temperament
   - Play skills
   - Behavioral regulation

5. Sensory Development
   - Visual processing
   - Auditory processing
   - Tactile sensitivity
   - Vestibular development
   - Proprioception
   - Sensory integration
   - Environmental adaptation

Always Consider:
- Age-appropriate expectations
- Individual development patterns
- Cultural influences
- Environmental factors
- Previous medical history
- Family dynamics
- Support systems

Provide:
- Evidence-based guidance
- Age-specific milestones
- Development-promoting activities
- Red flags to watch for
- Progress monitoring tools
- Professional referral guidelines
- Parent education resources"""),
            ("human", """Query: {query}
Baby's Age: {baby_age}
Current Abilities: {current_abilities}
Areas of Concern: {concerns}
Developmental History: {history}
Recent Changes: {recent_changes}
Environmental Factors: {environment}

Please provide:
1. Age-appropriate milestone assessment
2. Development-promoting activities
3. Next expected milestones
4. Red flags to watch for
5. Progress monitoring tips
6. Professional evaluation guidelines
7. Parent support strategies""")
        ])

    def get_agent_expertise(self) -> List[str]:
        """Return the agent's areas of expertise."""
        return [
            # Physical Development
            'motor skills', 'crawling', 'walking', 'coordination',
            'balance', 'strength', 'physical development',
            # Cognitive Development
            'learning', 'memory', 'problem-solving', 'attention',
            'understanding', 'thinking', 'cognitive skills',
            # Language Development
            'speech', 'language', 'communication', 'vocabulary',
            'babbling', 'words', 'expressions',
            # Social-Emotional Development
            'social skills', 'emotions', 'attachment', 'bonding',
            'interaction', 'play', 'behavior',
            # Sensory Development
            'senses', 'vision', 'hearing', 'touch', 'taste',
            'sensory processing', 'integration',
            # Milestones & Assessment
            'milestones', 'development', 'progress', 'screening',
            'evaluation', 'assessment', 'delays',
            # Hebrew
            'התפתחות', 'אבני דרך', 'מוטוריקה', 'שפה', 'חברתי',
            'רגשי', 'קוגניטיבי', 'חושי'
        ]

    def get_required_fields(self) -> List[str]:
        """Return the required fields for development-related queries."""
        return ['baby_age', 'current_abilities', 'areas_of_concern', 'developmental_history']

    def get_agent_prompt(self) -> str:
        """Return the agent's system prompt."""
        return """You are a comprehensive Child Development & Milestones Specialist helping parents understand and support their baby's development.

Key Areas of Expertise:

1. Physical Development
   - Gross Motor Skills
     * Head/neck control
     * Rolling, sitting, crawling
     * Standing, walking, climbing
     * Balance and coordination
   - Fine Motor Skills
     * Grasping and reaching
     * Hand-eye coordination
     * Manipulation of objects
     * Pre-writing skills

2. Cognitive Development
   - Learning and Memory
   - Problem-solving abilities
   - Attention and focus
   - Cause and effect understanding
   - Object permanence
   - Spatial awareness
   - Pattern recognition

3. Language Development
   - Pre-verbal communication
   - Receptive language
   - Expressive language
   - Babbling and first words
   - Gesture development
   - Language milestones
   - Bilingual development

4. Social-Emotional Development
   - Attachment and bonding
   - Emotional expression
   - Social interaction
   - Self-awareness
   - Temperament
   - Play skills
   - Behavioral regulation

5. Sensory Development
   - Visual processing
   - Auditory processing
   - Tactile sensitivity
   - Vestibular development
   - Proprioception
   - Sensory integration
   - Environmental adaptation

Always Consider:
- Age-appropriate expectations
- Individual development patterns
- Cultural influences
- Environmental factors
- Previous medical history
- Family dynamics
- Support systems

Provide:
- Evidence-based guidance
- Age-specific milestones
- Development-promoting activities
- Red flags to watch for
- Progress monitoring tools
- Professional referral guidelines
- Parent education resources"""

    def _extract_context_from_history(self) -> Dict[str, Any]:
        """Extract development-relevant information from conversation history"""
        gathered_info = {}
        messages = self.shared_memory.chat_memory.messages
        
        try:
            for message in messages:
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
                
                # Extract current abilities
                ability_categories = {
                    'physical': ['roll', 'crawl', 'walk', 'sit', 'stand', 'climb', 'run'],
                    'cognitive': ['understand', 'recognize', 'remember', 'find', 'solve', 'play'],
                    'language': ['babble', 'talk', 'word', 'say', 'speak', 'communicate'],
                    'social': ['smile', 'laugh', 'interact', 'play', 'share', 'respond']
                }
                
                for category, keywords in ability_categories.items():
                    if any(keyword in content for keyword in keywords):
                        if "current_abilities" not in gathered_info:
                            gathered_info["current_abilities"] = {}
                        gathered_info["current_abilities"][category] = content
                
                # Extract areas of concern
                concern_keywords = ['worry', 'concern', 'behind', 'delay', 'not yet', 'should']
                if any(keyword in content for keyword in concern_keywords):
                    if "areas_of_concern" not in gathered_info:
                        gathered_info["areas_of_concern"] = []
                    gathered_info["areas_of_concern"].append(content)
                
                # Extract developmental history
                if any(word in content for word in ['history', 'previously', 'before', 'used to']):
                    gathered_info["developmental_history"] = content
            
            return gathered_info
            
        except Exception as e:
            self.logger.error(f"Error extracting development context: {str(e)}")
            return {}

    async def _process_agent_specific(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
                    "text": "To provide appropriate developmental guidance, I need to know your baby's age and current abilities. Could you share this information?",
                    "missing_fields": missing_fields
                }
            
            # Process query with prompt template
            gathered_info = context[ContextFields.GATHERED_INFO]
            result = await self.llm_service.generate_response(
                self.prompt_template.format(
                    query=query,
                    baby_age=gathered_info.get("baby_age", {}).get("original", "Not specified"),
                    current_abilities=gathered_info.get("current_abilities", {}),
                    concerns=gathered_info.get("areas_of_concern", []),
                    history=gathered_info.get("developmental_history", "Not specified"),
                    recent_changes=gathered_info.get("recent_changes", "Not specified"),
                    environment=gathered_info.get("environment", "Not specified")
                )
            )
            
            # Add developmental guidance disclaimer
            disclaimer = "\n\nIMPORTANT: Every child develops at their own pace within a normal range. This information is for general guidance only. If you have specific concerns about your child's development, please consult with your pediatrician or a developmental specialist."
            
            result.content += disclaimer
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": result.content
            }
            
        except Exception as e:
            self.logger.error(f"Error in development agent processing: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "I'm having trouble processing your development-related question. Could you please try rephrasing it?"
            }

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        gathered_info = context.get('gathered_info', {})
        missing = []
        
        if 'baby_age' not in gathered_info:
            missing.append('baby_age')
            return missing  # Get age first
            
        if 'current_abilities' not in gathered_info:
            missing.append('current_abilities')
            return missing  # Get current abilities next
            
        if 'areas_of_concern' not in gathered_info:
            missing.append('areas_of_concern')
        
        return missing
