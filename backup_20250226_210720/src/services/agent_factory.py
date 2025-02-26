from typing import Dict, Optional, List, Tuple, Type, Any
from src.constants import AgentTypes, DynamicFieldDetector, ResponseTypes, ContextFields
from src.agents.general_agent import GeneralAgent
from src.agents.baby_gear_agent import BabyGearAgent
from src.agents.pregnancy_agent import PregnancyAgent
from src.agents.travel_agent import TravelAgent
from src.services.llm_service import LLMService
from src.agents.base_agent import BaseAgent
from src.langchain.config import BabywiseState
from src.utils.memory_utils import get_or_create_memory
from datetime import datetime, timedelta
import logging
from src.agents.sleep_agent import SleepAgent
from src.agents.feeding_agent import FeedingAgent
from src.agents.health_agent import HealthAgent
from src.agents.development_agent import DevelopmentAgent
import traceback
from langchain.memory import ConversationBufferMemory

logger = logging.getLogger(__name__)

class TransitionConfig:
    MIN_CONFIDENCE_THRESHOLD = 0.3
    MAX_TRANSITIONS_PER_MINUTE = 2
    CONFIDENCE_BOOST_THRESHOLD = 0.3
    TRANSITION_COOLDOWN = timedelta(seconds=30)

class AgentFactory:
    """Factory class for creating and managing agents."""
    
    def __init__(self, llm_service=None):
        """Initialize the agent factory."""
        self.llm_service = llm_service
        self.shared_memory = ConversationBufferMemory()
        self.logger = logging.getLogger(__name__)
        
        # Register all available agents
        self.agent_registry = {
            AgentTypes.GENERAL: GeneralAgent,
            AgentTypes.SLEEP: SleepAgent,
            AgentTypes.HEALTH: HealthAgent,
            AgentTypes.DEVELOPMENT: DevelopmentAgent,
            AgentTypes.FEEDING: FeedingAgent,
            AgentTypes.BABY_GEAR: BabyGearAgent,
            AgentTypes.TRAVEL: TravelAgent,
            AgentTypes.PREGNANCY: PregnancyAgent
        }
        
        # Initialize agent keywords for confidence calculation
        self.agent_keywords = {
            AgentTypes.GENERAL: [
                'general', 'advice', 'help', 'question', 'guidance',
                'recommendation', 'suggestion', 'tip', 'info'
            ],
            AgentTypes.PREGNANCY: [
                'pregnant', 'pregnancy', 'trimester', 'birth', 'labor',
                'הריון', 'טרימסטר', 'לידה', 'צירים', 'הריונית'
            ],
            AgentTypes.TRAVEL: [
                'travel', 'trip', 'flight', 'journey', 'vacation',
                'נסיעה', 'טיול', 'טיסה', 'מסע', 'חופשה'
            ],
            AgentTypes.SLEEP: [
                'sleep', 'nap', 'bedtime', 'night', 'routine', 'schedule',
                'tired', 'rest', 'שינה', 'לילה', 'שעות'
            ],
            AgentTypes.FEEDING: [
                'feed', 'eat', 'milk', 'formula', 'breast', 'bottle', 'solid',
                'hunger', 'food', 'האכלה', 'הנקה', 'אוכל', 'בקבוק'
            ],
            AgentTypes.HEALTH: [
                'sick', 'fever', 'doctor', 'medicine', 'symptom', 'pain',
                'health', 'vaccine', 'חום', 'חולה', 'רופא', 'תרופה'
            ],
            AgentTypes.DEVELOPMENT: [
                'milestone', 'develop', 'growth', 'skill', 'learn', 'crawl',
                'walk', 'talk', 'התפתחות', 'גדילה', 'אבני דרך'
            ],
            AgentTypes.BABY_GEAR: [
                'stroller', 'car seat', 'crib', 'carrier', 'toy', 'diaper',
                'bottle', 'monitor', 'עגלה', 'מוצר', 'ציוד'
            ]
        }
        
        # Initialize agent pool
        self.agents = {}
        self._initialize_agents()
        self.field_detector = DynamicFieldDetector()
        self.config = TransitionConfig()
        
        logger.info("Initialized AgentFactory with agents: %s", ", ".join(self.agent_registry.keys()))
        
    def _initialize_agents(self):
        """Initialize all available agents with logging"""
        logger.info("Initializing agent pool")
        
        # Initialize general agent first as it's the default fallback
        self.agents['general'] = self.create_agent(AgentTypes.GENERAL, "global")
        
        # Initialize other commonly used agents
        common_agents = [
            AgentTypes.BABY_GEAR,
            AgentTypes.FEEDING,
            AgentTypes.SLEEP,
            AgentTypes.HEALTH,
            AgentTypes.DEVELOPMENT,
            AgentTypes.TRAVEL,
            AgentTypes.PREGNANCY
        ]
        
        for agent_type in common_agents:
            self.agents[agent_type] = self.create_agent(agent_type, "global")
        
        logger.info(f"Initialized {len(self.agents)} agents: {list(self.agents.keys())}")
        
    def get_agent(self, message: str) -> BaseAgent:
        """Get the appropriate agent based on the message content"""
        # Simple keyword-based routing for now
        if any(keyword in message.lower() for keyword in ['stroller', 'crib', 'car seat', 'bottle', 'diaper']):
            logger.info("Selected baby gear agent")
            return self.agents['baby_gear']
        
        logger.info("Selected general agent")
        return self.agents['general']

    def _get_recent_transitions(self, state: Dict) -> List[Dict]:
        """Get recent transitions from state"""
        transitions = state.get("transitions", [])
        return [
            t for t in transitions 
            if datetime.now() - datetime.fromisoformat(t['timestamp']) < timedelta(minutes=1)
        ]
        
    def _add_transition(self, state: Dict, from_agent: str, to_agent: str, confidence: float) -> None:
        """Add transition to state"""
        if "transitions" not in state:
            state["transitions"] = []
            
        state["transitions"].append({
            'from_agent': from_agent,
            'to_agent': to_agent,
            'confidence': confidence,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    def _is_transition_rate_exceeded(self, state: Dict) -> bool:
        """Check if maximum transition rate is exceeded"""
        recent = self._get_recent_transitions(state)
        return len(recent) >= self.config.MAX_TRANSITIONS_PER_MINUTE
        
    def _is_in_cooldown(self, state: Dict) -> bool:
        """Check if in transition cooldown period"""
        transitions = state.get("transitions", [])
        if not transitions:
            return False
            
        last_transition = transitions[-1]
        return datetime.now() - datetime.fromisoformat(last_transition['timestamp']) < self.config.TRANSITION_COOLDOWN
        
    async def get_agent_for_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        current_agent_type: Optional[str] = None,
        state: Optional[Dict] = None
    ) -> Tuple[BaseAgent, float]:
        """Enhanced agent selection with transition management"""
        try:
            logger.info(f"Processing query for agent selection: {query[:100]}...")
            state = state or {}
            
            # First check if we should transition from current agent
            if current_agent_type:
                should_transition, reason = await self._should_transition_agent(
                    query, 
                    current_agent_type, 
                    state
                )
                
                if not should_transition:
                    confidence = self._calculate_confidence(query, current_agent_type)
                    logger.info(
                        f"Maintaining current agent {current_agent_type} "
                        f"(confidence: {confidence:.2f}, reason: {reason})"
                    )
                    return self.agents[current_agent_type], confidence
            
            # Determine new agent type and confidence
            agent_type, confidence = self._determine_agent_with_confidence(query)
            
            # Log selection decision
            logger.info(
                f"Selected agent: {agent_type} with confidence: {confidence:.2f}\n"
                f"Previous agent: {current_agent_type or 'None'}"
            )
            
            # Record transition if agent changed
            if current_agent_type and agent_type != current_agent_type:
                self._add_transition(state, current_agent_type, agent_type, confidence)
            
            # Create agent if not exists
            if agent_type not in self.agents:
                logger.info(f"Creating new agent of type: {agent_type}")
                self.agents[agent_type] = self.create_agent(agent_type, session_id or "global")
            
            return self.agents[agent_type], confidence
            
        except Exception as e:
            logger.error(f"Error in agent selection: {str(e)}", exc_info=True)
            # Fallback to general agent
            logger.info("Falling back to general agent due to error")
            return self.agents['general'], 0.3

    async def _should_transition_agent(self, query: str, current_agent_type: str, state: Dict) -> Tuple[bool, str]:
        """Enhanced transition decision logic with detailed reasoning"""
        try:
            # Check transition frequency
            if self._is_transition_rate_exceeded(state):
                return False, "Maximum transition rate exceeded"
            
            # Check transition cooldown
            if self._is_in_cooldown(state):
                return False, "In transition cooldown period"
            
            # Get new agent confidence
            new_agent_type, new_confidence = self._determine_agent_with_confidence(query)
            if new_agent_type == current_agent_type:
                return False, "Same agent type determined"
            
            # Calculate current agent confidence
            current_confidence = self._calculate_confidence(query, current_agent_type)
            
            # Check if new agent has significantly higher confidence
            if new_confidence > current_confidence + self.config.CONFIDENCE_BOOST_THRESHOLD:
                logger.info(
                    f"Agent transition approved:\n"
                    f"Current agent ({current_agent_type}): {current_confidence:.2f}\n"
                    f"New agent ({new_agent_type}): {new_confidence:.2f}"
                )
                return True, f"New agent has higher confidence (+{new_confidence - current_confidence:.2f})"
            
            # Check if current agent has completed its task
            if self._is_task_complete(current_agent_type, state):
                return True, "Current agent task completed"
            
            return False, "Insufficient confidence difference for transition"
            
        except Exception as e:
            logger.error(f"Error in transition decision: {str(e)}", exc_info=True)
            return False, f"Error in transition logic: {str(e)}"

    def _determine_agent_with_confidence(self, query: str) -> Tuple[str, float]:
        """Determine the most appropriate agent type and confidence score"""
        query = query.lower()
        
        # Check emergency queries first (highest priority)
        if any(term in query for term in ['emergency', 'choking', 'breathing', 'accident', 'hurt', 'injury', 'danger']):
            return AgentTypes.EMERGENCY, 1.0
        
        # Calculate confidence for each agent type
        agent_confidences = {
            AgentTypes.MENTAL_HEALTH: self._calculate_mental_health_confidence(query),
            AgentTypes.BABY_GEAR: self._calculate_baby_gear_confidence(query),
            AgentTypes.SLEEP: self._calculate_sleep_confidence(query),
            AgentTypes.FEEDING: self._calculate_feeding_confidence(query),
            AgentTypes.DEVELOPMENT: self._calculate_development_confidence(query),
            AgentTypes.GENERAL: 0.3  # Base confidence for general agent
        }
        
        # Get agent type with highest confidence
        agent_type = max(agent_confidences.items(), key=lambda x: x[1])[0]
        confidence = agent_confidences[agent_type]
        
        return agent_type, confidence

    def _calculate_mental_health_confidence(self, query: str) -> float:
        """Calculate confidence for mental health related queries"""
        mental_health_terms = {
            'depression', 'anxiety', 'stress', 'mood', 'emotional', 'feeling',
            'mental', 'therapy', 'postpartum', 'baby blues', 'sad', 'crying',
            'overwhelmed', 'lonely', 'isolated'
        }
        return self._calculate_term_matches(query, mental_health_terms)

    def _calculate_baby_gear_confidence(self, query: str) -> float:
        """Calculate confidence for baby gear related queries"""
        gear_terms = {
            'stroller', 'crib', 'car seat', 'gear', 'buy', 'product',
            'bottle', 'diaper', 'carrier', 'swing', 'monitor'
        }
        return self._calculate_term_matches(query, gear_terms)

    def _calculate_sleep_confidence(self, query: str) -> float:
        """Calculate confidence for sleep related queries"""
        return self._calculate_term_matches(query, self.field_detector.SLEEP_INDICATORS)

    def _calculate_feeding_confidence(self, query: str) -> float:
        """Calculate confidence for feeding related queries"""
        return self._calculate_term_matches(query, self.field_detector.FEEDING_INDICATORS)

    def _calculate_development_confidence(self, query: str) -> float:
        """Calculate confidence for development related queries"""
        return self._calculate_term_matches(query, self.field_detector.DEVELOPMENT_INDICATORS)

    def _calculate_term_matches(self, query: str, terms: set) -> float:
        """Calculate confidence based on term matches"""
        matches = sum(1 for term in terms if term in query)
        base_confidence = min(matches / max(len(terms) * 0.3, 1), 1.0)  # Adjusted to require fewer matches
        # Boost confidence if multiple matches found
        return base_confidence * (1 + 0.1 * matches) if matches > 1 else base_confidence

    def _is_task_complete(self, agent_type: str, state: Dict) -> bool:
        """Check if the current agent has completed its task"""
        # Check if all required fields are gathered
        required_fields = self._get_required_fields(agent_type)
        gathered_info = state.get('gathered_info', {})
        return all(field in gathered_info for field in required_fields)

    def _get_required_fields(self, agent_type: str) -> List[str]:
        """Get required fields for an agent type"""
        from src.constants import RequiredFields
        return RequiredFields.BY_AGENT.get(agent_type, [])

    def _calculate_confidence(self, query: str, agent_type: str) -> float:
        """Calculate confidence for an agent handling this query"""
        query_lower = query.lower()
        keywords = self.agent_keywords.get(agent_type, [])
        matches = sum(1 for keyword in keywords if keyword in query_lower)
        return min(matches / max(len(keywords), 1), 1.0)

    def calculate_confidence(self, query: str, expertise: List[str]) -> float:
        query_lower = query.lower()
        matches = sum(1 for keyword in expertise if keyword.lower() in query_lower)
        return min(matches / len(expertise), 1.0)

    def determine_query_type(self, query: str) -> str:
        query_lower = query.lower()
        if 'twins' in query_lower and 'stroller' in query_lower:
            return 'twin_stroller'
        elif 'stroller' in query_lower:
            return 'stroller'
        return 'general'

    def create_agent(self, agent_type: AgentTypes, session_id: str) -> BaseAgent:
        """Create a new agent instance."""
        try:
            # Convert string to enum if needed
            if isinstance(agent_type, str):
                try:
                    agent_type = AgentTypes(agent_type)
                except ValueError:
                    logger.error(f"Unknown agent type string: {agent_type}")
                    return self.agents.get('general')  # Fallback to general agent
            
            agent_class = self.agent_registry.get(agent_type)
            if not agent_class:
                logger.error(f"Unknown agent type: {agent_type}")
                return self.agents.get('general')  # Fallback to general agent
                
            # Create agent with proper agent_type
            agent = agent_class(
                agent_type=agent_type,  # Pass the enum directly
                name=f"{agent_type.value}_{session_id}",
                llm_service=self.llm_service
            )
            
            logger.info(f"Created agent: {agent_type} for session {session_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _get_agent_name(self, agent_type: str) -> str:
        """Get the display name for an agent type."""
        agent_names = {
            AgentTypes.GENERAL: "General Baby Care Guide",
            AgentTypes.SLEEP: "Sleep & Rest Specialist",
            AgentTypes.HEALTH: "Baby Health Specialist",
            AgentTypes.DEVELOPMENT: "Child Development & Milestones Specialist",
            AgentTypes.FEEDING: "Feeding & Nutrition Specialist",
            AgentTypes.BABY_GEAR: "Baby Gear & Equipment Specialist",
            AgentTypes.TRAVEL: "Travel & Adventure Guide",
            AgentTypes.PREGNANCY: "Pregnancy & Birth Specialist"
        }
        return agent_names.get(agent_type, "Baby Care Assistant")

    def determine_agent_type(self, query: str) -> str:
        """Determine which agent should handle the query based on content analysis"""
        query_lower = query.lower()
        
        # Budget-related keywords - check first as it's a higher-level concern
        budget_terms = [
            'budget', 'cost', 'price', 'money', 'expense',
            'spend', 'financial', 'afford', 'cheap', 'expensive',
            'תקציב', 'עלות', 'כסף', 'מחיר', 'הוצאה'
        ]
        if any(term in query_lower for term in budget_terms):
            # Check if this is primarily a budget query
            budget_focus_terms = ['plan', 'planning', 'manage', 'monthly', 'allocate', 'תכנון', 'חודשי']
            if any(term in query_lower for term in budget_focus_terms):
                return AgentTypes.BUDGET
        
        # Travel-related keywords
        travel_terms = [
            'travel', 'trip', 'flight', 'fly', 'plane', 'airport',
            'vacation', 'visit', 'journey', 'destination'
        ]
        if any(term in query_lower for term in travel_terms):
            return AgentTypes.TRAVEL
        
        # Pregnancy-related keywords
        pregnancy_terms = [
            'pregnant', 'pregnancy', 'trimester', 'weeks',
            'morning sickness', 'ultrasound', 'prenatal'
        ]
        if any(term in query_lower for term in pregnancy_terms):
            return AgentTypes.PREGNANCY
        
        # Baby gear keywords - check for specific product queries
        if any(word in query_lower for word in [
            'stroller', 'car seat', 'crib', 'carrier', 'toy', 'diaper',
            'bottle', 'monitor', 'gear', 'equipment', 'product',
            'עגלה', 'סלקל', 'מיטה', 'מנשא', 'ציוד', 'מוצר'
        ]):
            # If budget terms are present but not planning-focused, treat as gear query
            if any(term in query_lower for term in budget_terms):
                return AgentTypes.BABY_GEAR
            return AgentTypes.BABY_GEAR
        
        # Sleep-related keywords
        if any(word in query_lower for word in [
            'sleep', 'nap', 'bedtime', 'night', 'routine', 'schedule',
            'tired', 'rest', 'שינה', 'לילה', 'שעות'
        ]):
            return AgentTypes.SLEEP
        
        # Feeding-related keywords
        if any(word in query_lower for word in [
            'feed', 'eat', 'milk', 'formula', 'breast', 'bottle', 'solid',
            'hunger', 'food', 'האכלה', 'הנקה', 'אוכל', 'בקבוק'
        ]):
            return AgentTypes.FEEDING
        
        # Health-related keywords
        if any(word in query_lower for word in [
            'sick', 'fever', 'doctor', 'medicine', 'symptom', 'pain',
            'health', 'vaccine', 'חום', 'חולה', 'רופא', 'תרופה'
        ]):
            return AgentTypes.HEALTH
        
        # Development-related keywords
        if any(word in query_lower for word in [
            'milestone', 'develop', 'growth', 'skill', 'learn', 'crawl',
            'walk', 'talk', 'התפתחות', 'גדילה', 'אבני דרך'
        ]):
            return AgentTypes.DEVELOPMENT
        
        # Mental health and support keywords
        if any(word in query_lower for word in [
            'stress', 'anxiety', 'depression', 'overwhelm', 'support',
            'cope', 'feel', 'לחץ', 'חרדה', 'תמיכה'
        ]):
            return AgentTypes.MENTAL_HEALTH
        
        # Default to general agent if no specific match
        return AgentTypes.GENERAL

    async def route_query(self, query: str, session_id: str) -> Dict[str, Any]:
        """Route a query to the appropriate agent and get response"""
        try:
            # Get memory components
            memory_components = await get_or_create_memory(session_id)
            
            # Create state
            state = BabywiseState(
                messages=[],  # Will be populated from memory
                agent_type="general",  # Default agent type
                metadata={
                    "gathered_info": {},
                    "session_id": session_id
                }
            )
            
            # Get the appropriate agent
            agent, confidence = await self.get_agent_for_query(query, session_id)
            
            # Update state with agent type
            state["agent_type"] = agent.agent_type.value
            
            # Process query through agent
            result = await agent.invoke(state)
            
            # Return the result
            return {
                "type": "answer",
                "text": result["messages"][-1].content if result.get("messages") else "No response generated",
                "agent_type": agent.agent_type.value,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error routing query: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "text": "I encountered an error processing your request. Please try again.",
                "error": str(e)
            }

    def _extract_context_from_message(self, message: str) -> Dict[str, Any]:
        """Extract context from a single message"""
        gathered_info = {}
        content = message.lower()
        
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
        
        # Extract general topic
        topic_keywords = ['about', 'help with', 'advice on', 'question about']
        if any(keyword in content for keyword in topic_keywords):
            gathered_info["general_topic"] = content
        
        # Extract parenting style
        if any(word in content for word in ['style', 'approach', 'method', 'philosophy']):
            gathered_info["parenting_style"] = content
        
        # Extract daily routine
        if any(word in content for word in ['routine', 'schedule', 'daily', 'pattern']):
            gathered_info["daily_routine"] = content
        
        # Extract specific challenges
        if any(word in content for word in ['challenge', 'difficult', 'struggle', 'issue']):
            gathered_info["specific_challenges"] = content
        
        return gathered_info

    def _get_previous_agent(self, session_id: str) -> Optional[BaseAgent]:
        """Get the previous agent for a session"""
        return getattr(self, f'_previous_agent_{session_id}', None)
    
    def _store_agent(self, session_id: str, agent: BaseAgent):
        """Store the current agent for a session"""
        setattr(self, f'_previous_agent_{session_id}', agent) 