from typing import Dict, Any, Optional, List
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

class MockLLMService:
    """Mock LLM service for testing"""
    
    def __init__(self, api_key: str = "test-key", model: str = "test-model"):
        self.api_key = api_key
        self.model = model
        
    async def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AIMessage:
        """Generate a mock response by converting to messages"""
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Convert to LangChain messages and use agenerate_response
        lc_messages = [
            HumanMessage(content=msg["content"]) if msg["role"] == "user"
            else AIMessage(content=msg["content"])
            for msg in messages
        ]
        return await self.agenerate_response(lc_messages, system_message, context)
        
    async def agenerate_response(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AIMessage:
        """Generate a mock response from messages"""
        # Extract content from the last message
        last_message = messages[-1] if messages else None
        if not last_message:
            return AIMessage(content="No message provided")
            
        content = last_message.content.lower()
        
        # Check for age in the message
        if "month" in content:
            for i in range(1, 37):
                if f"{i} month" in content:
                    return AIMessage(content=f"Here's advice for your {i}-month-old baby...")
                    
        # Check for parenting style
        if any(style in content for style in ["attachment", "gentle", "montessori", "traditional"]):
            style = next(s for s in ["attachment", "gentle", "montessori", "traditional"] if s in content)
            return AIMessage(content=f"Based on your {style} parenting style...")
            
        # Default response
        return AIMessage(content="Here's some general baby advice...") 