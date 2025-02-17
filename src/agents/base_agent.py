from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from src.constants import ResponseTypes, AgentTypes
from src.docs.common_questions import COMMON_QUESTIONS, RESPONSE_GUIDELINES, SPECIAL_CONSIDERATIONS

class BaseAgent(ABC):
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.agent_type: str = AgentTypes.GENERAL  # Default type, should be overridden by subclasses
        self.name: str = "Base Agent"  # Should be overridden by subclasses
        self.expertise: List[str] = []  # Should be overridden by subclasses
        self.required_context: List[str] = []  # Should be overridden by subclasses
        
        # Load common questions and guidelines
        self.common_questions = COMMON_QUESTIONS
        self.response_guidelines = RESPONSE_GUIDELINES
        self.special_considerations = SPECIAL_CONSIDERATIONS
        
        # Standard medical disclaimer
        self.medical_disclaimer = (
            "⚠️ Important: I want to clarify that I'm not a medical professional. "
            "This information is for educational purposes only. "
            "For medical advice, diagnosis, or treatment, please consult with your healthcare provider."
        )

    async def process_query(self, query: str, context: Optional[Dict] = None, chat_history: Optional[List[Dict]] = None) -> Dict:
        """Process a query with enhanced context management and parent-friendly responses"""
        try:
            # Initialize or use existing context
            context = context or {}
            chat_history = chat_history or []
            
            # Store original query if not present
            if 'original_query' not in context:
                context['original_query'] = query

            # Check for emergency situations first
            if self._is_emergency_situation(query):
                return self._handle_emergency_situation(query)

            # Get relevant category and subcategory
            category, subcategory = self._identify_question_category(query)
            
            # Get response guidelines for this type of query
            guidelines = self._get_response_guidelines(category)

            # Generate enhanced prompt with guidelines
            prompt = self._generate_enhanced_prompt(query, category, subcategory, context, guidelines)

            # Determine if we should use Perplexity API
            use_perplexity = self._should_use_perplexity(query, category)
            
            # Generate response using appropriate API
            if use_perplexity:
                print("Using Perplexity API for real-time product information...")
                response = await self.llm_service.generate_perplexity_response(prompt, context)
            else:
                print("Using OpenAI API for general response...")
                response = await self.llm_service.generate_response(prompt, chat_history)

            # Add medical disclaimer for relevant categories or if needed
            needs_disclaimer = (category in ['mental_health', 'health_hygiene', 'safety_emergencies'] 
                              or self._needs_medical_disclaimer(query))

            if needs_disclaimer:
                # Ensure the disclaimer is at the end by appending it
                response['text'] = f"{response['text'].rstrip()}\n\n{self.medical_disclaimer}"

            return response

        except Exception as e:
            print(f"Error in {self.agent_type} agent: {str(e)}")
            return {
                'type': ResponseTypes.ERROR,
                'text': "I apologize, but I'm having trouble understanding. Could you rephrase your question?"
            }

    def _is_emergency_situation(self, query: str) -> bool:
        """Check if query describes an emergency situation"""
        emergency_keywords = [
            'choking', 'not breathing', 'unconscious', 'seizure',
            'severe bleeding', 'head injury', 'fall', 'accident',
            'emergency', 'hospital', '911', 'ambulance'
        ]
        return any(keyword in query.lower() for keyword in emergency_keywords)

    def _handle_emergency_situation(self, query: str) -> Dict:
        """Generate response for emergency situations"""
        return {
            'type': ResponseTypes.EMERGENCY,
            'text': "⚠️ This sounds like an emergency situation. Please:\n\n"
                   "1. Call emergency services (911) immediately\n"
                   "2. Stay calm and stay with your baby\n"
                   "3. Follow emergency dispatcher instructions\n"
                   "4. Contact your pediatrician after emergency care"
        }

    def _needs_medical_disclaimer(self, query: str) -> bool:
        """Check if query requires medical disclaimer"""
        medical_keywords = [
            'health', 'medical', 'sick', 'symptoms', 'pain', 'fever',
            'medicine', 'treatment', 'doctor', 'hospital', 'emergency',
            'infection', 'disease', 'condition', 'diagnosis'
        ]
        return any(keyword in query.lower() for keyword in medical_keywords)

    def _needs_professional_referral(self, query: str) -> bool:
        """Check if query requires professional referral"""
        for situation in self.special_considerations['referral_needed']:
            if any(word in query.lower() for word in situation.lower().split()):
                return True
        return False

    def _generate_referral_response(self, query: str) -> Dict:
        """Generate response recommending professional consultation"""
        return {
            'type': ResponseTypes.REFERRAL,
            'text': f"{self.medical_disclaimer}\n\n"
                   "Based on your question, I recommend consulting with a healthcare provider who can:"
                   "\n1. Properly evaluate the situation"
                   "\n2. Provide professional medical advice"
                   "\n3. Recommend appropriate treatment if needed"
                   "\n4. Monitor progress and adjust care as needed"
        }

    def _identify_question_category(self, query: str) -> tuple:
        """Identify the category and subcategory of the question"""
        query_lower = query.lower()
        
        for category, subcategories in self.common_questions.items():
            for subcategory, questions in subcategories.items():
                for question in questions:
                    if self._calculate_similarity(query_lower, question.lower()) > 0.7:
                        return category, subcategory
                        
        return "general", None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        # Simple word overlap for now - could be enhanced with more sophisticated methods
        words1 = set(text1.split())
        words2 = set(text2.split())
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        return overlap / total if total > 0 else 0

    def _get_response_guidelines(self, category: str) -> List[str]:
        """Get response guidelines for the category"""
        if category in ['health_hygiene', 'safety_emergencies']:
            return self.response_guidelines['response_structure']['medical_topics']
        elif category in ['clothing_essentials']:
            return self.response_guidelines['response_structure']['product_recommendations']
        else:
            return self.response_guidelines['response_structure']['parenting_advice']

    def _generate_enhanced_prompt(self, query: str, category: str, subcategory: str, context: Dict, guidelines: List[str]) -> str:
        """Generate enhanced prompt with guidelines and context"""
        # Get similar questions for context
        similar_questions = self._get_similar_questions(query, category, subcategory)
        
        prompt = f"""As a knowledgeable parenting assistant specializing in {self.agent_type}, 
        please help with this question: {query}

        Category: {category}
        Subcategory: {subcategory}

        Similar questions to consider:
        {self._format_similar_questions(similar_questions)}

        Response Guidelines:
        {self._format_guidelines(guidelines)}

        General Principles to Follow:
        {self._format_guidelines(self.response_guidelines['general_principles'])}

        Context Information:
        {self._format_context(context)}

        Please provide a comprehensive, supportive response that:
        1. Directly addresses the question
        2. Follows the guidelines above
        3. Uses a warm, encouraging tone
        4. Provides practical, actionable advice
        5. Acknowledges common challenges
        6. Offers additional resources when relevant"""

        return prompt

    def _get_similar_questions(self, query: str, category: str, subcategory: str) -> List[str]:
        """Get similar questions from the common questions database"""
        if category not in self.common_questions or subcategory not in self.common_questions[category]:
            return []
            
        questions = self.common_questions[category][subcategory]
        similar = []
        
        for question in questions:
            if self._calculate_similarity(query.lower(), question.lower()) > 0.3:
                similar.append(question)
                
        return similar[:3]  # Return top 3 similar questions

    def _format_similar_questions(self, questions: List[str]) -> str:
        """Format similar questions for prompt"""
        if not questions:
            return "No similar questions found."
        return "\n".join(f"- {q}" for q in questions)

    def _format_guidelines(self, guidelines: List[str]) -> str:
        """Format guidelines for prompt"""
        return "\n".join(f"- {g}" for g in guidelines)

    def _format_context(self, context: Dict) -> str:
        """Format context information for prompt"""
        if not context:
            return "No additional context available."
            
        formatted = []
        if 'original_query' in context:
            formatted.append(f"Original Query: {context['original_query']}")
        if 'gathered_info' in context:
            formatted.append("Gathered Information:")
            for key, value in context['gathered_info'].items():
                formatted.append(f"- {key}: {value}")
                
        return "\n".join(formatted)

    def _should_use_perplexity(self, query: str, category: str) -> bool:
        """Determine if we should use Perplexity API based on query content and category"""
        # Use Perplexity for product-related queries and real-time information needs
        product_categories = ['clothing_essentials', 'safety_emergencies']
        product_keywords = [
            'cost', 'price', 'buy', 'purchase', 'recommend', 'best',
            'compare', 'versus', 'vs', 'difference between', 'kit',
            'brand', 'model', 'latest', 'new', 'current'
        ]
        
        # Check if query is in a product-related category
        if category in product_categories:
            return True
            
        # Check if query contains product-related keywords
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in product_keywords):
            return True
            
        return False

    @abstractmethod
    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        """Process agent-specific logic. Should be implemented by subclasses."""
        pass

    def _get_missing_critical_fields(self, context: Dict) -> List[str]:
        """Get list of missing critical fields based on agent type and context.
        Should be overridden by subclasses if they have specific required fields."""
        gathered_info = context.get('gathered_info', {})
        return [field for field in getattr(self, 'required_context', [])
                if field not in gathered_info]