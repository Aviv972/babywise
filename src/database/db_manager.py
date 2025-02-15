from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import os
from typing import Optional, List, Dict
import sqlite3

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
        self.conn = sqlite3.connect('chat_history.db')
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                conversation_id INTEGER,
                content TEXT,
                role TEXT,  -- 'user' or 'model'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        self.conn.commit()

    def create_conversation(self) -> int:
        cursor = self.conn.execute(
            "INSERT INTO conversations DEFAULT VALUES"
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_message(self, conversation_id: int, content: str, role: str):
        self.conn.execute(
            "INSERT INTO messages (conversation_id, content, role) VALUES (?, ?, ?)",
            (conversation_id, content, role)
        )
        self.conn.commit()

    def get_conversation_history(self, conversation_id: int, limit: int = 10) -> List[Dict]:
        cursor = self.conn.execute(
            """SELECT content, role FROM messages 
               WHERE conversation_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (conversation_id, limit)
        )
        return cursor.fetchall()

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