"""
Configuration package for the Babywise application.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
import base64
from enum import Enum
import logging
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from functools import lru_cache

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # API Keys
    openai_api_key: str
    langsmith_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    
    # Model Configuration
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.4
    max_tokens: int = 2000
    
    # Database Configuration
    database_url: str = "sqlite:///chatbot.db"
    mongodb_uri: Optional[str] = None
    
    # Memory Configuration
    memory_window_size: int = 5
    max_token_limit: int = 4000
    
    # Tracing Configuration
    langchain_tracing: bool = False
    langchain_project: Optional[str] = "babywise"
    
    class Config:
        env_file = ".env"

    def validate(self):
        """Validate all required configuration"""
        logger.info("Validating configuration...")
        
        # Check OpenAI API key
        if not self.openai_api_key:
            logger.error("Missing OpenAI API key")
            raise ValueError("OPENAI_API_KEY is required")
        if not self.openai_api_key.startswith('sk-'):
            logger.error("Invalid OpenAI API key format")
            raise ValueError("Invalid OpenAI API key format")
        logger.info("OpenAI API key validated")
            
        # Check Perplexity API key
        if self.perplexity_api_key:
            if not self.perplexity_api_key.startswith('pplx-'):
                logger.error("Invalid Perplexity API key format")
                raise ValueError("Invalid Perplexity API key format")
            logger.info("Perplexity API key validated")
        else:
            logger.warning("Perplexity API key not provided")
        
        # Log configuration status
        logger.info(f"Using model: {self.model_name}")
        logger.info(f"Database URL: {self.database_url}")
        logger.info("Configuration validation complete")

        if self.langchain_tracing and not self.langsmith_api_key:
            raise ValueError("LANGSMITH_API_KEY must be set when LANGCHAIN_TRACING is enabled")
        
        # Set LangChain environment variables
        if self.langchain_tracing:
            os.environ["LANGCHAIN_TRACING"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.validate()
    return settings

class ResponseTypes(Enum):
    """Enum for different types of responses"""
    ANSWER = "answer"
    ERROR = "error"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"

# This file makes the config directory a proper Python package 