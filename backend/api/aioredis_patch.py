#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced patch for aioredis compatibility with Python 3.12
- Patches missing distutils module
- Provides StrictVersion implementation
- Handles aioredis exceptions
"""

import sys
import logging
import traceback
import re
from types import ModuleType

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# IMPORTANT: Create and install patches BEFORE any imports of the affected modules

# Create distutils module structure
def create_distutils_modules():
    """Create the entire distutils module structure with the StrictVersion replacement"""
    # StrictVersion compatibility implementation
    class StrictVersion:
        """
        A compatibility implementation of distutils.version.StrictVersion
        for Python 3.12 which removed the distutils module.
        
        This implementation follows the same interface as the original StrictVersion
        but is simplified to only support the operations needed by aioredis.
        """
        version_re = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')

        def __init__(self, version_string):
            self.parse(version_string)

        def parse(self, version_string):
            match = self.version_re.match(version_string)
            if not match:
                raise ValueError(f"Invalid version number '{version_string}'")
            
            self.version = tuple(map(int, match.groups()))
            self.major, self.minor, self.patch = self.version

        def __str__(self):
            return f"{self.major}.{self.minor}.{self.patch}"

        def __repr__(self):
            return f"StrictVersion('{self}')"

        def __eq__(self, other):
            if isinstance(other, str):
                other = StrictVersion(other)
            return self.version == other.version

        def __lt__(self, other):
            if isinstance(other, str):
                other = StrictVersion(other)
            return self.version < other.version

        def __le__(self, other):
            if isinstance(other, str):
                other = StrictVersion(other)
            return self.version <= other.version

        def __gt__(self, other):
            if isinstance(other, str):
                other = StrictVersion(other)
            return self.version > other.version

        def __ge__(self, other):
            if isinstance(other, str):
                other = StrictVersion(other)
            return self.version >= other.version

    # Create all needed modules in the hierarchy
    modules = {
        'distutils': ModuleType('distutils'),
        'distutils.version': ModuleType('distutils.version'),
        'distutils.util': ModuleType('distutils.util'),
    }
    
    # Add StrictVersion to distutils.version
    modules['distutils.version'].StrictVersion = StrictVersion
    
    # Add stubs for any other potentially required functions/classes
    def stub_function(*args, **kwargs):
        """Stub function that does nothing but log a warning"""
        logger.warning(f"Stub function called with args={args}, kwargs={kwargs}")
        return None
        
    # Add stub functions to distutils.util if needed
    modules['distutils.util'].strtobool = lambda s: True if s.lower() in ('y', 'yes', 't', 'true', 'on', '1') else False
    
    # Register all modules
    for name, module in modules.items():
        if name not in sys.modules:
            sys.modules[name] = module
            logger.info(f"Registered synthetic module: {name}")

    # Return the created modules for testing
    return modules

def create_aioredis_exceptions():
    """Create and register the aioredis.exceptions module"""
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
        
    # Register the patched module
    if 'aioredis.exceptions' not in sys.modules:
        sys.modules['aioredis.exceptions'] = aioredis_exceptions
        logger.info("Registered synthetic module: aioredis.exceptions")
    
    return aioredis_exceptions

def apply_patches():
    """Apply all patches for aioredis compatibility with Python 3.12"""
    results = {"success": False, "errors": []}
    
    try:
        # Step 1: Create and register distutils modules
        logger.info("Creating distutils module hierarchy")
        distutils_modules = create_distutils_modules()
        
        # Test distutils.version.StrictVersion
        try:
            from distutils.version import StrictVersion
            test_version = StrictVersion("1.0.0")
            assert str(test_version) == "1.0.0"
            assert test_version < StrictVersion("2.0.0")
            logger.info("Successfully verified StrictVersion patch")
        except Exception as e:
            error_msg = f"StrictVersion patch verification failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
            
        # Step 2: Create and register aioredis.exceptions
        logger.info("Creating aioredis.exceptions module")
        aioredis_exceptions = create_aioredis_exceptions()
        
        # Test aioredis.exceptions
        try:
            from aioredis.exceptions import (
                AuthenticationError,
                ConnectionError,
                TimeoutError
            )
            logger.info("Successfully verified critical exception imports")
        except Exception as e:
            error_msg = f"aioredis.exceptions patch verification failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            results["errors"].append(error_msg)
        
        # Set success status based on errors
        results["success"] = len(results["errors"]) == 0
        
        # Log results
        if results["success"]:
            logger.info("All patches successfully applied and verified")
        else:
            logger.error(f"Patches applied with {len(results['errors'])} errors")
            
    except Exception as e:
        error_msg = f"Unexpected error applying patches: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        results["errors"].append(error_msg)
        results["success"] = False
        
    return results

# Apply patches immediately on module import
patch_results = apply_patches()

# Export the patch results for other modules to check
__all__ = ['patch_results'] 