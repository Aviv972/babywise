from datetime import datetime
import os
from typing import Optional, List, Dict, Any
import json
import logging
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # In-memory storage
        self._conversations = {}
        self._messages = {}
        self._chat_sessions = {}
        self._context_info = {}
        self._knowledge_base = {}
        
    async def initialize(self):
        """Initialize in-memory storage"""
        logger.info("Initialized in-memory storage")
        return True

    async def store_message_batch(self, messages: List[Dict[str, Any]]) -> bool:
        """Store multiple messages in memory"""
        try:
            for msg in messages:
                session_id = msg.get('session_id')
                if session_id not in self._chat_sessions:
                    self._chat_sessions[session_id] = {
                        'created_at': datetime.utcnow().isoformat(),
                        'last_updated': datetime.utcnow().isoformat()
                    }
                
                if session_id not in self._messages:
                    self._messages[session_id] = []
                
                self._messages[session_id].append({
                    'content': msg.get('content'),
                    'role': msg.get('role'),
                    'type': msg.get('type', 'text'),
                    'timestamp': datetime.utcnow().isoformat()
                })
            return True
        except Exception as e:
            logger.error(f"Error in batch message storage: {str(e)}")
            return False

    async def store_context_batch(self, session_id: str, context_items: List[Dict[str, Any]]) -> bool:
        """Store multiple context items in memory"""
        try:
            if session_id not in self._context_info:
                self._context_info[session_id] = []
            
            for item in context_items:
                self._context_info[session_id].append({
                    'field': item.get('field'),
                    'value': item.get('value'),
                    'timestamp': datetime.utcnow().isoformat()
                })
            return True
        except Exception as e:
            logger.error(f"Error in batch context storage: {str(e)}")
            return False

    async def store_message(self, session_id: str, message: Dict[str, Any]):
        """Store single message in memory"""
        try:
            if session_id not in self._chat_sessions:
                self._chat_sessions[session_id] = {
                    'created_at': datetime.utcnow().isoformat(),
                    'last_updated': datetime.utcnow().isoformat()
                }
            
            if session_id not in self._messages:
                self._messages[session_id] = []
            
            self._messages[session_id].append({
                'content': message.get('content'),
                'role': message.get('role'),
                'type': message.get('type', 'text'),
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': message.get('metadata', {})
            })
            return True
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            return False

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history from memory"""
        try:
            if session_id not in self._messages:
                return []
            
            messages = self._messages[session_id]
            return sorted(messages, key=lambda x: x['timestamp'], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []

    def create_conversation(self, agent_type: str = None, original_query: str = None, metadata: dict = None) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(len(self._conversations) + 1)
        self._conversations[conversation_id] = {
            'agent_type': agent_type,
            'original_query': original_query,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat()
        }
        return conversation_id

    def get_context_info(self, session_id: str) -> Dict[str, str]:
        """Get all context information for a conversation"""
        try:
            return {
                item['field']: item['value']
                for item in self._context_info.get(session_id, [])
            }
        except Exception as e:
            logger.error(f"Error getting context info: {str(e)}")
            return {}

    async def search_knowledge_base(self, query: str, threshold: float = 0.7) -> List[Dict]:
        """Search knowledge base for relevant entries"""
        # Simple implementation - can be enhanced with better search logic if needed
        return []

    async def close(self):
        """Cleanup (no-op for in-memory storage)"""
        pass

    def __del__(self):
        """Cleanup on object destruction"""
        pass

    def update_conversation_metadata(self, conversation_id: str, metadata: dict):
        """Update conversation metadata"""
        if conversation_id in self._conversations:
            self._conversations[conversation_id]['metadata'].update(metadata)
            self._conversations[conversation_id]['last_updated'] = datetime.utcnow().isoformat()

    def add_message(self, conversation_id: str, content: str, role: str, 
                   msg_type: str = None, metadata: dict = None):
        """Add a message to the conversation"""
        try:
            if conversation_id not in self._messages:
                self._messages[conversation_id] = []
            
            self._messages[conversation_id].append({
                'content': content,
                'role': role,
                'type': msg_type or 'text',
                'metadata': metadata or {},
                'timestamp': datetime.utcnow().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            return False

    def add_context_info(self, conversation_id: str, field: str, value: str):
        """Store context information for a conversation"""
        try:
            if conversation_id not in self._context_info:
                self._context_info[conversation_id] = []
            
            self._context_info[conversation_id].append({
                'field': field,
                'value': value,
                'timestamp': datetime.utcnow().isoformat()
            })
            return True
        except Exception as e:
            logger.error(f"Error adding context info: {str(e)}")
            return False

    def search_knowledge_base_by_category(self, query: str, category: str, threshold: float = 0.7) -> Optional[str]:
        """Search for existing relevant responses within a specific category"""
        # Simple in-memory implementation using string similarity
        from difflib import SequenceMatcher
        
        def similarity(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Search in knowledge base
        best_match = None
        best_score = 0
        
        for entry in self._knowledge_base.values():
            if entry['category'] == category:
                score = similarity(query, entry['query'])
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = entry
        
        return best_match['response'] if best_match else None

    def add_to_knowledge_base(self, category: str, query: str, response: str, 
                            source: str, keywords: List[str], relevance_score: float = 1.0):
        """Store new response in knowledge base"""
        entry_id = str(len(self._knowledge_base) + 1)
        self._knowledge_base[entry_id] = {
            'category': category,
            'query': query,
            'keywords': keywords,
            'response': response,
            'source': source,
            'relevance_score': relevance_score,
            'usage_count': 1,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def search_existing_response(self, query: str, agent_name: str) -> Optional[str]:
        """Search for existing response in message history"""
        from difflib import SequenceMatcher
        
        def similarity(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Search through all messages
        for messages in self._messages.values():
            for msg in messages:
                if msg.get('metadata', {}).get('agent_type') == agent_name:
                    if similarity(query, msg.get('content', '')) > 0.8:
                        return msg.get('content')
        return None 