import asyncio
from src.services.llm_service import LLMService
from src.services.agent_factory import AgentFactory

async def test_agent_selection():
    # Initialize services
    llm_service = LLMService()
    agent_factory = AgentFactory(llm_service)
    
    # Test queries
    test_queries = [
        "what is the cheapest baby strollers on the market right now?",
        "what should I expect in the third trimester?",
        "what do I need to prepare for my baby?",
        "which car seat is safest?",
        "when will I feel the baby kick?"
    ]
    
    print("\n=== Starting Agent Selection Tests ===\n")
    
    for query in test_queries:
        print(f"\n--- Testing Query: {query} ---")
        
        # Get agent selection
        agent = await agent_factory.get_agent_for_query(query)
        
        # Get agent response
        response = await agent.process_query(query, {"keywords": query.split()})
        
        print(f"\nFinal Response: {response}")
        print("-" * 50)
        
        # Add delay between tests
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_agent_selection()) 