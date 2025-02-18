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
        # Use in-memory database for immediate access
        is_vercel = os.environ.get('VERCEL', False)
        self.db_url = 'file::memory:?cache=shared' if is_vercel else 'chatbot.db'
        self.conn: Optional[sqlite3.Connection] = None
        
        # Initialize persistent storage if in production
        self.persistent = PersistentStorage() if is_vercel else None
        
        self.create_tables()

    def get_connection(self) -> sqlite3.Connection:
        if not self.conn:
            self.conn = sqlite3.connect(self.db_url, uri=True)
        return self.conn
        
    def create_tables(self):
        """Create necessary tables in SQLite"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables for immediate access
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            message TEXT,
            role TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
        ''')
        
        conn.commit()

    async def store_message(self, session_id: str, message: str, role: str):
        """Store message in both immediate and persistent storage"""
        # Store in SQLite for immediate access
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, message, role) VALUES (?, ?, ?)",
            (session_id, message, role)
        )
        conn.commit()
        
        # Store in persistent storage if available
        if self.persistent:
            message_data = {
                'message': message,
                'role': role,
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': session_id
                }
            }
            await self.persistent.store_message(session_id, message_data)

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history from both storages"""
        # Get immediate history from SQLite
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT message, role, timestamp 
               FROM messages 
               WHERE session_id = ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (session_id, limit)
        )
        
        immediate_history = [
            {'message': msg, 'role': role, 'timestamp': ts}
            for msg, role, ts in cursor.fetchall()
        ]
        
        # Get persistent history if available
        if self.persistent:
            persistent_history = await self.persistent.get_conversation_history(session_id, limit)
            # Merge histories, prioritizing immediate history
            return self._merge_histories(immediate_history, persistent_history)
        
        return immediate_history

    def _merge_histories(self, immediate: List[Dict], persistent: List[Dict]) -> List[Dict]:
        """Merge immediate and persistent histories, removing duplicates"""
        merged = {}
        
        # Add immediate history first (higher priority)
        for msg in immediate:
            key = f"{msg['timestamp']}_{msg['message']}"
            merged[key] = msg
            
        # Add persistent history
        for msg in persistent:
            key = f"{msg['timestamp']}_{msg['message']}"
            if key not in merged:
                merged[key] = msg
                
        # Sort by timestamp and return
        return sorted(merged.values(), key=lambda x: x['timestamp'], reverse=True)

    async def store_context(self, session_id: str, context_data: Dict[str, Any]):
        """Store context in persistent storage"""
        if self.persistent:
            await self.persistent.store_context(session_id, context_data)

    async def get_context(self, session_id: str) -> Optional[Dict]:
        """Get context from persistent storage"""
        if self.persistent:
            return await self.persistent.get_context(session_id)
        return None

    async def store_knowledge_base_entry(self, entry: Dict[str, Any]):
        """Store entry in knowledge base"""
        if self.persistent:
            await self.persistent.store_knowledge_base_entry(entry)

    async def search_knowledge_base(self, query: str, threshold: float = 0.7) -> List[Dict]:
        """Search knowledge base for relevant entries"""
        if self.persistent:
            return await self.persistent.search_knowledge_base(query, threshold)
        return []

    async def close(self):
        """Close all database connections"""
        if self.conn:
            self.conn.close()
        if self.persistent:
            await self.persistent.close()

    def __del__(self):
        """Cleanup on object destruction"""
        if self.conn:
            try:
                self.conn.close()
            except:
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

    def get_context_info(self, conversation_id: int) -> Dict[str, str]:
        """Get all context information for a conversation"""
        cursor = self.conn.execute(
            """SELECT field, value 
               FROM context_info 
               WHERE conversation_id = ?
               ORDER BY created_at DESC""",
            (conversation_id,)
        )
        
        context = {}
        for row in cursor.fetchall():
            context[row[0]] = row[1]
        return context

    def update_conversation_metadata(self, conversation_id: int, metadata: dict):
        """Update conversation metadata"""
        self.conn.execute(
            """UPDATE conversations 
               SET metadata = ?
               WHERE id = ?""",
            (json.dumps(metadata), conversation_id)
        )
        self.conn.commit()

    def search_knowledge_base(self, query: str, category: str, threshold: float = 0.7) -> Optional[str]:
        """Search for existing relevant responses"""
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