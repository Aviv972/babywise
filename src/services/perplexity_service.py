from openai import AsyncOpenAI
from typing import Dict, List
import json
from src.config import Config

class PerplexityService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.PERPLEXITY_API_KEY
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.perplexity.ai"
        )

    async def generate_response(self, prompt: str, chat_history: List[Dict] = None) -> Dict:
        try:
            messages = []
            
            if chat_history:
                messages.extend([
                    {
                        "role": msg['role'],
                        "content": msg['content']
                    }
                    for msg in chat_history[-10:]
                ])

            messages.append({
                "role": "user",
                "content": prompt
            })

            response = await self.client.chat.completions.create(
                model="sonar-pro",
                messages=messages
            )

            return {
                "type": "answer",
                "text": str(response.choices[0].message.content),
                "role": "model"
            }

        except Exception as e:
            print(f"Error in PerplexityService: {e}")
            return {
                "type": "error",
                "text": "Error connecting to Perplexity service",
                "role": "model"
            }

    async def search_and_enrich(self, query: str, chat_history: List[Dict] = None) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a baby gear expert. Search for current prices and availability of baby products."
                }
            ]

            if chat_history:
                messages.extend([
                    {
                        "role": msg['role'],
                        "content": msg['content']
                    }
                    for msg in chat_history[-10:]
                ])

            messages.append({
                "role": "user",
                "content": query
            })

            response = await self.client.chat.completions.create(
                model="sonar-pro",
                messages=messages
            )
            
            return response.choices[0].message.content

        except Exception as e:
            print(f"Error in PerplexityService: {e}")
            return "Error retrieving real-time information" 