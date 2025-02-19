from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import os
from typing import Optional, List, Dict, Any
import sqlite3
import json
from .persistent_storage import PersistentStorage
import logging
import asyncio
from contextlib import asynccontextmanager
from src.exceptions import DatabaseError

logger = logging.getLogger(__name__)

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    agent_name = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    query = Column(Text)
    response = Column(Text)
    confidence_score = Column(Float)
    category = Column(String)  # Add this column
    source = Column(String)    # Add this column
    conversation = relationship("Conversation", back_populates="messages")

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    
    id = Column(Integer, primary_key=True)
    category = Column(String)      # Agent category
    query = Column(String)         # Original query
    keywords = Column(String)      # Extracted keywords
    response = Column(Text)        # Stored response
    source = Column(String)        # OpenAI or Perplexity
    timestamp = Column(DateTime, default=datetime.utcnow)
    relevance_score = Column(Float)  # How relevant this response is
    usage_count = Column(Integer, default=0)  # How many times this response was used

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

    async def store_message(self, session_id: str, message: str, role: str):
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
                'content': message,
                'role': role,
                'type': 'text',
                'timestamp': datetime.utcnow().isoformat()
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
            'metadata': metadata,
            'created_at': datetime.utcnow().isoformat()
        }
        return conversation_id

    def get_context_info(self, conversation_id: str) -> Dict[str, str]:
        """Get all context information for a conversation"""
        return {
            item['field']: item['value']
            for item in self._context_info.get(conversation_id, [])
        }

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

    def create_conversation(self, agent_type: str = None, original_query: str = None, metadata: dict = None) -> int:
        """Create a new conversation and return its ID"""
        cursor = self.conn.execute(
            """INSERT INTO conversations 
               (agent_type, original_query, metadata, user_id) 
               VALUES (?, ?, ?, ?)""",
            (agent_type, original_query, json.dumps(metadata) if metadata else None, 'default')
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, conversation_id: int, content: str, role: str, 
                   msg_type: str = None, metadata: dict = None):
        """Add a message to the conversation"""
        self.conn.execute(
            """INSERT INTO messages 
               (conversation_id, content, role, type, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, content, role, msg_type, 
             json.dumps(metadata) if metadata else None)
        )
        self.conn.commit()

    def add_context_info(self, conversation_id: int, field: str, value: str):
        """Store context information for a conversation"""
        self.conn.execute(
            """INSERT INTO context_info 
               (conversation_id, field, value)
               VALUES (?, ?, ?)""",
            (conversation_id, field, value)
        )
        self.conn.commit()

    def get_conversation_history_immediate(self, conversation_id: int, limit: int = 10) -> List[Dict]:
        """Get conversation history with all associated data"""
        # Get messages
        cursor = self.conn.execute(
            """SELECT m.content, m.role, m.type, m.metadata, m.created_at,
                      c.original_query, c.agent_type, c.metadata as conv_metadata
               FROM messages m
               JOIN conversations c ON m.conversation_id = c.id
               WHERE m.conversation_id = ?
               ORDER BY m.created_at DESC LIMIT ?""",
            (conversation_id, limit)
        )
        
        messages = []
        for row in cursor.fetchall():
            message = {
                'content': row[0],
                'role': row[1],
                'type': row[2],
                'metadata': json.loads(row[3]) if row[3] else {},
                'timestamp': row[4],
                'conversation_info': {
                    'original_query': row[5],
                    'agent_type': row[6],
                    'metadata': json.loads(row[7]) if row[7] else {}
                }
            }
            messages.append(message)
        
        return messages

    def update_conversation_metadata(self, conversation_id: int, metadata: dict):
        """Update conversation metadata"""
        self.conn.execute(
            """UPDATE conversations 
               SET metadata = ?
               WHERE id = ?""",
            (json.dumps(metadata), conversation_id)
        )
        self.conn.commit()

    def search_knowledge_base_by_category(self, query: str, category: str, threshold: float = 0.7) -> Optional[str]:
        """Search for existing relevant responses within a specific category"""
        session = self.Session()
        try:
            # Find similar queries in the same category
            similar_entries = session.query(KnowledgeBase)\
                .filter(KnowledgeBase.category == category)\
                .all()
            
            # Calculate similarity scores
            from difflib import SequenceMatcher
            def similarity(a, b):
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()
            
            # Find best match
            best_match = None
            best_score = 0
            
            for entry in similar_entries:
                score = similarity(query, entry.query)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = entry
            
            if best_match:
                # Update usage count
                best_match.usage_count += 1
                session.commit()
                return best_match.response
                
            return None
            
        finally:
            session.close()

    def add_to_knowledge_base(self, category: str, query: str, response: str, 
                            source: str, keywords: List[str], relevance_score: float = 1.0):
        """Store new response in knowledge base"""
        session = self.Session()
        try:
            entry = KnowledgeBase(
                category=category,
                query=query,
                keywords=','.join(keywords),
                response=response,
                source=source,
                relevance_score=relevance_score,
                usage_count=1
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()

    async def search_existing_response(self, query: str, agent_name: str) -> Optional[str]:
        cursor = self.conn.execute(
            """SELECT response FROM messages 
               WHERE agent = ? AND similarity(query, ?) > 0.8
               ORDER BY created_at DESC LIMIT 1""",
            (agent_name, query)
        )
        result = cursor.fetchone()
        return result[0] if result else None 