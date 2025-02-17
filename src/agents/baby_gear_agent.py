from typing import Dict, List, Any, Optional, Union
from src.agents.base_agent import BaseAgent
from src.constants import ResponseTypes, AgentTypes
from src.services.llm_service import LLMService
import json

class BabyGearAgent(BaseAgent):
    def __init__(self, llm_service: LLMService):
        super().__init__(llm_service)
        self.agent_type = "baby_gear"
        self.name = "Baby Gear Expert"
        
        # Define expertise for agent selection
        self.expertise = [
            "strollers", "car seats", "cribs", "carriers",
            "high chairs", "playpens", "monitors", "breast pumps"
        ]
        self.required_context = ["budget", "preferences"]

    def _calculate_confidence(self, query: str, keywords: List[str]) -> float:
        """Calculate confidence score for handling a query based on keyword matches."""
        query_lower = query.lower()
        
        # Core gear-related keywords
        gear_keywords = [
            "stroller", "עגלה", "car seat", "כיסא בטיחות",
            "crib", "מיטה", "bassinet", "עריסה",
            "gear", "equipment", "ציוד"
        ]
        
        matching_keywords = sum(
            1 for keyword in gear_keywords 
            if keyword in query_lower or any(word in query_lower for word in keyword.split())
        )
        
        confidence = min(matching_keywords / 2, 1.0)
        print(f"BabyGearAgent: Found {matching_keywords} gear-related keywords; confidence = {confidence}")
        return confidence

    def _prepare_prompt(self, query: str, lang: str) -> str:
        """Prepare the final prompt for the LLM based on the query and language."""
        prompt = f"""As a baby gear expert, provide detailed advice about: {query}

Analysis Framework:
1. Safety Considerations:
   - Age/stage appropriateness
   - Relevant safety guidelines

2. Product Evaluation:
   - Essential features and quality markers
   - Durability and ease of use

3. Value Assessment:
   - Price ranges and cost-effectiveness
   - Long-term usability and maintenance needs

4. Practical Usage:
   - Real-world usage tips and common challenges

5. Recommendations:
   - Specific suggestions and alternatives with clear reasoning

Please respond in {lang}."""
        return prompt

    def _identify_gear_type(self, query: str) -> Optional[str]:
        """Identify which type of gear the user is asking about."""
        gear_keywords = {
            "stroller": ["stroller", "pushchair", "buggy", "עגלה"],
            "car_seat": ["car seat", "carseat", "כיסא בטיחות"],
            "crib": ["crib", "bed", "bassinet", "מיטה", "עריסה"]
        }
        query_lower = query.lower()
        for gear, keywords in gear_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return gear
        return None

    async def can_handle_query(self, query: str, keywords: List[str]) -> bool:
        """Decide if this agent should handle the query."""
        print("\n=== BabyGearAgent Checking Query ===")
        print(f"Query received: {query}")
        
        # First check if this is explicitly about baby gear
        gear_related = any(word in query.lower() for word in [
            "stroller", "עגלה", "car seat", "כיסא בטיחות",
            "crib", "מיטה", "bassinet", "עריסה"
        ])
        
        if gear_related:
            print("Detected gear-related query")
            return True
        
        # If not explicitly about gear, calculate general confidence
        confidence = self._calculate_confidence(query, keywords)
        print(f"General confidence score: {confidence}")
        
        # Only handle high confidence gear-related queries
        return confidence > 0.8 and any(word in query.lower() for word in [
            "gear", "equipment", "product", "buy", "purchase",
            "ציוד", "מוצר", "לקנות", "רכישה"
        ])

    def _set_role_boundaries(self):
        """Define what this agent can or cannot do."""
        self.role_boundaries = {
            "can_do": [
                "product recommendations",
                "price comparisons",
                "feature analysis",
                "safety guidelines",
                "age appropriateness",
                "product specifications"
            ],
            "cannot_do": [
                "medical advice",
                "health recommendations",
                "pregnancy guidance",
                "child development",
                "parenting advice"
            ]
        }

    def _is_hebrew(self, text: str) -> bool:
        """Check if the text contains Hebrew characters."""
        return any('\u0590' <= c <= '\u05FF' for c in text)

    def _get_language(self, text: str) -> str:
        """Return 'he' if Hebrew, otherwise 'en'."""
        return 'he' if self._is_hebrew(text) else 'en'

    def add_context(self, field: str, value: str):
        """Maintain compatibility with existing code"""
        self.conversation_state['gathered_info'][field] = value

    def _get_missing_context(self) -> List[str]:
        """Return a list of required context fields that haven't been answered."""
        return [field for field in self.question_flow[0]['extract_keys'] if field not in self.conversation_state['gathered_info']]

    def _generate_relevant_question(self, field: str, lang: str) -> str:
        """Generate a follow-up question for the missing context field."""
        return self.question_flow[0]['question'][lang]

    def _analyze_query_needs(self, query: str) -> List[str]:
        """Analyze the query to determine which context fields are actually needed."""
        needed_info = []
        query_lower = query.lower()

        print("\n=== Analyzing Query Needs ===")
        print(f"Query: {query_lower}")

        # For queries about specific price points (cheapest/most expensive), we don't need context
        if any(word in query_lower for word in [
            "cheapest", "most expensive", "highest price", "lowest price",
            "הכי זול", "הכי יקר", "המחיר הגבוה", "המחיר הנמוך"
        ]):
            print("Price comparison query - no context needed")
            return []

        # For general price queries, we need budget
        if any(word in query_lower for word in ["price", "cost", "budget", "מחיר", "עלות", "תקציב"]):
            print("Price query - need budget")
            needed_info.append("budget_range")

        # For recommendation queries, we need more context
        if any(word in query_lower for word in ["recommend", "best", "good", "suitable", "מומלץ", "טוב", "מתאים"]):
            print("Recommendation query - need relevant context")
            needed_info.append("age")
            if "car" in query_lower or "רכב" in query_lower:
                needed_info.append("car_type")
            if "space" in query_lower or "אחסון" in query_lower:
                needed_info.append("living_situation")

        print(f"Needed information: {needed_info}")
        return needed_info

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process baby gear specific queries"""
        try:
            # Extract budget from query if present
            if 'under' in query.lower() and '$' in query:
                import re
                budget_match = re.search(r'\$?(\d+)', query)
                if budget_match:
                    context['gathered_info'] = context.get('gathered_info', {})
                    context['gathered_info']['budget'] = f"${budget_match.group(1)}"
                    print(f"Extracted budget: {context['gathered_info']['budget']}")

            # Set query type for stroller queries
            if 'stroller' in query.lower():
                context['query_type'] = 'twin_stroller' if 'twins' in query.lower() else 'stroller'
                print(f"Set query type to: {context['query_type']}")

            # Prepare prompt with context
            prompt = f"""As a baby gear expert, I need to provide a recommendation for {context.get('query_type', 'baby gear')}.

