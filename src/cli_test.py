import asyncio
from src.services.agent_factory import AgentFactory
from src.config import Config
from src.services.llm_service import LLMService
from src.services.chat_session import ChatSession

async def test_connection():
    """Test OpenAI connection before starting interactive mode"""
    try:
        llm_service = LLMService()
        response = await llm_service.generate_response("test connection")
        print("Connection test successful!")
        return llm_service
    except Exception as e:
        print(f"Connection test failed: {e}")
        return None

async def test_agent_interactive():
    # Test connection first
    llm_service = await test_connection()
    if not llm_service:
        print("Exiting due to connection error")
        return
    
    # Validate configuration
    Config.validate()
    
    # Initialize agent factory with LLM service
    agent_factory = AgentFactory(llm_service)
    
    # Initialize chat session
    chat_session = ChatSession(agent_factory)
    
    print("\n=== Interactive Agent Testing ===")
    print("Type 'exit' to quit\n")
    
    while True:
        # Get query from user
        query = input("\nEnter your query: ")
        if query.lower() == 'exit':
            break
            
        print("\n--- Processing Query ---")
        
        try:
            # Process query through chat session
            response = await chat_session.process_query(query)
            
            # Print response
            if isinstance(response, dict):
                print(f"\nResponse Type: {response.get('type', 'unknown')}")
                print(f"Response Text: {response.get('text', str(response))}")
            else:
                print(f"\nResponse: {response}")
                
            # Print current context state
            print("\nCurrent Context State:")
            context = chat_session.get_state()
            print(f"Agent Type: {context.get('agent_type', 'unknown')}")
            print(f"Gathered Info: {context.get('gathered_info', {})}")
            
        except Exception as e:
            print(f"\nError processing query: {str(e)}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_agent_interactive()) 