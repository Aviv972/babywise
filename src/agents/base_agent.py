from abc import ABC, abstractmethod
from typing import Dict, List
from src.services.llm_service import LLMService

class BaseAgent(ABC):
    def __init__(self, name: str, expertise: List[str], llm_service: LLMService):
        self.name = name
        self.expertise = expertise
        self.llm_service = llm_service

    async def process_query(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        try:
            analysis = await self.llm_service.analyze_query_intent(
                query=query,
                context=context,
                chat_history=chat_history
            )

            if not analysis.get('next_question'):
                return await self.llm_service.generate_final_response(
                    context=context,
                    chat_history=chat_history
                )

            return {
                'type': 'follow_up_question',
                'field': analysis['next_question']['field'],
                'question': analysis['next_question']['question'],
                'previous_field': analysis.get('previous_field')
            }

        except Exception as e:
            print(f"Error in BaseAgent: {e}")
            raise

    def _parse_field_value(self, field: str, answer: str) -> str:
        field_mapping = {
            'budget': lambda x: f"${x}" if not x.startswith('$') else x,
            'features': lambda x: ', '.join(x.split()),
            'usage': lambda x: x.strip()
        }
        return field_mapping.get(field, lambda x: x)(answer)

    def _parse_llm_field(self, field: str) -> str:
        field = field.lower().strip('- ').split('\n')[0]
        field_mapping = {
            'budget range': 'budget',
            'price range': 'budget',
            'cost range': 'budget',
            'desired features': 'features',
            'stroller features': 'features',
            'important features': 'features',
            'intended use': 'usage',
            'main use': 'usage',
            'primary use': 'usage'
        }
        return field_mapping.get(field, field)

    @abstractmethod
    async def _process_agent_specific(self, query: str, context: Dict, chat_history: List[Dict]) -> Dict:
        pass