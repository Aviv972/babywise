from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
from src.config import Config
from src.constants import ContextFields, MessageRoles, ResponseTypes, QuestionFields, RequiredFields, AgentTypes
import json
import os
from dotenv import load_dotenv
import logging

class LLMService:
    def __init__(self, api_key: str = None, model: str = None):
        load_dotenv()  # Ensure environment variables are loaded
        self.openai_api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.perplexity_api_key = os.getenv('PERPLEXITY_API_KEY')
        self.model = model or os.getenv('MODEL_NAME', 'gpt-4')
        
        logger = logging.getLogger(__name__)
        logger.info(f"Initializing LLM Service with model: {self.model}")
        
        if not self.openai_api_key:
            logger.error("OpenAI API key is missing!")
            raise ValueError("OpenAI API key is required")
            
        # Initialize OpenAI client
        try:
            logger.info("Initializing OpenAI client...")
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}", exc_info=True)
            raise
        
        # Initialize Perplexity client if key is available
        if self.perplexity_api_key:
            try:
                logger.info("Initializing Perplexity client...")
                self.perplexity_client = AsyncOpenAI(
                    api_key=self.perplexity_api_key,
                    base_url="https://api.perplexity.ai"
                )
                logger.info("Perplexity client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Perplexity client: {str(e)}", exc_info=True)
                self.perplexity_client = None
        else:
            logger.warning("Perplexity API key not found. Some features may be limited.")
            self.perplexity_client = None

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

    def merge_context(self, original_query: str, gathered_info: Dict, current_query: str) -> str:
        """Merge all context information into a comprehensive prompt"""
        return f"""CONVERSATION CONTEXT:
        Original Query: {original_query}
        
        Information gathered so far:
        {json.dumps(gathered_info, indent=2)}
        
        Current Query: "{current_query}"
        
        IMPORTANT REMINDERS:
        1. Always relate your response back to the original query
        2. Use ALL gathered information
        3. Stay focused on the original topic
        4. If asking follow-up questions, they must be relevant to the original query
        """

    async def generate_response(self, prompt: str, chat_history: List[Dict] = None, context: Dict = None) -> Dict:
        """Generate a response using OpenAI API with enhanced context awareness"""
        logger = logging.getLogger(__name__)
        try:
            logger.info("\n=== OpenAI Response Generation ===")
            logger.info(f"Using model: {self.model}")
            logger.info(f"Context available: {bool(context)}")
            
            # Build messages array with enhanced context
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add context if available
            if context:
                context_str = f"""Current context:
                Original Query: {context.get('original_query', 'Not provided')}
                Agent Type: {context.get('agent_type', 'Not specified')}
                Gathered Information: {json.dumps(context.get('gathered_info', {}), indent=2)}
                """
                messages.append({"role": "system", "content": context_str})
                logger.info("Added context to messages")

            # Add relevant chat history if available
            if chat_history:
                for msg in chat_history[-3:]:  # Include last 3 messages for context
                    messages.append({
                        "role": msg.get('role', 'user'),
                        "content": msg.get('content', '')
                    })
                logger.info("Added chat history to messages")

            # Add the current prompt
            messages.append({"role": "user", "content": prompt})

            logger.info("Sending request to OpenAI...")
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            if not response.choices or not response.choices[0].message:
                logger.error("No valid response from OpenAI API")
                raise ValueError("No valid response from OpenAI API")

            logger.info("Successfully received response from OpenAI")
            return {'text': response.choices[0].message.content}

        except Exception as e:
            logger.error(f"Error in OpenAI response generation: {str(e)}", exc_info=True)
            raise

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
        try:
            # Simplified analysis that always returns an empty result
            return {
                "extracted_info": [],
                "next_question": None
            }
        except Exception as e:
            print(f"Error in analyze_query_intent: {str(e)}")
            return {
                "extracted_info": [],
                "next_question": None
            }

    def _format_history_with_context(self, chat_history: List[Dict]) -> str:
        """Format chat history with context information"""
        if not chat_history:
            return ""
            
        formatted_msgs = []
        for msg in chat_history[-5:]:  # Last 5 messages for conciseness
            context_snapshot = msg.get('context_snapshot', {})
            formatted_msg = f"""
            {msg['role'].capitalize()}: {msg['content']}
            Context: {json.dumps(context_snapshot.get('gathered_info', {}), indent=2)}
            """
            formatted_msgs.append(formatted_msg)
            
        return "\nConversation History:\n" + "\n".join(formatted_msgs)

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

    async def evaluate_context(self, prompt: str) -> str:
        """Evaluate if current context is sufficient for a meaningful response"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a context evaluation assistant. Your task is to determine if there is sufficient context to provide a meaningful response. Return ONLY 'true' or 'false'."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1  # Low temperature for more consistent evaluation
            )
            return response.choices[0].message.content.strip().lower()
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

            response = await self.perplexity_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable baby product expert providing current market recommendations with accurate pricing and availability information."},
                    {"role": "user", "content": enhanced_prompt}
                ],
                temperature=0.7
            )

            if not response.choices or not response.choices[0].message:
                raise ValueError("No valid response from Perplexity API")

            return {
                'type': ResponseTypes.ANSWER,
                'text': response.choices[0].message.content
            }

        except Exception as e:
            print(f"Error in Perplexity response generation: {str(e)}")
            # Fallback to OpenAI if Perplexity fails
            print("Falling back to OpenAI for response...")
            return await self.generate_response(query, context=context) 