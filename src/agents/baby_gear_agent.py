from typing import Dict, List, Any, Optional, Union
from .base_agent import BaseAgent
import json
from src.services.llm_service import LLMService

class BabyGearAgent(BaseAgent):
    def __init__(self, llm_service: LLMService):
        super().__init__(
            name="Baby Gear Expert",
            expertise=[
                "stroller", "car seat", "crib", "baby gear",
                "עגלה", "כיסא בטיחות", "מיטת תינוק", "ציוד לתינוק"
            ],
            llm_service=llm_service
        )
        
        # Define expertise for agent selection
        self.expertise = [
            "stroller", "car seat", "crib", "baby gear",
            "עגלה", "כיסא בטיחות", "מיטת תינוק", "ציוד לתינוק"
        ]

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

    async def process_query(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        # First query - set query type
        if not context.get('query_type'):
            context['query_type'] = 'twin_stroller' if 'twins' in query.lower() else 'stroller'

        # Use base processing with full context
        return await super().process_query(query, context, chat_history)

    async def _generate_final_response(self, context: Dict, chat_history: List[Dict]) -> Dict:
        """Generate stroller-specific recommendations"""
        prompt = f"""Original Query: {context['original_query']}
        Query Type: {context['query_type']}
        
        Information Collected:
        {json.dumps(context['gathered_info'], indent=2)}
        
        Provide specific recommendations that:
        1. Match the requirements exactly
        2. Include product names and features
        3. Explain why each suggestion fits their needs"""

        return await self.llm_service.generate_response(
            prompt=prompt,
            chat_history=chat_history
        )

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

    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        if self.needs_realtime_info(query):
            return await self._get_realtime_info(query, context, chat_history)
        return await self.llm_service.generate_response(query, chat_history)

    def needs_realtime_info(self, query: str) -> bool:
        realtime_keywords = ["price", "availability", "in stock", "compare"]
        return any(keyword in query.lower() for keyword in realtime_keywords)

    async def _get_realtime_info(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        return await self.llm_service.generate_response(
            f"Get current prices and availability for: {query}",
            chat_history
        )
