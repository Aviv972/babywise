#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Patch for aioredis compatibility with Python 3.12
"""

import sys
import logging
import traceback
from types import ModuleType

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def apply_patch():
    """Apply patches for aioredis compatibility."""
    try:
        # Create module to hold patched exceptions
        aioredis_exceptions = ModuleType('aioredis.exceptions')
        
        # Define base exception classes
        class RedisError(Exception):
            """Base exception for Redis errors"""
            pass

        class ConnectionError(RedisError):
            """Connection related errors"""
            pass

        class TimeoutError(RedisError):
            """Redis operation timeout"""
            pass

        class AuthenticationError(ConnectionError):
            """Authentication failed"""
            pass

        class AuthenticationWrongNumberOfArgsError(AuthenticationError):
            """Authentication failed due to wrong number of arguments"""
            pass

        class BusyLoadingError(ConnectionError):
            """Redis server is busy loading data"""
            pass

        class InvalidResponse(RedisError):
            """Invalid response from Redis"""
            pass

        class ResponseError(RedisError):
            """Redis command error"""
            pass

        class DataError(RedisError):
            """Invalid data format"""
            pass

        class PubSubError(RedisError):
            """Pub/Sub operation errors"""
            pass

        class WatchError(RedisError):
            """Watch command failed"""
            pass

        class NoScriptError(ResponseError):
            """Script does not exist"""
            pass

        class ExecAbortError(ResponseError):
            """Transaction aborted"""
            pass

        class ReadOnlyError(ResponseError):
            """Read only mode"""
            pass

        class NoPermissionError(ResponseError):
            """No permission to execute command"""
            pass

        class ModuleError(ResponseError):
            """Module command failed"""
            pass

        class LockError(RedisError):
            """Lock operation failed"""
            pass

        class LockNotOwnedError(LockError):
            """Lock is not owned by this client"""
            pass

        class ChildDeadlockedError(RedisError):
            """Child process deadlocked"""
            pass

        class ChannelError(RedisError):
            """Channel operation failed"""
            pass

        class MaxClientsError(ConnectionError):
            """Too many clients error"""
            pass

        class ConnectionClosedError(ConnectionError):
            """Connection was closed"""
            pass

        class ProtocolError(RedisError):
            """Protocol parsing error"""
            pass

        class ReplicationError(RedisError):
            """Replication error"""
            pass

        class MasterDownError(ReplicationError):
            """Master is down"""
            pass

        class SlaveError(ReplicationError):
            """Slave error"""
            pass

        # Register all exception classes in the module
        exception_classes = [
            RedisError,
            ConnectionError,
            TimeoutError,
            AuthenticationError,
            AuthenticationWrongNumberOfArgsError,
            BusyLoadingError,
            InvalidResponse,
            ResponseError,
            DataError,
            PubSubError,
            WatchError,
            NoScriptError,
            ExecAbortError,
            ReadOnlyError,
            NoPermissionError,
            ModuleError,
            LockError,
            LockNotOwnedError,
            ChildDeadlockedError,
            ChannelError,
            MaxClientsError,
            ConnectionClosedError,
            ProtocolError,
            ReplicationError,
            MasterDownError,
            SlaveError
        ]

        for cls in exception_classes:
            setattr(aioredis_exceptions, cls.__name__, cls)
            logger.debug(f"Registered exception class: {cls.__name__}")

        # Register the patched module
        sys.modules['aioredis.exceptions'] = aioredis_exceptions
        
        # Verify the patch by importing critical exceptions
        try:
            from aioredis.exceptions import (
                AuthenticationWrongNumberOfArgsError,
                AuthenticationError,
                ConnectionError,
                TimeoutError,
                BusyLoadingError,
                InvalidResponse,
                ResponseError,
                DataError,
                PubSubError,
                WatchError,
                ChildDeadlockedError
            )
            logger.info("Successfully verified critical exception imports")
            return True
        except ImportError as e:
            logger.error(f"Failed to verify exception imports after patching: {e}")
            logger.error(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f"Error applying aioredis patch: {e}")
        logger.error(traceback.format_exc())
        return False

# Apply the patch and store the result
patch_result = apply_patch()

if patch_result:
    logger.info("Successfully applied aioredis patch")
else:
    logger.error("Failed to apply aioredis patch")

# Export the patch result for other modules to check
__all__ = ['patch_result'] 