import os
from dotenv import load_dotenv
from pathlib import Path
import base64

class Config:
    # Load environment variables
    load_dotenv()
    print("\n=== Loading Configuration ===")

    @classmethod
    def get_api_key(cls) -> str:
        """Get and validate OpenAI API key"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        return api_key.strip()

    # Remove any validation that might interfere with the key format
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
    MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-4o-mini')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///chatbot.db')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    print("Perplexity API Key loaded successfully")  # Just confirm it's loaded without showing the key

    @classmethod
    def validate(cls):
        """Validate all required configuration"""
        required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate OpenAI API key format
        api_key = cls.get_api_key()
        if not api_key.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
            
        # Validate Perplexity API key format
        perplexity_key = cls.PERPLEXITY_API_KEY
        if not perplexity_key.startswith('pplx-'):
            raise ValueError("Invalid Perplexity API key format")
        
        print("Environment variables loaded successfully")
        print(f"Using model: {cls.MODEL_NAME}") 