Current Information:
Budget: {context.get('gathered_info', {}).get('budget', 'Not specified')}
Query: {query}

Please provide:
1. 2-3 specific product recommendations within the budget
2. Key features and benefits of each
3. Price points
4. Where to buy
5. Any important considerations

Focus on practical, real-world advice and current market options."""

            print("Sending prompt to LLM service...")
            response = await self.llm_service.generate_response(
                prompt=prompt,
                chat_history=chat_history,
                context=context
            )
            
            if not response or not response.get('text'):
                print("No response received from LLM service")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I apologize, but I'm having trouble accessing current product information. Could you please tell me what specific features you're looking for in a stroller? This will help me provide better recommendations."
                }
            
            print("Successfully generated response")
            return {
                'type': ResponseTypes.ANSWER,
                'text': response['text']
            }
            
        except Exception as e:
            print(f"Error in baby gear agent specific processing: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I'm having trouble processing your request. Could you please specify what features are most important to you in a stroller? For example: lightweight, compact folding, storage space, or terrain handling?"
            }

    def _format_gathered_info(self) -> str:
        """Format gathered information for prompt"""
        info = []
        for question, answer in self.conversation_state['gathered_info'].items():
            info.append(f"Q: {question}\nA: {answer}")
        return "\n\n".join(info)

    def _extract_product_info(self, text: str) -> List[Dict]:
        """Extract structured product information from response text"""
        products = []
        lines = text.split('\n')
        current_product = {}
        
        for line in lines:
            if line.strip():
                # Look for product names (capitalized words)
                if any(word[0].isupper() for word in line.split()):
                    if current_product:
                        products.append(current_product)
                    current_product = {"name": line.strip()}
                # Look for prices
                elif "$" in line:
                    current_product["price"] = line[line.find("$"):].split()[0]
                    # Extract features from the same line
                    features = line[:line.find("$")].strip()
                    if features:
                        current_product["features"] = features
        
        if current_product:
            products.append(current_product)
        
        return products

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is relevant to agent's domain"""
        query_lower = query.lower()
        
        # Core gear terms that strongly indicate this is a gear query
        gear_terms = [
            "stroller", "car seat", "crib", "bassinet",
            "עגלה", "כיסא בטיחות", "מיטת תינוק", "עריסה",
            "gear", "equipment", "product", "buy", "purchase",
            "ציוד", "מוצר", "לקנות", "רכישה"
        ]
        
        # If query contains gear terms, this is definitely our domain
        if any(term in query_lower for term in gear_terms):
            print("Found gear-specific terms")
            return 1.0  # Return 1.0 for gear queries
        
        return 0.0  # Not our domain

    def is_safety_related(self, query: str) -> bool:
        safety_keywords = ["safe", "safety", "danger", "warning"]
        return any(keyword in query.lower() for keyword in safety_keywords)

    def is_medical_advice(self, query: str) -> bool:
        medical_keywords = ["health", "medical", "doctor", "symptom"]
        return any(keyword in query.lower() for keyword in medical_keywords)

    def needs_realtime_info(self, query: str) -> bool:
        realtime_keywords = ["price", "availability", "in stock", "compare"]
        return any(keyword in query.lower() for keyword in realtime_keywords)

    async def _get_realtime_info(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        return await self.llm_service.generate_response(
            f"Get current prices and availability for: {query}",
            chat_history
        )

    async def process_query(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process baby gear queries with enhanced user experience"""
        try:
            print("\n=== Processing Baby Gear Query ===")
            print(f"Query: {query}")
            print(f"Initial Context: {json.dumps(context.get('gathered_info', {}), indent=2)}")

            # Initialize or get gathered_info
            gathered_info = context.get('gathered_info', {})

            # Extract budget from query if present
            if 'under' in query.lower() and '$' in query:
                import re
                budget_match = re.search(r'\$?(\d+)', query)
                if budget_match:
                    gathered_info['budget'] = f"${budget_match.group(1)}"
                    context['gathered_info'] = gathered_info
                    print(f"Extracted budget: {gathered_info['budget']}")

            # Update context with any new information
            context['gathered_info'] = gathered_info

            # Get product category from context
            product_category = context.get('product_category')
            if not product_category:
                # Try to determine product category from query
                product_categories = {
                    'car_seat': ['car seat', 'carseat', 'car safety', 'infant seat', 'booster seat', 'convertible seat'],
                    'stroller': ['stroller', 'pushchair', 'pram', 'buggy', 'travel system'],
                    'carrier': ['carrier', 'baby wrap', 'sling', 'baby wearing'],
                    'furniture': ['crib', 'bassinet', 'changing table', 'playpen']
                }
                
                query_lower = query.lower()
                for category, keywords in product_categories.items():
                    if any(keyword in query_lower for keyword in keywords):
                        product_category = category
                        context['product_category'] = category
                        print(f"Detected product category: {category}")
                        break

            # Prepare enhanced context for the LLM
            enhanced_context = {
                'query_type': product_category or 'general',
                'gathered_info': gathered_info,
                'needs_realtime_info': True,
                'agent_type': 'baby_gear',
                'product_category': product_category
            }

            # Generate response with enhanced context
            response = await self.llm_service.generate_perplexity_response(
                query=query,
                context=enhanced_context
            )
            
            if not response or not response.get('text'):
                print("No response received from LLM service")
                return {
                    'type': ResponseTypes.ERROR,
                    'text': "I apologize, but I'm having trouble accessing current product information. Please try again in a moment."
                }
            
            print("Successfully generated recommendation")
            return {
                'type': ResponseTypes.ANSWER,
                'text': response['text']
            }
            
        except Exception as e:
            print(f"Error in baby gear agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            }

    def _extract_preferences(self, query: str) -> List[str]:
        """Extract preferences from the query"""
        preferences = []
        query_lower = query.lower()
        
        # Feature keywords and their variations
        feature_map = {
            'lightweight': ['light', 'lightweight', 'easy to carry'],
            'compact': ['compact', 'small', 'foldable', 'easy to store'],
            'storage': ['storage', 'basket', 'space'],
            'maneuverability': ['easy to maneuver', 'turns', 'steering'],
            'terrain': ['all-terrain', 'rough terrain', 'smooth ride'],
            'safety': ['safe', 'safety features', 'secure']
        }
        
        for feature, keywords in feature_map.items():
            if any(keyword in query_lower for keyword in keywords):
                preferences.append(feature)
                
        return preferences

    def _extract_usage(self, query: str) -> Optional[str]:
        """Extract usage information from the query"""
        query_lower = query.lower()
        
        # Usage patterns and their indicators
        usage_patterns = {
            'daily_use': ['everyday', 'daily', 'regular'],
            'travel': ['travel', 'vacation', 'trips'],
            'outdoor': ['outdoor', 'parks', 'walks'],
            'urban': ['city', 'urban', 'sidewalks'],
            'jogging': ['jogging', 'running', 'exercise']
        }
        
        for usage, indicators in usage_patterns.items():
            if any(indicator in query_lower for indicator in indicators):
                return usage
                
        return None

    async def _generate_product_recommendation(self, query: str, product_type: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Generate detailed product recommendations with enhanced context"""
        try:
            gathered_info = context.get('gathered_info', {})
            print(f"Generating recommendation with info: {json.dumps(gathered_info, indent=2)}")
            
            # Prepare enhanced context for the LLM
            enhanced_context = {
                'query_type': product_type,
                'gathered_info': gathered_info,
                'needs_realtime_info': True,
                'agent_type': 'baby_gear'
            }

            # Generate response with enhanced context
            response = await self.llm_service.generate_response(
                prompt=query,
                chat_history=chat_history,
                context=enhanced_context
            )
            
            if not response or not response.get('text'):
                raise ValueError("No response received from LLM service")

            print("Successfully generated recommendation")
            return {
                'type': ResponseTypes.ANSWER,
                'text': response['text']
            }
            
        except Exception as e:
            print(f"Error generating product recommendation: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I'm having trouble accessing current product information. Could you please tell me what specific features are most important to you? This will help me provide better recommendations."
            }

    async def _generate_friendly_follow_up(self, question_info: Dict, context: Dict, product_type: str) -> Dict:
        """Generate natural follow-up questions specific to baby gear"""
        field = question_info['field']
        
        questions = {
            'budget': f"What's your budget range for the {product_type.replace('_', ' ')}? This helps me recommend options that work for you.",
            'preferences': f"What features are most important to you in a {product_type.replace('_', ' ')}? For example, weight, size, or specific functions?",
            'usage': "How do you plan to use this most often? For example, daily errands, travel, or specific activities?",
            'baby_age': "How old is your baby? This helps me recommend age-appropriate options.",
            'car_type': "What type of car will you be installing this in? This ensures we find a car seat that fits properly."
        }

        return {
            'type': 'follow_up_question',
            'field': field,
            'question': questions.get(field, f"Could you tell me more about your {field.replace('_', ' ')}?")
        }

    def _determine_product_type(self, query: str) -> str:
        """Determine the type of baby gear product from the query"""
        query_lower = query.lower()
        
        # First check for explicit mentions
        product_mapping = {
            'stroller': ['stroller', 'pushchair', 'pram', 'buggy', 'עגלה'],
            'car_seat': ['car seat', 'carseat', 'car safety', 'מושב בטיחות'],
            'crib': ['crib', 'bed', 'bassinet', 'מיטת תינוק', 'עריסה'],
            'carrier': ['carrier', 'sling', 'wrap', 'מנשא'],
            'breast_pump': ['pump', 'breast pump', 'משאבת חלב'],
            'monitor': ['monitor', 'camera', 'מוניטור'],
            'high_chair': ['high chair', 'feeding chair', 'כיסא אוכל'],
            'playpen': ['playpen', 'play yard', 'לול']
        }

        # Check for exact matches first
        for product, keywords in product_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                print(f"Found product type: {product} based on keywords: {keywords}")
                return product

        # If no exact match, check for contextual clues
        if any(word in query_lower for word in ['walk', 'push', 'fold', 'travel with']):
            print("Inferring stroller from context")
            return 'stroller'
        
        if any(word in query_lower for word in ['sleep', 'nap']):
            print("Inferring crib from context")
            return 'crib'
        
        if any(word in query_lower for word in ['car', 'drive', 'vehicle']):
            print("Inferring car seat from context")
            return 'car_seat'

        print("No specific product type found, defaulting to unknown")
        return 'unknown'

    def _get_initial_recommendations(self, product_type: str, gathered_info: Dict) -> List[Dict]:
        """Get initial product recommendations based on available information"""
        if product_type == 'breast_pump':
            return self._get_breast_pump_recommendations(gathered_info)
        if product_type == 'stroller':
            return self._get_stroller_recommendations(gathered_info)
        # Add other product types as needed
        return []

    def _get_breast_pump_recommendations(self, gathered_info: Dict) -> List[Dict]:
        """Get breast pump recommendations based on gathered information"""
        budget = gathered_info.get('budget', 'unknown')
        preferences = gathered_info.get('preferences', '')
        
        recommendations = []
        
        # Budget-friendly electronic pumps
        if 'under $200' in str(budget).lower():
            recommendations.extend([
                {
                    'name': 'Spectra S2 Plus',
                    'price': '$159',
                    'features': ['Hospital grade', 'Quiet operation', 'Adjustable suction', 'Closed system'],
                    'best_for': 'Overall best value for money'
                },
                {
                    'name': 'Medela Pump In Style',
                    'price': '$199',
                    'features': ['Double electric', 'Portable', 'Good suction strength'],
                    'best_for': 'Reliable daily use'
                },
                {
                    'name': 'Lansinoh Smartpump 2.0',
                    'price': '$150',
                    'features': ['Bluetooth connectivity', 'App tracking', 'Compact design'],
                    'best_for': 'Smart features on a budget'
                }
            ])
        
        # Filter based on preferences if any are specified
        if preferences:
            preferences_lower = preferences.lower()
            filtered_recommendations = []
            for rec in recommendations:
                features_str = ' '.join(rec['features']).lower()
                matches_preferences = True
                
                if 'small' in preferences_lower or 'portable' in preferences_lower:
                    if not ('portable' in features_str or 'compact' in features_str):
                        matches_preferences = False
                if 'app' in preferences_lower or 'smart' in preferences_lower:
                    if not ('app' in features_str or 'bluetooth' in features_str):
                        matches_preferences = False
                if 'quiet' in preferences_lower:
                    if not 'quiet' in features_str:
                        matches_preferences = False
                
                if matches_preferences:
                    filtered_recommendations.append(rec)
            
            recommendations = filtered_recommendations if filtered_recommendations else recommendations
        
        return recommendations

    def _format_recommendations(self, recommendations: List[Dict], gathered_info: Dict) -> str:
        """Format recommendations into a readable response"""
        if not recommendations:
            return "Based on your requirements, I don't have any matching recommendations. Could you tell me if you're flexible on any of your criteria?"
        
        response = "Based on your requirements, here are some recommended breast pumps:\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            response += f"{i}. {rec['name']} - {rec['price']}\n"
            response += f"   Best for: {rec['best_for']}\n"
            response += f"   Key features: {', '.join(rec['features'])}\n\n"
        
        # Add helpful context about what information could refine the recommendations
        missing = self._get_helpful_additional_criteria(gathered_info)
        if missing:
            response += f"\nTo help refine these recommendations further, you could tell me:\n"
            response += f"- {missing[0]}"
        
        return response

    def _get_helpful_additional_criteria(self, gathered_info: Dict) -> List[str]:
        """Get suggestions for additional helpful (but not critical) information"""
        helpful_criteria = []
        
        if 'preferences' not in gathered_info:
            helpful_criteria.append("Any specific features you're looking for (e.g., portability, noise level, battery operation)")
        if 'usage_frequency' not in gathered_info:
            helpful_criteria.append("How often you plan to use it (e.g., daily, occasional, travel)")
        if 'brand_preference' not in gathered_info:
            helpful_criteria.append("If you have any preferred brands")
            
        return helpful_criteria

    def _get_missing_critical_info(self, product_type: str, gathered_info: Dict) -> List[str]:
        """Determine missing critical information based on product type"""
        missing = []
        
        # Universal requirements
        if 'budget' not in gathered_info:
            missing.append('budget')
            return missing  # Always get budget first
        
        # Product-specific requirements
        if product_type == 'stroller':
            # For strollers, we need usage information first
            if 'usage' not in gathered_info:
                missing.append('usage')
                return missing
            
            # Only ask for age if we have usage and it indicates the stroller is for a young baby
            usage = gathered_info.get('usage', '').lower()
            if ('baby_age' not in gathered_info and 
                ('newborn' in usage or 'infant' in usage or 'young' in usage)):
                missing.append('baby_age')
            
        elif product_type == 'car_seat':
            # For car seats, age is critical for safety
            if 'baby_age' not in gathered_info:
                missing.append('baby_age')
                return missing
            if 'car_type' not in gathered_info:
                missing.append('car_type')
            
        elif product_type == 'crib':
            # For cribs, we need usage information
            if 'usage' not in gathered_info:
                missing.append('usage')
                return missing
        
        # Only ask for preferences if we have the basic requirements
        if not missing and 'preferences' not in gathered_info:
            missing.append('preferences')
        
        return missing
