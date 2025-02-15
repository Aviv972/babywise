from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
from src.config import Config
from src.constants import ContextFields, MessageRoles, ResponseTypes, QuestionFields, RequiredFields, AgentTypes
import json

class LLMService:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.MODEL_NAME
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.system_prompt = """You are a parenting expert assistant.
            CRITICAL INSTRUCTIONS FOR CONTEXT MAINTENANCE:
            1. The original query is your PRIMARY FOCUS - never lose sight of it
            2. ALL follow-up questions and responses MUST directly relate to the original query
            3. Information gathering should be CUMULATIVE - maintain ALL previously gathered info
            4. When user provides new information:
               - Store it
               - Integrate it with existing context
               - Stay focused on the original topic
               - Do NOT switch topics unless explicitly requested
            5. Context Rules:
               - Always reference the original query in your responses
               - Each response should build upon previous information
               - Validate that new questions relate to the original goal
               
            Examples of Correct Context Maintenance:
            
            Example 1 - Stroller Query:
            Original: "What stroller for twins?"
            User: "they are 1 year old"
            ✓ CORRECT: "For 1-year-old twins, what's your preferred stroller style (side-by-side or tandem)?"
            ✗ WRONG: "Let's discuss developmental milestones for 1-year-olds"
            
            Example 2 - Sleep Training:
            Original: "How to sleep train 6-month twins?"
            User: "they currently wake up 5 times a night"
            ✓ CORRECT: "Given they wake 5 times nightly, what sleep training method interests you for your 6-month twins?"
            ✗ WRONG: "Let's discuss night feeding schedules"
            
            Example 3 - Feeding Schedule:
            Original: "What's a good feeding schedule for twins?"
            User: "they're exclusively breastfed"
            ✓ CORRECT: "For breastfed twins, how often are you currently feeding them?"
            ✗ WRONG: "Let's discuss breastfeeding positions"
            
            Keep responses:
            1. Focused on original query
            2. Building on gathered context
            3. Specific and actionable
            4. Structured and clear."""

    def merge_context(self, original_query: str, gathered_info: Dict, current_query: str) -> str:
        return f"""Original Query: {original_query}
        
        Clarifications collected so far:
        {json.dumps(gathered_info, indent=2)}
        
        Current Input: "{current_query}"
        """

    async def generate_response(self, prompt: str, chat_history: List[Dict] = None) -> Dict:
        try:
            messages = [
                {"role": MessageRoles.SYSTEM, "content": self.system_prompt}
            ]
            
            if chat_history:
                messages.extend([
                    {
                        "role": msg['role'],
                        "content": msg['content']
                    }
                    for msg in chat_history[-10:]
                ])

            messages.append({"role": MessageRoles.USER, "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            return {
                "type": ResponseTypes.ANSWER,
                "text": str(response.choices[0].message.content),
                "role": MessageRoles.MODEL
            }

        except Exception as e:
            print(f"Error in LLMService: {str(e)}")
            return {
                "type": ResponseTypes.ERROR,
                "text": "Error connecting to LLM service",
                "role": MessageRoles.MODEL
            }

    def _prepare_prompt(self, prompt: str, context: Dict) -> str:
        if not context or not context.get('context_gathered'):
            return prompt

        context_str = "\n".join([
            f"{key}: {value}" 
            for key, value in context.get('context_gathered', {}).items()
        ])

        return f"""Based on this context:
                  {context_str}
                  
                  Query: {prompt}
                  
                  Provide a concise, specific response that:
                  1. Addresses the exact question
                  2. Uses the provided context
                  3. Gives clear recommendations
                  Keep it brief and focused."""

    def _build_context_reminder(self, context: Dict) -> str:
        """Build a context reminder to keep the conversation focused"""
        original_query = context.get(ContextFields.ORIGINAL_QUERY, '')
        query_type = context.get(ContextFields.QUERY_TYPE, '')
        agent_type = context.get(ContextFields.CURRENT_AGENT, '')
        gathered_info = context.get(ContextFields.GATHERED_INFO, {})
        
        return f"""MAINTAIN FOCUS ON ORIGINAL QUERY: {original_query}
        Current topic: {query_type}
        Agent type: {agent_type}
        Information gathered so far: {json.dumps(gathered_info, indent=2)}
        
        DO NOT LOSE THIS CONTEXT IN YOUR RESPONSE.
        NEXT QUESTIONS MUST RELATE TO THE ORIGINAL QUERY."""

    async def analyze_query_intent(self, query: str, context: Dict, chat_history: List[Dict] = None) -> Dict:
        gathered_info = context[ContextFields.GATHERED_INFO]
        original_query = context[ContextFields.ORIGINAL_QUERY]
        
        # Format chat history for better context
        formatted_history = ""
        if chat_history:
            formatted_history = "\nPrevious conversation:\n"
            for msg in chat_history[-5:]:
                role = "User" if msg['role'] == MessageRoles.USER else "Assistant"
                formatted_history += f"{role}: {msg['content']}\n"
        
        # Build stroller-specific context-aware prompt
        prompt = f"""STROLLER RECOMMENDATION TASK:

Original Query: {original_query}
{formatted_history}
Current User Input: "{query}"

Information gathered so far:
{json.dumps(gathered_info, indent=2)}

Based on the ORIGINAL QUERY about finding a stroller and the current conversation:
1. Extract any new information about:
   - Budget (e.g., numbers with $ or price mentions)
   - Preferences (e.g., lightweight, easy transport)
   - Use case (e.g., travel, daily walks)
   - Baby's age/weight
2. Generate a specific follow-up question about missing stroller details

Return JSON:
{{
    "extracted_info": [
        {{
            "field": "budget",
            "value": "under $400"  # Example
        }},
        {{
            "field": "preferences",
            "value": "lightweight, easy transport"  # Example
        }}
    ],
    "next_question": {{
        "field": "stroller_features",
        "question": "specific_stroller_related_question"
    }}
}}

IMPORTANT: 
- Every question MUST be about stroller features, usage, or requirements
- Use previously gathered information to make questions specific
- If budget is known, ask about features within that budget
- If preferences are known, ask about specific stroller features matching those preferences"""

        response = await self.generate_response(prompt, chat_history)
        try:
            parsed = json.loads(response['text'])
            
            # Store any extracted information
            if parsed.get('extracted_info'):
                for info in parsed['extracted_info']:
                    gathered_info[info['field']] = info['value']
                    print(f"Stored information - Field: {info['field']}, Value: {info['value']}")
            
            # Ensure the next question is stroller-specific and builds on gathered info
            if parsed.get('next_question'):
                question = parsed['next_question']['question']
                budget = gathered_info.get('budget', '')
                preferences = gathered_info.get('preferences', '')
                
                # Make question more specific based on gathered info
                if budget and preferences:
                    question = f"For a {preferences} stroller {budget}, what specific features are most important to you (e.g., folding mechanism, storage capacity, wheel type)?"
                elif budget:
                    question = f"Within {budget}, what specific stroller features are most important to you?"
                elif preferences:
                    question = f"For a {preferences} stroller, what other features do you need?"
                
                parsed['next_question']['question'] = question
            
            return parsed
        except json.JSONDecodeError:
            # Fallback to a stroller-specific question
            return {
                "extracted_info": [],
                "next_question": {
                    "field": "stroller_requirements",
                    "question": "What specific stroller features are most important to you (e.g., weight, folding, storage space)?"
                }
            }

    def _extract_budget_info(self, query: str) -> Optional[str]:
        """Extract budget information from query"""
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() in ['under', 'below', 'within']:
                if i + 1 < len(words):
                    amount = words[i + 1].replace('$', '').replace(',', '')
                    if amount.isdigit():
                        return f"Under ${amount}"
        return None

    def _extract_preferences(self, query: str) -> List[str]:
        """Extract user preferences from query"""
        preference_keywords = {
            'lightweight': ['lightweight', 'light', 'portable'],
            'durable': ['durable', 'sturdy', 'strong'],
            'compact': ['compact', 'small', 'foldable'],
            'storage': ['storage', 'space', 'capacity']
        }
        
        found_preferences = []
        query_lower = query.lower()
        
        for pref, keywords in preference_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                found_preferences.append(pref)
                
        return found_preferences

    def _is_stroller_specific(self, question: str) -> bool:
        """Verify question is specifically about strollers"""
        stroller_terms = ['stroller', 'wheels', 'fold', 'push', 'recline', 'storage']
        return any(term in question.lower() for term in stroller_terms)

    def _generate_stroller_followup(self, gathered_info: Dict) -> Dict:
        """Generate a stroller-specific follow-up question"""
        budget = gathered_info.get('budget', '')
        preferences = gathered_info.get('preferences', [])
        
        if budget and preferences:
            return {
                "field": "stroller_features",
                "question": f"For a {', '.join(preferences)} stroller within {budget}, what additional features are most important (e.g., recline positions, storage capacity, wheel type)?"
            }
        elif budget:
            return {
                "field": "stroller_type",
                "question": f"Within {budget}, what type of stroller are you looking for (e.g., lightweight, travel system, jogging stroller)?"
            }
        elif preferences:
            return {
                "field": "budget",
                "question": f"For a {', '.join(preferences)} stroller, what is your budget range?"
            }
        else:
            return {
                "field": "stroller_requirements",
                "question": "What are your most important requirements for the stroller (e.g., weight, folding, storage space)?"
            }

    async def generate_final_response(self, context: Dict, chat_history: List[Dict] = None) -> Dict:
        gathered_info = context[ContextFields.GATHERED_INFO]
        original_query = context[ContextFields.ORIGINAL_QUERY]
        query_type = context.get(ContextFields.QUERY_TYPE, '')
        agent_type = context.get(ContextFields.CURRENT_AGENT, '')
        
        context_reminder = self._build_context_reminder(context)
        
        # Build a dynamic prompt based on agent type
        prompt_parts = [
            context_reminder,
            "\nBased on ALL the above information, provide a detailed response that addresses the ORIGINAL QUERY:",
            original_query
        ]
        
        # Add relevant criteria based on gathered information
        prompt_parts.append("\nConsider all gathered information:")
        for field, value in gathered_info.items():
            if field in RequiredFields.QUESTIONS:
                prompt_parts.append(f"- {field}: {value}")
        
        # Add response format based on agent type
        if agent_type == AgentTypes.BABY_GEAR:
            prompt_parts.extend([
                "\nFormat your response as:",
                "1. Top Recommendation: [Product with price]",
                "2. Why this matches their needs: [2-3 bullet points]",
                "3. Alternative Option: [Second choice with price]",
                "\nEnsure recommendations match ALL gathered information."
            ])
        elif agent_type in [AgentTypes.SLEEP_ROUTINE, AgentTypes.FEEDING]:
            prompt_parts.extend([
                "\nFormat your response as:",
                "1. Recommended Approach: [Main recommendation]",
                "2. Key Benefits: [2-3 bullet points]",
                "3. Implementation Tips: [2-3 practical steps]",
                "\nEnsure advice considers ALL gathered information."
            ])
        else:
            prompt_parts.extend([
                "\nProvide a clear, structured response that:",
                "1. Directly addresses their original query",
                "2. Uses ALL gathered information",
                "3. Gives actionable recommendations"
            ])
        
        # Add final reminder to stay on topic
        prompt_parts.append(f"\nIMPORTANT: Your response must directly answer: {original_query}")
        
        prompt = "\n".join(prompt_parts)
        response = await self.generate_response(prompt, chat_history)
        
        # Validate the response maintains context
        relevance_check = await self.calculate_context_relevance(
            response['text'],
            original_query
        )
        
        if relevance_check < 0.7:  # If response isn't relevant enough
            # Add stronger context reminder and try again
            prompt = f"""CRITICAL: Your previous response lost context of the original query.
            
            {prompt}
            
            YOU MUST STAY FOCUSED ON THE ORIGINAL QUERY: {original_query}
            DO NOT PROVIDE GENERAL ADVICE - BE SPECIFIC TO THE QUERY."""
            
            response = await self.generate_response(prompt, chat_history)
        
        return {
            'type': ResponseTypes.ANSWER,
            'text': response['text'],
            'role': MessageRoles.MODEL
        }

    async def check_topic_similarity(self, query: str, current_topic: str) -> float:
        """Check if query is related to current topic"""
        prompt = f"""Compare this query: "{query}"
        To this topic: "{current_topic}"
        
        Return a similarity score between 0.0 and 1.0, where:
        0.0 = completely unrelated
        1.0 = exactly the same topic
        
        Return only the number."""

        response = await self.generate_response(prompt)
        try:
            return float(response['text'].strip())
        except:
            return 0.0

    async def is_followup_question(self, query: str, context: Dict) -> bool:
        """Determine if this is a follow-up question"""
        prompt = f"""Original topic: {context[ContextFields.QUERY_TYPE]}
        Previous messages: {json.dumps(context[ContextFields.GATHERED_INFO])}
        Current query: "{query}"
        
        Is this a follow-up question to the previous conversation?
        Consider:
        1. References to previous products/recommendations
        2. Follow-up indicators like "what about", "how about", "and"
        3. Questions about details of previous responses
        
        Return only "yes" or "no"."""

        response = await self.generate_response(prompt)
        return response['text'].strip().lower() == 'yes'

    async def extract_product_names(self, text: str) -> List[str]:
        """Extract product names from text"""
        prompt = f"""From this text: "{text}"
        Extract all product names (brand names, model names, etc.)
        Return as JSON array of strings.
        Example: ["Graco 4Ever", "Chicco KeyFit 30"]"""

        response = await self.generate_response(prompt)
        try:
            return json.loads(response['text'])
        except:
            return []

    async def calculate_context_relevance(self, query: str, context: str) -> float:
        prompt = f"""Compare this query: "{query}" with context: "{context}"
        Return similarity score (0.0-1.0)"""
        response = await self.generate_response(prompt)
        try:
            return float(response['text'].strip())
        except:
            return 0.0

    async def prepare_prompt(self, query: str, context: Dict) -> str:
        prompt = f"""Original Query: {context[ContextFields.ORIGINAL_QUERY]}
        Context: {json.dumps(context[ContextFields.GATHERED_INFO])}
        Current Query: {query}"""
        return prompt

    async def format_context(self, gathered_info: Dict) -> str:
        return "\n".join([f"- {k}: {v}" for k, v in gathered_info.items()])

    async def get_missing_context(self, query: str, context: Dict) -> List[str]:
        prompt = self.merge_context(
            original_query=context[ContextFields.ORIGINAL_QUERY],
            gathered_info=context[ContextFields.GATHERED_INFO],
            current_query=query
        )
        prompt += "\nWhat information is still needed? Return as JSON array of missing fields."
        
        response = await self.generate_response(prompt)
        try:
            return json.loads(response['text'])
        except:
            return []

    async def generate_context_question(self, field: str) -> str:
        questions = {
            QuestionFields.BUDGET: 'What is your budget range?',
            QuestionFields.FEATURES: 'What features are most important to you?',
            QuestionFields.USAGE: 'How will you mainly use this?'
        }
        return questions.get(field, f"Please provide information about {field}")

    async def meets_requirement(self, response: str, requirement: str) -> bool:
        prompt = f"""Check if response meets: {requirement}
        Response: {response}
        Return only 'yes' or 'no'"""
        result = await self.generate_response(prompt)
        return result['text'].strip().lower() == 'yes'

    async def generate_constrained_response(self, query: str, constraints: List[str]) -> Dict:
        prompt = f"""Query: {query}
        Must follow constraints: {json.dumps(constraints)}"""
        return await self.generate_response(prompt)

    async def analyze_query_needs(self, query: str, context: Dict) -> List[str]:
        prompt = f"""What info is needed for: {query}
        Current context: {json.dumps(context)}
        Return as JSON array of needed fields."""
        response = await self.generate_response(prompt)
        try:
            return json.loads(response['text'])
        except:
            return [] 