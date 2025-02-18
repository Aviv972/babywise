from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional, Any
import os
import logging
from datetime import datetime
import json
import asyncio

logger = logging.getLogger(__name__)

class PersistentStorage:
    def __init__(self):
        self.client = None
        self.db = None
        # Create event loop for initialization
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._initialize_db())

    async def _initialize_db(self):
        """Initialize MongoDB connection"""
        try:
            mongodb_url = os.environ.get('MONGODB_URI')
            if not mongodb_url:
                logger.warning("MongoDB URI not found in environment variables")
                return

            # Configure MongoDB connection based on official documentation
            self.client = AsyncIOMotorClient(
                mongodb_url,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
                maxPoolSize=50,
                retryWrites=True,
                tls=True,
                tlsAllowInvalidCertificates=False,
                tlsAllowInvalidHostnames=False,
            )
            
            # Test the connection
            self.db = self.client.get_database('babywise')
            
            # Log connection info - use await for async operations
            server_info = await self.client.server_info()
            if server_info:
                logger.info("MongoDB connection initialized successfully")
                
                # Log security info if available
                if 'security' in server_info:
                    ssl_info = server_info['security'].get('SSLServerSubjectName')
                    if ssl_info:
                        logger.info(f"Connected with SSL to: {ssl_info}")
                        
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {str(e)}")
            self.client = None
            self.db = None

    async def _is_connected(self) -> bool:
        """Check if MongoDB is connected and verify TLS configuration"""
        if not self.client or not self.db:
            return False
            
        try:
            # Verify connection and TLS configuration - use await
            server_info = await self.client.admin.command('serverStatus')
            if server_info and 'security' in server_info:
                ssl_info = server_info['security'].get('SSLServerSubjectName')
                if ssl_info:
                    logger.debug(f"Connected to MongoDB with SSL subject: {ssl_info}")
            return True
        except Exception as e:
            logger.warning(f"MongoDB connection check failed: {str(e)}")
            return False

    async def store_conversation(self, session_id: str, data: Dict[str, Any]):
        """Store conversation data"""
        if not await self._is_connected():
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
        if not await self._is_connected():
            logger.warning("MongoDB not connected, skipping persistent storage")
            return

        try:
            message['timestamp'] = datetime.utcnow()
            message['session_id'] = session_id

            await self.db.messages.insert_one(message)
            logger.debug(f"Stored message for session {session_id}")
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            return None

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve conversation history"""
        if not await self._is_connected():
            logger.warning("MongoDB not connected, returning empty history")
            return []

        try:
            cursor = self.db.messages.find(
                {'session_id': session_id}
            ).sort('timestamp', -1).limit(limit)
            
            messages = await cursor.to_list(length=limit)
            return messages
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []

    async def store_context(self, session_id: str, context_data: Dict[str, Any]):
        """Store context information"""
        if not await self._is_connected():
            logger.warning("MongoDB not connected, skipping context storage")
            return

        try:
            context_data['timestamp'] = datetime.utcnow()
            context_data['session_id'] = session_id

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
        if not await self._is_connected():
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
        if not await self._is_connected():
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
        if not await self._is_connected():
            logger.warning("MongoDB not connected, returning empty search results")
            return []

        try:
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