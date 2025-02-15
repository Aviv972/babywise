class GeneralAgent(BaseAgent):
    def __init__(self, llm_service):
        super().__init__(name="General Assistant", expertise=[], llm_service=llm_service)
        
    async def process_query(self, query: str, context: Dict) -> Dict:
        # For general queries, analyze if we need to route to specialist
        analysis = await self.llm_service.analyze_query_intent(query)
        
        if analysis['confidence'] > 0.7 and analysis['agent_type'] != 'general':
            return {
                'type': 'redirect',
                'agent_type': analysis['agent_type'],
                'reason': f"This query would be better handled by our {analysis['agent_type']} specialist."
            }
            
        # Otherwise handle as general query
        response = await self.llm_service.generate_response(query)
        return {
            'type': 'answer',
            'text': response['text']
        } 