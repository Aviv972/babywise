import asyncio
from src.services.agent_factory import AgentFactory
from src.config import Config
from src.services.llm_service import LLMService

async def test_connection():
    """Test OpenAI connection before starting interactive mode"""
    try:
        llm_service = LLMService()
        response = await llm_service.generate_response("test connection")
        print("Connection test successful!")
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

async def test_agent_interactive():
    # Test connection first
    if not await test_connection():
        print("Exiting due to connection error")
        return
    
    # Validate configuration
    Config.validate()
    
    # Initialize agent factory (no need for LLMService parameter now)
    agent_factory = AgentFactory()
    
    print("\n=== Interactive Agent Testing ===")
    print("Type 'exit' to quit\n")
    
    while True:
        # Get query from user
        query = input("\nEnter your query: ")
        if query.lower() == 'exit':
            break
            
        print("\n--- Processing Query ---")
        
        # Get agent selection
        agent = await agent_factory.get_agent_for_query(query)
        
        # Get agent response
        response = await agent.process_query(query, {"keywords": query.split()})
        
        print(f"\nFinal Response: {response}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_agent_interactive()) 