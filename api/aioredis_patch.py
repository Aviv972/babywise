#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Patch for aioredis to fix incompatibility with Python 3.12.
This file is designed to be imported at the very beginning of the application.
"""

import sys
import logging
import traceback

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
        import types
        aioredis_exceptions = types.ModuleType('aioredis.exceptions')
        
        # Create base exception classes
        class RedisError(Exception): pass
        aioredis_exceptions.RedisError = RedisError
        logger.info("Created RedisError base class")
        
        # Create the patched TimeoutError
        if asyncio.TimeoutError is builtins.TimeoutError:
            # If they're the same, only use one of them
            class TimeoutError(asyncio.TimeoutError, RedisError): pass
        else:
            # If they're different (shouldn't happen in 3.12+, but just in case)
            class TimeoutError(asyncio.TimeoutError, builtins.TimeoutError, RedisError): pass
        
        aioredis_exceptions.TimeoutError = TimeoutError
        logger.info("Created TimeoutError class")
        
        # Add other necessary exception classes
        class ConnectionError(RedisError): pass
        class ProtocolError(RedisError): pass
        class WatchError(RedisError): pass
        class ConnectionClosedError(ConnectionError): pass
        class PoolClosedError(ConnectionError): pass
        class AuthenticationError(ConnectionError): pass
        class ResponseError(RedisError): pass
        class DataError(RedisError): pass
        class PubSubError(RedisError): pass
        class ExecAbortError(ResponseError): pass
        class ReadOnlyError(ResponseError): pass
        class NoScriptError(ResponseError): pass
        class ScriptError(ResponseError): pass
        class BusyLoadingError(ResponseError): pass
        class InvalidResponse(RedisError): pass
        class NotSupportedError(RedisError): pass
        class ClusterError(RedisError): pass
        class ClusterDownError(ClusterError): pass
        class ClusterCrossSlotError(ClusterError): pass
        
        # Register all exception classes
        aioredis_exceptions.ConnectionError = ConnectionError
        aioredis_exceptions.ProtocolError = ProtocolError
        aioredis_exceptions.WatchError = WatchError
        aioredis_exceptions.ConnectionClosedError = ConnectionClosedError
        aioredis_exceptions.PoolClosedError = PoolClosedError
        aioredis_exceptions.AuthenticationError = AuthenticationError
        aioredis_exceptions.ResponseError = ResponseError
        aioredis_exceptions.DataError = DataError
        aioredis_exceptions.PubSubError = PubSubError
        aioredis_exceptions.ExecAbortError = ExecAbortError
        aioredis_exceptions.ReadOnlyError = ReadOnlyError
        aioredis_exceptions.NoScriptError = NoScriptError
        aioredis_exceptions.ScriptError = ScriptError
        aioredis_exceptions.BusyLoadingError = BusyLoadingError
        aioredis_exceptions.InvalidResponse = InvalidResponse
        aioredis_exceptions.NotSupportedError = NotSupportedError
        aioredis_exceptions.ClusterError = ClusterError
        aioredis_exceptions.ClusterDownError = ClusterDownError
        aioredis_exceptions.ClusterCrossSlotError = ClusterCrossSlotError
        
        logger.info("Created and registered all exception classes")
        
        # Verify AuthenticationError is properly registered
        if hasattr(aioredis_exceptions, 'AuthenticationError'):
            logger.info(f"AuthenticationError is registered: {aioredis_exceptions.AuthenticationError}")
        else:
            logger.error("AuthenticationError is NOT registered!")
        
        # Register the module
        sys.modules['aioredis.exceptions'] = aioredis_exceptions
        
        # Verify the module is registered
        if 'aioredis.exceptions' in sys.modules:
            logger.info("aioredis.exceptions module is registered in sys.modules")
        else:
            logger.error("aioredis.exceptions module is NOT registered in sys.modules!")
        
        # Verify we can import from the patched module
        try:
            from aioredis.exceptions import AuthenticationError as TestAuthError
            logger.info(f"Successfully imported AuthenticationError from patched module: {TestAuthError}")
        except ImportError as e:
            logger.error(f"Failed to import AuthenticationError from patched module: {e}")
        
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