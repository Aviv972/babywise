class TemplateAgent(BaseAgent):
    def __init__(self, llm_service):
        # Define expertise
        primary_expertise = [
            "keyword1", "keyword2",
            "hebrew1", "hebrew2"
        ]
        
        secondary_expertise = [
            "related1", "related2",
            "hebrew_related1", "hebrew_related2"
        ]
        
        super().__init__(
            name="Agent Name",
            expertise=primary_expertise + secondary_expertise,
            llm_service=llm_service
        )
        
        # Define role boundaries
        self.role_boundaries = {
            "can_do": ["task1", "task2"],
            "cannot_do": ["task3", "task4"]
        }

    def _calculate_domain_relevance(self, query: str) -> float:
        """Check if query is in this agent's domain"""
        query_lower = query.lower()
        
        # Primary domain terms
        primary_terms = ["term1", "term2"]
        if any(term in query_lower for term in primary_terms):
            print("Found domain-specific terms")
            return 1.0
        
        # Secondary domain terms
        secondary_terms = ["term3", "term4"]
        if any(term in query_lower for term in secondary_terms):
            print("Found domain-related terms")
            return 0.7
        
        return 0.0  # Not our domain

    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict:
        """Process query using standardized response format"""
        try:
            # Check for needed context
            needed_fields = await self._analyze_query_context_needs(query)
            missing_fields = [field for field in needed_fields 
                            if field not in context]
            
            if missing_fields:
                field = missing_fields[0]
                question_prompt = f"""Generate a natural follow-up question about the user's {field} 
                in the context of: {query}"""
                
                # Use LLMService's formatted response
                question_response = await self.llm_service.generate_response(question_prompt)
                
                return {
                    "type": "follow_up_question",
                    "question": question_response["text"],
                    "field": field
                }
            
            # Use parent's standardized process_query
            return await super().process_query(query, context)
            
        except Exception as e:
            print(f"Error in {self.__class__.__name__} process_query: {e}")
            raise 