from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from src.constants import ResponseTypes, AgentTypes, ContextFields
from src.docs.common_questions import COMMON_QUESTIONS, RESPONSE_GUIDELINES
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, Runnable
from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool
from src.langchain import BabywiseState
import logging
import re

logger = logging.getLogger(__name__) 