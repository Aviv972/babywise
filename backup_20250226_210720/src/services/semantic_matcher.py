from typing import Dict, List, Optional, Tuple
from src.constants import BaseFields, DynamicFieldDetector, AgentTypes, QuestionFields
from src.services.llm_service import LLMService
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SemanticMatcher:
    def __init__(self, model):
        self.model = model
        self.embeddings = OpenAIEmbeddings()
        self.agent_descriptions = self._initialize_agent_descriptions()
        self.vector_store = self._create_vector_store()
        logger.info("Initialized semantic matcher with agent descriptions")

    def _initialize_agent_descriptions(self) -> Dict[str, str]:
        """Initialize agent descriptions for semantic matching"""
        return {
            AgentTypes.SLEEP_TRAINING: """Expert in baby sleep training, schedules, and routines.
                Handles queries about naps, bedtime, night wakings, and sleep transitions.""",
                
            AgentTypes.FEEDING: """Specialist in baby feeding and nutrition.
                Handles queries about breastfeeding, formula, solids, feeding schedules, and nutrition.""",
                
            AgentTypes.MEDICAL_HEALTH: """Medical health advisor for common baby conditions.
                Handles queries about symptoms, illnesses, vaccinations, and general health concerns.""",
                
            AgentTypes.DEVELOPMENT: """Child development specialist.
                Handles queries about milestones, growth, skills, and developmental stages.""",
                
            AgentTypes.BABY_GEAR: """Baby product and gear specialist.
                Handles queries about strollers, car seats, cribs, toys, and other baby equipment.""",
                
            AgentTypes.MENTAL_HEALTH: """Mental health and emotional support specialist.
                Handles queries about parental stress, anxiety, depression, and emotional well-being.""",
                
            AgentTypes.GENERAL: """General baby care assistant.
                Handles broad queries and can route to specialized agents when needed."""
        }

    def _create_vector_store(self) -> FAISS:
        """Create FAISS vector store with agent descriptions"""
        texts = list(self.agent_descriptions.values())
        metadatas = [{"agent_type": agent_type} for agent_type in self.agent_descriptions.keys()]
        
        return FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )

    async def find_best_agent(self, query: str, threshold: float = 0.7) -> Tuple[str, float]:
        """Find the best agent for a query using semantic similarity"""
        try:
            # Get similar documents
            docs = self.vector_store.similarity_search_with_score(query, k=2)
            
            if not docs:
                logger.info(f"No matching agent found for query: {query}")
                return AgentTypes.GENERAL, 0.0
            
            # Get best match
            best_match, score = docs[0]
            agent_type = best_match.metadata["agent_type"]
            
            # Convert score to similarity (FAISS returns distance)
            similarity = 1.0 - min(score, 1.0)
            
            logger.info(f"Best matching agent: {agent_type} with similarity: {similarity:.2f}")
            
            # Return general agent if similarity is below threshold
            if similarity < threshold:
                logger.info(f"Similarity below threshold, using general agent")
                return AgentTypes.GENERAL, similarity
            
            return agent_type, similarity
            
        except Exception as e:
            logger.error(f"Error finding best agent: {str(e)}", exc_info=True)
            return AgentTypes.GENERAL, 0.0

    async def get_agent_confidence(self, query: str, agent_type: str) -> float:
        """Get confidence score for a specific agent type"""
        try:
            # Get agent description
            description = self.agent_descriptions.get(agent_type)
            if not description:
                return 0.0
            
            # Calculate similarity between query and agent description
            query_embedding = await self.embeddings.aembed_query(query)
            desc_embedding = await self.embeddings.aembed_query(description)
            
            similarity = np.dot(query_embedding, desc_embedding)
            
            logger.debug(f"Confidence for {agent_type}: {similarity:.2f}")
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating agent confidence: {str(e)}", exc_info=True)
            return 0.0

    async def should_transition(self, query: str, current_agent: str, threshold: float = 0.3) -> Tuple[bool, str]:
        """Determine if we should transition to a different agent"""
        try:
            # Find best matching agent
            best_agent, similarity = await self.find_best_agent(query)
            
            # If best agent is different and similarity is above threshold
            if best_agent != current_agent and similarity > threshold:
                logger.info(f"Suggesting transition from {current_agent} to {best_agent}")
                return True, best_agent
            
            return False, current_agent
            
        except Exception as e:
            logger.error(f"Error in transition decision: {str(e)}", exc_info=True)
            return False, current_agent

    def _format_context_for_prompt(self, context: Dict) -> str:
        """Format context information for inclusion in prompts"""
        parts = []
        if context.get('original_query'):
            parts.append(f"Original Query: {context['original_query']}")
        if context.get('agent_type'):
            parts.append(f"Query Type: {context['agent_type']}")
        if context.get('gathered_info'):
            parts.append("Information Gathered:")
            for field, value in context['gathered_info'].items():
                parts.append(f"- {field}: {value}")
        return "\n".join(parts)

    async def extract_fields(self, query: str, context: Dict = None) -> List[Tuple[str, float]]:
        """
        Extract relevant fields from a query using semantic similarity.
        Now considers existing context.
        """
        context_str = self._format_context_for_prompt(context) if context else ""
        prompt = f"""Context:
        {context_str}
        
        New Query: "{query}"
        
        Considering the FULL CONTEXT ABOVE, identify information being asked about or provided.
        Focus on NEW information while maintaining awareness of what we already know.
        
        Consider these aspects:
        1. Time-related (when, how often, duration)
        2. Quantity-related (how much, how many)
        3. Preference-related (likes, wants, needs)
        4. Constraint-related (limitations, requirements)
        5. Specific details about previously discussed topics
        
        Return a JSON array of objects with 'field_type' and 'confidence':
        [
            {{"field_type": "temporal", "confidence": 0.9}},
            {{"field_type": "preference", "confidence": 0.7}}
        ]
        """
        
        try:
            response = await self.llm.generate_response(prompt)
            fields = response.get('text', '[]')
            return [(f['field_type'], f['confidence']) for f in eval(fields)]
        except:
            # Fallback to basic detection if LLM fails
            basic_type = DynamicFieldDetector.extract_field_type(query)
            return [(basic_type, 1.0)]

    async def extract_value(self, query: str, field_type: str, context: Dict = None) -> Optional[str]:
        """Extract the value for a specific field type from the query, considering context"""
        context_str = self._format_context_for_prompt(context) if context else ""
        prompt = f"""Context:
        {context_str}
        
        New Query: "{query}"
        Field Type: {field_type}
        
        Extract the value related to this field type, considering the full context above.
        If the value builds on previous information, include that context in your interpretation.
        
        Consider:
        1. Numbers and quantities
        2. Time expressions
        3. Preferences and choices
        4. How this new information relates to what we already know
        
        Return only the extracted value, or "null" if no relevant value found.
        """
        
        try:
            response = await self.llm.generate_response(prompt)
            value = response.get('text', '').strip()
            return None if value.lower() == 'null' else value
        except:
            return None

    async def determine_missing_fields(self, agent_type: str, context: Dict) -> List[str]:
        """Determine what fields are still needed based on context"""
        context_str = self._format_context_for_prompt(context)
        prompt = f"""Context:
        {context_str}
        Agent Type: {agent_type}
        
        What essential information is still missing to provide a complete response?
        Consider:
        1. What we already know from the context
        2. Required fields for this type of query
        3. Safety and practical requirements
        4. Logical next questions based on previous answers
        
        For example, if we know this is about a twin stroller and have a budget,
        we might need to know about:
        - Preferred style (side-by-side vs tandem)
        - Storage needs
        - Usage terrain
        
        Return a JSON array of missing field types.
        """
        
        try:
            response = await self.llm.generate_response(prompt)
            return eval(response.get('text', '[]'))
        except:
            # Fallback to basic required fields
            from src.constants import AgentContext
            return AgentContext.get_required_base_fields(agent_type)

    async def should_ask_followup(self, query: str, context: Dict) -> Tuple[bool, Optional[str], str]:
        """
        Determine if a follow-up question is needed and what to ask about.
        Returns (should_ask, field_to_ask_about, suggested_question)
        """
        context_str = self._format_context_for_prompt(context)
        prompt = f"""Context:
        {context_str}
        
        New Query: "{query}"
        
        Determine if we need more information to provide a complete response.
        Consider:
        1. The original query and its context
        2. All information gathered so far
        3. Critical missing information
        4. Natural conversation flow
        
        For example, if this is about twin strollers and we have:
        - Age of twins
        - Budget
        We might need:
        - Preferred style
        - Usage patterns
        
        Return JSON:
        {{
            "needs_followup": true/false,
            "missing_field": "field_name_or_null",
            "suggested_question": "natural_language_question",
            "importance": 0.0-1.0
        }}
        """
        
        try:
            response = await self.llm.generate_response(prompt)
            result = eval(response.get('text', '{}'))
            if result.get('importance', 0) > 0.7:
                return (
                    result.get('needs_followup', False),
                    result.get('missing_field'),
                    result.get('suggested_question', '')
                )
            return False, None, ""
        except:
            return False, None, "" 