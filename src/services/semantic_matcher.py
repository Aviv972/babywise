from typing import Dict, List, Optional, Tuple
from src.constants import BaseFields, DynamicFieldDetector, AgentTypes, QuestionFields
from src.services.llm_service import LLMService

class SemanticMatcher:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

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