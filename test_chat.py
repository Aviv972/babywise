import asyncio
from src.langchain.graph import ConversationGraph
from langchain_core.messages import HumanMessage, AIMessage

async def test_chat():
    print("\n=== Testing Chat with Context Saving ===\n")
    
    # Initialize the conversation graph
    graph = ConversationGraph()
    thread_id = 'test_thread_123'
    
    # First message about twins and stroller
    print("User: I have twins who are 6 months old. What stroller do you recommend?")
    response1 = await graph.process_message(thread_id, 'I have twins who are 6 months old. What stroller do you recommend?')
    print("\nAssistant:", response1)
    
    # Second message referring to previous context
    print("\nUser: Which one of these would be best for traveling?")
    response2 = await graph.process_message(thread_id, 'Which one of these would be best for traveling?')
    print("\nAssistant:", response2)
    
    # Third message still maintaining context
    print("\nUser: And what about car seat compatibility?")
    response3 = await graph.process_message(thread_id, 'And what about car seat compatibility?')
    print("\nAssistant:", response3)
    
    # Show the stored context
    print("\n=== Stored Context ===")
    print("Thread ID:", thread_id)
    if thread_id in graph.memory:
        messages = graph.memory[thread_id].get("messages", [])
        print(f"Number of messages in context: {len(messages)}")
        print("\nMessage History:")
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant" if isinstance(msg, AIMessage) else "System"
            print(f"{role}: {msg.content[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_chat()) 