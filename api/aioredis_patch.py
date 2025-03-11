#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Patch for aioredis to fix incompatibility with Python 3.12.
This file is designed to be imported at the very beginning of the application.
"""

import sys
import logging
import traceback
from types import ModuleType

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

def apply_patch():
    """
    Apply patch for aioredis TimeoutError for Python 3.12 compatibility.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        import asyncio
        import builtins
        
        # Only apply this patch for Python 3.12+
        if sys.version_info < (3, 12):
            logger.info("Python version is below 3.12, skipping aioredis TimeoutError patch")
            return False
            
        logger.info("Pre-patching aioredis TimeoutError for Python 3.12 compatibility")
        
        # Create a module to hold our patched exceptions
        aioredis_exceptions = ModuleType('aioredis.exceptions')
        
        # Define base exception classes
        class RedisError(Exception):
            pass

        class ConnectionError(RedisError):
            pass

        class ProtocolError(RedisError):
            pass

        class WatchError(RedisError):
            pass

        class ConnectionClosedError(ConnectionError):
            pass

        class MaxClientsError(ConnectionError):
            pass

        class AuthenticationError(ConnectionError):
            pass

        class AuthenticationWrongNumberOfArgsError(AuthenticationError):
            pass

        class TimeoutError(RedisError):
            pass

        class BusyLoadingError(ConnectionError):
            pass

        class InvalidResponse(RedisError):
            pass

        class ResponseError(RedisError):
            pass

        class DataError(RedisError):
            pass

        class PubSubError(RedisError):
            pass

        class WatchVariableError(WatchError):
            pass

        # Register all exception classes in the module
        exception_classes = [
            RedisError,
            ConnectionError,
            ProtocolError,
            WatchError,
            ConnectionClosedError,
            MaxClientsError,
            AuthenticationError,
            AuthenticationWrongNumberOfArgsError,
            TimeoutError,
            BusyLoadingError,
            InvalidResponse,
            ResponseError,
            DataError,
            PubSubError,
            WatchVariableError
        ]

        for cls in exception_classes:
            setattr(aioredis_exceptions, cls.__name__, cls)

        # Register the patched module
        sys.modules['aioredis.exceptions'] = aioredis_exceptions
        
        # Verify the patch
        try:
            from aioredis.exceptions import AuthenticationWrongNumberOfArgsError
            logger.info(f"Successfully imported AuthenticationWrongNumberOfArgsError after patching: {AuthenticationWrongNumberOfArgsError}")
        except ImportError as e:
            logger.error(f"Failed to verify AuthenticationWrongNumberOfArgsError import after patching: {e}")
            logger.error(traceback.format_exc())
            return False

        logger.info("Successfully pre-patched aioredis.exceptions module")
        return True
    except Exception as e:
        logger.error(f"Failed to pre-patch aioredis: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Apply the patch when the module is imported
patch_result = apply_patch()
logger.info(f"aioredis patch result: {patch_result}")

# Export the patch result for other modules to check
__all__ = ['patch_result'] 