class ChatbotError(Exception):
    """Base exception class for chatbot errors"""
    pass

class ModelProcessingError(ChatbotError):
    """Raised when there's an error processing the query with the model"""
    pass

class DatabaseError(ChatbotError):
    """Raised when there's an error with database operations"""
    pass

class ValidationError(ChatbotError):
    """Raised when input validation fails"""
    pass

class ContextError(ChatbotError):
    """Raised when there's an error with context management"""
    pass

class AgentError(ChatbotError):
    """Raised when there's an error with agent operations"""
    pass 