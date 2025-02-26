from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
from src.config import Config
from src.constants import ContextFields, MessageRoles, ResponseTypes, QuestionFields, RequiredFields, AgentTypes
import json
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import asyncio
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema.messages import BaseMessage

logger = logging.getLogger(__name__)

class LLMError(Exception):
    def __init__(self, error_type: str, message: str, details: Dict[str, Any] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)

class LLMService:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",  # GPT-4 Omnimind Mini
        temperature: float = 0.4,
        streaming: bool = False
    ):
        self.model = ChatOpenAI(
            openai_api_key=api_key,
            model_name=model,
            temperature=temperature,
            streaming=streaming,
            callbacks=[StreamingStdOutCallbackHandler()] if streaming else None
        )
        logger.info(f"Initialized LLM service with model: {model}")

    async def agenerate_response(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AIMessage:
        """Generate a response using the LLM with message-based input"""
        try:
            # Create message list starting with system prompt if provided
            final_messages = []
            if system_prompt:
                final_messages.append(SystemMessage(content=system_prompt))
            
            # Add context from memory if provided
            if context and "chat_history" in context:
                final_messages.extend(context["chat_history"])
            
            # Add the provided messages
            final_messages.extend(messages)
            
            # Generate response
            response = await self.model.ainvoke(final_messages)
            logger.debug(f"Generated response: {response.content[:100]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise

    async def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AIMessage:
        """Generate a response using the LLM"""
        try:
            messages = []
            
            # Add system message if provided
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            # Add context from memory if provided
            if context and "chat_history" in context:
                messages.extend(context["chat_history"])
            
            # Add the current prompt
            messages.append(HumanMessage(content=prompt))
            
            # Generate response
            response = await self.model.ainvoke(messages)
            logger.debug(f"Generated response: {response.content[:100]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}", exc_info=True)
            raise

    async def stream_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Stream a response using the LLM"""
        try:
            # Create streaming model instance
            streaming_model = ChatOpenAI(
                openai_api_key=self.model.openai_api_key,
                model_name=self.model.model_name,
                temperature=self.model.temperature,
                streaming=True
            )
            
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            if context and "chat_history" in context:
                messages.extend(context["chat_history"])
            messages.append(HumanMessage(content=prompt))
            
            async for chunk in streaming_model.astream(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}", exc_info=True)
            raise

    def validate_response(self, response: AIMessage) -> bool:
        """Validate that the response meets our requirements"""
        if not response or not response.content:
            return False
        if len(response.content.strip()) < 10:  # Arbitrary minimum length
            return False
        return True

    def _should_use_perplexity(self, prompt: str, context: Dict = None) -> bool:
        """Determine if we should use Perplexity API based on query content."""
        print("\n=== Perplexity Trigger Analysis ===")
        print(f"Analyzing query: {prompt}")
        
        if not context:
            print("❌ No context provided")
            return False

        # Comprehensive list of baby product types
        product_types = [
            # Transportation
            'stroller', 'twin_stroller', 'car_seat', 'baby_carrier', 'baby_wrap', 'travel_system',
            
            # Sleep and Nursery
            'crib', 'bassinet', 'cradle', 'co_sleeper', 'playpen', 'pack_n_play', 'baby_monitor',
            'crib_mattress', 'bedding', 'sleep_sack', 'swaddle', 'night_light', 'white_noise',
            
            # Feeding
            'breast_pump', 'bottle', 'bottle_warmer', 'sterilizer', 'nursing_pillow', 'high_chair',
            'booster_seat', 'feeding_set', 'sippy_cup', 'baby_food_maker',
            
            # Diapering
            'changing_table', 'diaper_pail', 'diaper_bag', 'wipe_warmer', 'diaper_caddy',
            
            # Bath and Grooming
            'baby_bathtub', 'bath_seat', 'grooming_kit', 'baby_towel', 'bath_toys',
            'baby_toiletries', 'bath_thermometer',
            
            # Safety
            'baby_gate', 'cabinet_lock', 'outlet_cover', 'corner_guard', 'baby_fence',
            'safety_harness', 'anti_tip_strap',
            
            # Play and Development
            'play_mat', 'activity_gym', 'bouncer', 'swing', 'jumper', 'walker',
            'activity_center', 'play_yard', 'educational_toys',
            
            # Clothing and Accessories
            'baby_clothes', 'shoes', 'mittens', 'bibs', 'burp_cloths', 'baby_blanket',
            
            # Health and Comfort
            'humidifier', 'air_purifier', 'thermometer', 'nasal_aspirator', 'medicine_dispenser',
            'teething_toys'
        ]

        # Check if this is a product recommendation query
        query_lower = prompt.lower()
        
        # Enhanced product type detection with specific categories
        product_categories = {
            'car_seat': ['car seat', 'carseat', 'car safety', 'infant seat', 'booster seat', 'convertible seat'],
            'stroller': ['stroller', 'pushchair', 'pram', 'buggy', 'travel system'],
            'carrier': ['carrier', 'baby wrap', 'sling', 'baby wearing'],
            'furniture': ['crib', 'bassinet', 'changing table', 'playpen']
        }
        
        # Determine specific product category
        product_category = None
        for category, keywords in product_categories.items():
            if any(keyword in query_lower for keyword in keywords):
                product_category = category
                break
                
        product_type_match = bool(product_category)
        print(f"Product type in query? {product_type_match} (Category: {product_category})")
        
        purchase_intent = any(word in query_lower for word in [
            'recommend', 'product', 'price', 'cost', 'buy', 'purchase',
            'brand', 'model', 'compare', 'versus', 'vs', 'best',
            'affordable', 'expensive', 'cheap', 'quality', 'review',
            'where to get', 'shop', 'store', 'online', 'retail'
        ])
        print(f"Purchase intent detected? {purchase_intent}")
        
        is_product_query = product_type_match or purchase_intent
        print(f"Final product query determination: {is_product_query}")

        # Check if we need real-time information
        has_budget = 'budget' in context.get('gathered_info', {})
        print(f"Has budget in context? {has_budget}")
        
        real_time_keywords = any(word in query_lower for word in [
            'latest', 'current', 'market', 'available', 'new',
            'price', 'cost', 'deal', 'sale', 'discount',
            'today', 'now', 'stock', 'inventory', 'shipping'
        ])
        print(f"Real-time keywords detected? {real_time_keywords}")
        
        needs_real_time = has_budget or real_time_keywords
        print(f"Needs real-time info? {needs_real_time}")

        should_use = is_product_query and needs_real_time
        print(f"\nFinal decision - Use Perplexity? {should_use}")
        
        if should_use:
            print("✅ Will attempt to use Perplexity API")
        else:
            print("❌ Will use OpenAI instead")
            print("Reason:", end=" ")
            if not is_product_query:
                print("Not a product query")
            elif not needs_real_time:
                print("No real-time information needed")

        # Store the product category in context if available
        if context and product_category:
            context['product_category'] = product_category

        return should_use

    def _prepare_messages(self, prompt: str, chat_history: List[Dict], context: Dict) -> List[Dict]:
        """Prepare messages with enhanced context handling"""
        self.logger.info("Preparing messages with context")
        
        # Start with system message
        messages = [SystemMessage(content=self.system_prompt)]
        
        # Add context if available
        if context:
            self.logger.debug("Adding context to messages")
            
            gathered_info = context.get("gathered_info", {})
            
            # Format age information if available
            age_info = gathered_info.get("baby_age", {})
            age_str = ""
            if isinstance(age_info, dict):
                age_str = age_info.get("original", "")
            elif isinstance(age_info, str):
                age_str = age_info
            elif age_info:  # Handle any other non-empty value
                age_str = str(age_info)
            
            # Create a strong context reminder
            context_str = f"""CRITICAL CONTEXT - YOU MUST USE THIS IN YOUR RESPONSE:
            Baby's Age: {age_str}
            Original Query: {context.get('original_query', 'Not provided')}
            
            Additional Context:
            {json.dumps(gathered_info, indent=2)}
            
            You MUST:
            1. Reference ALL context information above in your response
            2. Keep your response focused on the original query
            3. Ensure all advice is age-appropriate
            4. Maintain this context in follow-up questions
            5. Use the EXACT same language as the user's messages
            6. NEVER ask for information that has already been provided
            7. If multiple babies (twins/triplets) are mentioned, maintain that context"""
            
            messages.append(SystemMessage(content=context_str))
        
        # Convert chat history to LangChain message format
        if chat_history:
            self.logger.debug(f"Adding conversation history: {len(chat_history)} messages")
            for msg in chat_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
                elif msg["role"] == "system":
                    messages.append(SystemMessage(content=msg["content"]))
        
        # Add current prompt as HumanMessage
        messages.append(HumanMessage(content=prompt))
        
        return messages

    async def generate_final_response(self, context: Dict, chat_history: List[Dict] = None) -> Dict:
        gathered_info = context[ContextFields.GATHERED_INFO]
        original_query = context[ContextFields.ORIGINAL_QUERY]
        agent_type = context.get(ContextFields.AGENT_TYPE, AgentTypes.GENERAL)
        
        # Create a strong context reminder
        context_reminder = []
        if 'baby_age' in gathered_info:
            context_reminder.append(f"Baby's Age: {gathered_info['baby_age']}")
        if agent_type == AgentTypes.FEEDING:
            context_reminder.append("Topic: Feeding recommendations")
            if 'feeding_type' in gathered_info:
                context_reminder.append(f"Current Feeding: {gathered_info['feeding_type']}")
        
        # Build the prompt with strong context
        prompt_parts = [
            f"Original Query: {original_query}",
            "Important Context:",
            *context_reminder,
            "\nYou MUST use ALL the context above in your response.",
            "Your response should be specific to the baby's age and directly address feeding."
        ]
        
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
                "1. Age-Appropriate Recommendations: [Main recommendation]",
                "2. Key Benefits: [2-3 bullet points]",
                "3. Implementation Tips: [2-3 practical steps]",
                "\nEnsure advice considers the baby's exact age and feeding context."
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
            response.content,
            original_query
        )
        
        if relevance_check < 0.7 or not any(reminder.lower() in response.content.lower() for reminder in context_reminder):
            # Add stronger context reminder and try again
            prompt = f"""CRITICAL: Your previous response lost context.
            
            {prompt}
            
            YOU MUST:
            1. Keep focus on the original query: {original_query}
            2. Include the baby's age: {gathered_info.get('baby_age', 'Unknown')}
            3. Provide feeding-specific advice
            4. Reference all context provided above
            
            DO NOT provide general advice - be specific to this case."""
            
            response = await self.generate_response(prompt, chat_history)
        
        return {
            'type': ResponseTypes.ANSWER,
            'text': response.content,
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
            return float(response.content.strip())
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
        return response.content.strip().lower() == 'yes'

    async def extract_product_names(self, text: str) -> List[str]:
        """Extract product names from text"""
        prompt = f"""From this text: "{text}"
        Extract all product names (brand names, model names, etc.)
        Return as JSON array of strings.
        Example: ["Graco 4Ever", "Chicco KeyFit 30"]"""

        response = await self.generate_response(prompt)
        try:
            return json.loads(response.content)
        except:
            return []

    async def calculate_context_relevance(self, query: str, context: str) -> float:
        prompt = f"""Compare this query: "{query}" with context: "{context}"
        Return similarity score (0.0-1.0)"""
        response = await self.generate_response(prompt)
        try:
            return float(response.content.strip())
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
            return json.loads(response.content)
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
        return result.content.strip().lower() == 'yes'

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
            return json.loads(response.content)
        except:
            return []

    async def evaluate_context(self, prompt: str) -> str:
        """Evaluate if current context is sufficient for a meaningful response"""
        try:
            response = await self.model.ainvoke([
                {
                    "role": "system",
                    "content": "You are a context evaluation assistant. Your task is to determine if there is sufficient context to provide a meaningful response. Return ONLY 'true' or 'false'."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ])
            return response.content.strip().lower()
        except Exception as e:
            print(f"Error evaluating context: {str(e)}")
            return 'false'  # Default to needing more context on error

    def _needs_medical_disclaimer(self, query: str) -> bool:
        """Check if the query needs a medical disclaimer"""
        health_keywords = [
            'health', 'medical', 'sick', 'symptoms', 'pain', 'doctor',
            'depression', 'anxiety', 'mental', 'stress', 'postpartum',
            'baby blues', 'medication', 'treatment', 'diagnosis',
            'fever', 'infection', 'disease', 'condition', 'therapy'
        ]
        return any(keyword in query.lower() for keyword in health_keywords)

    def _add_medical_disclaimer(self, response: str) -> str:
        """Add a medical disclaimer to the response"""
        disclaimer = (
            "⚠️ Important: I want to clarify that I'm not a medical professional. "
            "This information is for educational purposes only. "
            "For medical advice, diagnosis, or treatment, please consult with your healthcare provider.\n\n"
        )
        return disclaimer + response 

    async def generate_perplexity_response(self, query: str, context: Dict) -> Dict:
        """Generate a response using Perplexity API for real-time product information."""
        try:
            print("\n=== Perplexity Response Generation ===")
            # Extract context information
            gathered_info = context.get('gathered_info', {})
            budget = gathered_info.get('budget', 'Not specified')
            preferences = gathered_info.get('preferences', [])
            usage = gathered_info.get('usage', '')

            print(f"Budget: {budget}")
            print(f"Preferences: {preferences}")
            print(f"Usage: {usage}")

            # Create enhanced prompt for product recommendations
            product_category = context.get('product_category', 'general')
            
            if product_category == 'car_seat':
                enhanced_prompt = f"""You are a knowledgeable baby product expert. Please provide current market information and recommendations for this car seat query: {query}

Requirements:
- Budget: {budget}
- Preferences: {', '.join(preferences) if preferences else 'Not specified'}
- Usage: {usage}

Provide your response in this EXACT format:

👋 [Friendly greeting]

🛡️ Safety First:
- Latest safety ratings and certifications
- Key safety features to look for
- Installation considerations

🏆 Top Recommendation: [Product Name]
💰 Price: [Current exact price]
✨ Key Features:
- [Safety Feature 1]
- [Safety Feature 2]
- [Comfort/Convenience Feature]

🔍 Safety Certifications:
- [List relevant safety certifications]
- [Crash test ratings if available]

🛍️ Where to Buy:
- [Store/Website 1]
- [Store/Website 2]

💡 Why This Choice:
[2-3 sentences explaining safety features and value]

🌟 Alternative Option: [Second Product]
[Follow same safety-focused format as above]

⚠️ Important Safety Notes:
- [Key safety consideration 1]
- [Key safety consideration 2]
- [Installation tip]

🤔 Need more help?
[One relevant follow-up question about specific needs]

Remember to emphasize that proper installation and use are crucial for car seat safety."""
            elif product_category == 'stroller':
                enhanced_prompt = f"""You are a knowledgeable baby product expert. Please provide current market information and recommendations for this stroller query: {query}

Requirements:
- Budget: {budget}
- Preferences: {', '.join(preferences) if preferences else 'Not specified'}
- Usage: {usage}

Provide your response in this EXACT format:

👋 [Friendly greeting]

🏆 Top Pick: [Product Name]
💰 Price: [Current exact price]
✨ Key Features:
- [Mobility Feature]
- [Comfort Feature]
- [Storage/Convenience Feature]

🛍️ Where to Buy:
- [Store/Website 1]
- [Store/Website 2]

💡 Why This Choice:
[2-3 sentences explaining why this matches their needs]

🌟 Alternative Option: [Second Product]
[Follow same format as above]

🤔 Need more help?
[One relevant follow-up question about their needs]"""
            else:
                # Default product template
                enhanced_prompt = f"""You are a knowledgeable baby product expert. Please provide current market information and recommendations for this query: {query}

Requirements:
- Budget: {budget}
- Preferences: {', '.join(preferences) if preferences else 'Not specified'}
- Usage: {usage}

Provide your response in this EXACT format:

👋 [Friendly greeting]

🏆 Top Recommendation: [Product Name]
💰 Price: [Current exact price]
✨ Key Features:
- [Feature 1]
- [Feature 2]
- [Feature 3]

🛍️ Where to Buy:
- [Store/Website 1]
- [Store/Website 2]

💡 Why This Choice:
[2-3 sentences explaining why this matches their needs]

🌟 Alternative Option: [Second Product]
[Follow same format as above]

🤔 Need more help?
[One relevant follow-up question about their needs]"""

            print("Sending enhanced prompt to Perplexity...")
            
            # Determine which model to use based on query type
            if any(term in query.lower() for term in ['compare', 'difference', 'better', 'pros and cons', 'vs', 'versus']):
                # Use llama-3-70b-chat for comparison queries (replacing sonar-reasoning)
                print("Using llama-3-70b-chat for comparison query...")
                model = "llama-3-70b-chat"
            else:
                # Use llama-3-34b-chat for general product queries (replacing sonar-medium-chat)
                print("Using llama-3-34b-chat for product information...")
                model = "llama-3-34b-chat"

            response = await self.model.ainvoke([
                {"role": "system", "content": "You are a knowledgeable baby product expert providing current market recommendations with accurate pricing and availability information."},
                {"role": "user", "content": enhanced_prompt}
            ])

            if not response or not response.content:
                raise ValueError("No valid response from Perplexity API")

            return {
                'type': ResponseTypes.ANSWER,
                'text': response.content
            }

        except Exception as e:
            print(f"Error in Perplexity response generation: {str(e)}")
            # Fallback to OpenAI if Perplexity fails
            print("Falling back to OpenAI for response...")
            return await self.generate_response(query, context=context) 