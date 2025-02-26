class MockLLMService:
    async def generate_response(self, *args, **kwargs):
        return {
            "type": "text",
            "text": "Mock response",
            "role": "assistant"
        }
        
    async def analyze_query_intent(self, *args, **kwargs):
        return {
            "intent": "mock_intent",
            "confidence": 0.9,
            "extracted_info": [
                {"field": "baby_age", "value": "3 months"},
                {"field": "location", "value": "urban"}
            ]
        }
        
    async def process_query(self, *args, **kwargs):
        return {
            "type": "text",
            "text": "Mock response",
            "role": "assistant",
            "addressed_fields": ["baby_age", "location"],
            "previous_field": "baby_age"
        } 