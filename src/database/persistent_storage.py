from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PersistentStorage:
    def __init__(self):
        self.client = None
        self.db = None
        self._initialize_db()

    def _initialize_db(self):
        """Initialize MongoDB connection"""
        try:
            mongodb_url = os.environ.get('MONGODB_URI')
            if not mongodb_url:
                logger.warning("MongoDB URI not found in environment variables")
                return

            # Add connection timeout and server selection timeout
            self.client = AsyncIOMotorClient(
                mongodb_url,
                serverSelectionTimeoutMS=5000,  # 5 seconds timeout for server selection
                connectTimeoutMS=5000,          # 5 seconds timeout for initial connection
                socketTimeoutMS=5000,           # 5 seconds timeout for socket operations
                maxPoolSize=1,                  # Limit connection pool for serverless
                retryWrites=True                # Enable retrying write operations
            )
            
            # Test the connection with timeout
            self.db = self.client.get_database('babywise')
            logger.info("MongoDB connection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {str(e)}")
            self.client = None
            self.db = None

    def _is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        return self.client is not None and self.db is not None

    async def store_conversation(self, session_id: str, data: Dict[str, Any]):
        """Store conversation data"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, skipping persistent storage")
            return

        try:
            # Add timestamp and ensure session_id
            data['timestamp'] = datetime.utcnow()
            data['session_id'] = session_id

            await self.db.conversations.update_one(
                {'session_id': session_id},
                {'$set': data},
                upsert=True
            )
            logger.info(f"Stored conversation data for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")

    async def store_message(self, session_id: str, message: Dict[str, Any]):
        """Store a message in the conversation history"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, skipping persistent storage")
            return

        try:
            message['timestamp'] = datetime.utcnow()
            message['session_id'] = session_id

            # Remove write_concern from insert_one
            await self.db.messages.insert_one(message)
            logger.info(f"Stored message for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            return None

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve conversation history"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, returning empty history")
            return []

        try:
            # Add maxTimeMS to limit query execution time
            cursor = self.db.messages.find(
                {'session_id': session_id}
            ).sort('timestamp', -1).limit(limit)
            cursor.max_time_ms(5000)  # 5 seconds timeout
            
            messages = await cursor.to_list(length=limit)
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []

    async def store_context(self, session_id: str, context_data: Dict[str, Any]):
        """Store context information"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, skipping context storage")
            return

        try:
            context_data['timestamp'] = datetime.utcnow()
            context_data['session_id'] = session_id

            # Remove write_concern from update_one
            await self.db.context.update_one(
                {'session_id': session_id},
                {'$set': context_data},
                upsert=True
            )
            logger.info(f"Stored context for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing context: {str(e)}")
            return None

    async def get_context(self, session_id: str) -> Optional[Dict]:
        """Retrieve context information"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, returning None for context")
            return None

        try:
            context = await self.db.context.find_one({'session_id': session_id})
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return None

    async def store_knowledge_base_entry(self, entry: Dict[str, Any]):
        """Store an entry in the knowledge base"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, skipping knowledge base entry")
            return

        try:
            entry['timestamp'] = datetime.utcnow()
            await self.db.knowledge_base.insert_one(entry)
            logger.info("Stored new knowledge base entry")
        except Exception as e:
            logger.error(f"Error storing knowledge base entry: {str(e)}")

    async def search_knowledge_base(self, query: str, threshold: float = 0.7) -> List[Dict]:
        """Search the knowledge base for relevant entries"""
        if not self._is_connected():
            logger.warning("MongoDB not connected, returning empty search results")
            return []

        try:
            # Using MongoDB's text search
            cursor = self.db.knowledge_base.find(
                {
                    '$text': {'$search': query}
                },
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})])

            results = await cursor.to_list(length=5)
            return [r for r in results if r.get('score', 0) >= threshold]
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return []

    async def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed") 