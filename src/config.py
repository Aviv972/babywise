import os
from dotenv import load_dotenv
from pathlib import Path
import base64
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Config:
    # Load environment variables
    load_dotenv()
    logger.info("\n=== Loading Configuration ===")

    @classmethod
    def get_api_key(cls) -> str:
        """Get and validate OpenAI API key"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found")
            raise ValueError("OPENAI_API_KEY not found")
        logger.info("OpenAI API key loaded successfully")
        return api_key.strip()

    # Remove any validation that might interfere with the key format
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
    MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///chatbot.db')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

    @classmethod
    def validate(cls):
        """Validate all required configuration"""
        logger.info("Validating configuration...")
        
        # Check OpenAI API key
        if not cls.OPENAI_API_KEY:
            logger.error("Missing OpenAI API key")
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.OPENAI_API_KEY.startswith('sk-'):
            logger.error("Invalid OpenAI API key format")
            raise ValueError("Invalid OpenAI API key format")
        logger.info("OpenAI API key validated")
            
        # Check Perplexity API key
        if cls.PERPLEXITY_API_KEY:
            if not cls.PERPLEXITY_API_KEY.startswith('pplx-'):
                logger.error("Invalid Perplexity API key format")
                raise ValueError("Invalid Perplexity API key format")
            logger.info("Perplexity API key validated")
        else:
            logger.warning("Perplexity API key not provided")
        
        # Log configuration status
        logger.info(f"Using model: {cls.MODEL_NAME}")
        logger.info(f"Database URL: {cls.DATABASE_URL}")
        logger.info("Configuration validation complete")

class ResponseTypes(Enum):
    """Enum for different types of responses"""
    ANSWER = "answer"
    ERROR = "error"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification" 