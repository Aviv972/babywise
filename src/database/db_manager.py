from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import os
from typing import Optional, List, Dict
import sqlite3
import json

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
        # Use in-memory database for Vercel environment
        is_vercel = os.environ.get('VERCEL', False)
        self.db_url = 'file::memory:?cache=shared' if is_vercel else 'chatbot.db'
        self.conn: Optional[sqlite3.Connection] = None
        self.create_tables()

    def get_connection(self) -> sqlite3.Connection:
        if not self.conn:
            self.conn = sqlite3.connect(self.db_url, uri=True)
        return self.conn
        
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables
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

    def get_conversation_history(self, conversation_id: int, limit: int = 10) -> List[Dict]:
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

    def close(self):
        """Close the database connection"""
        self.conn.close()

    def __del__(self):
        """Ensure database connection is closed when object is destroyed"""
        try:
            self.conn.close()
        except:
            pass

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