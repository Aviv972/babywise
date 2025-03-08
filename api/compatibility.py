"""
Babywise Assistant - Compatibility Module

This module provides compatibility fixes for various Python version and dependency issues.
It follows the project's asynchronous programming guidelines and provides proper error handling.

Usage:
    import api.compatibility  # This will apply all necessary patches
"""

import sys
import logging
import inspect
import types
from typing import Any, Dict, Optional, Callable, ForwardRef, cast

# Configure logging
logger = logging.getLogger(__name__)

def diagnose_forward_ref_classes() -> Dict[str, Any]:
    """
    Diagnose if there are multiple ForwardRef classes in the environment.
    
    This function checks various modules that might define or import ForwardRef
    to identify potential conflicts.
    
    Returns:
        Dict[str, Any]: Diagnostic information about ForwardRef classes
    """
    try:
        logger.info("Diagnosing ForwardRef classes in the environment")
        
        # Initialize results
        results = {
            "modules_with_forward_ref": [],
            "forward_ref_classes": [],
            "evaluate_signatures": [],
            "is_multiple_classes": False
        }
        
        # Check typing module
        from typing import ForwardRef as TypingForwardRef
        results["modules_with_forward_ref"].append("typing")
        results["forward_ref_classes"].append(str(TypingForwardRef))
        
        if hasattr(TypingForwardRef, "_evaluate"):
            sig = str(inspect.signature(TypingForwardRef._evaluate))
            results["evaluate_signatures"].append(f"typing.ForwardRef._evaluate{sig}")
        
        # Check if pydantic.typing imports a different ForwardRef
        try:
            import pydantic.typing
            if hasattr(pydantic.typing, "ForwardRef"):
                pydantic_fr = pydantic.typing.ForwardRef
                results["modules_with_forward_ref"].append("pydantic.typing")
                results["forward_ref_classes"].append(str(pydantic_fr))
                
                if hasattr(pydantic_fr, "_evaluate"):
                    sig = str(inspect.signature(pydantic_fr._evaluate))
                    results["evaluate_signatures"].append(f"pydantic.typing.ForwardRef._evaluate{sig}")
                
                # Check if they're the same class
                results["is_same_as_typing"] = (pydantic_fr is TypingForwardRef)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not check pydantic.typing.ForwardRef: {str(e)}")
        
        # Check if there are multiple ForwardRef classes
        unique_classes = set(results["forward_ref_classes"])
        results["is_multiple_classes"] = (len(unique_classes) > 1)
        
        # Log findings
        if results["is_multiple_classes"]:
            logger.warning(f"Found multiple ForwardRef classes: {results['forward_ref_classes']}")
        else:
            logger.info("Found single ForwardRef class")
            
        logger.info(f"ForwardRef signatures: {results['evaluate_signatures']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error diagnosing ForwardRef classes: {str(e)}")
        return {"error": str(e)}

def apply_direct_pydantic_patch() -> bool:
    """
    Apply a direct patch to pydantic.typing.evaluate_forwardref.
    
    This completely replaces the function with a custom implementation that
    handles the recursive_guard parameter correctly.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        logger.info("Applying direct patch to pydantic.typing.evaluate_forwardref")
        
        # Import pydantic.typing
        import pydantic.typing
        from typing import cast, Any, ForwardRef
        
        # Define a completely new implementation
        def safe_evaluate_forwardref(type_, globalns, localns):
            """
            Safe implementation of evaluate_forwardref that handles the recursive_guard parameter.
            
            This is a complete replacement for pydantic.typing.evaluate_forwardref that
            works with both older and newer versions of Python.
            """
            logger.debug(f"Safe evaluate_forwardref called for {type_}")
            
            try:
                # Try to call _evaluate with recursive_guard as a keyword argument
                return cast(Any, type_)._evaluate(globalns, localns, recursive_guard=set())
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    # If recursive_guard is not accepted as a keyword, try without it
                    logger.debug("Falling back to _evaluate without recursive_guard")
                    return cast(Any, type_)._evaluate(globalns, localns)
                else:
                    # Re-raise other TypeErrors
                    raise
        
        # Replace the function
        pydantic.typing.evaluate_forwardref = safe_evaluate_forwardref
        logger.info("Successfully applied direct patch to pydantic.typing.evaluate_forwardref")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply direct pydantic patch: {str(e)}")
        return False

def patch_distutils() -> bool:
    """
    Create a mock distutils module if it's missing.
    
    This is needed for Python 3.12+ where distutils was removed from the standard library.
    Many packages still depend on distutils, so we create a minimal mock implementation.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        # Check if distutils is already available
        try:
            import distutils
            logger.info("distutils module already exists, no patching needed")
            return True
        except ImportError:
            logger.info("distutils module not found, creating mock implementation")
            
        # Create a mock distutils module
        mock_distutils = types.ModuleType('distutils')
        mock_distutils.__path__ = []
        sys.modules['distutils'] = mock_distutils
        
        # Create distutils.version submodule
        mock_version = types.ModuleType('distutils.version')
        sys.modules['distutils.version'] = mock_version
        
        # Create LooseVersion class
        class LooseVersion:
            def __init__(self, version_string):
                self.version_string = version_string
                
            def __str__(self):
                return self.version_string
                
            def __repr__(self):
                return f"LooseVersion('{self.version_string}')"
                
            def __eq__(self, other):
                if isinstance(other, str):
                    return self.version_string == other
                return self.version_string == other.version_string
                
            def __lt__(self, other):
                if isinstance(other, str):
                    return self.version_string < other
                return self.version_string < other.version_string
                
            def __gt__(self, other):
                if isinstance(other, str):
                    return self.version_string > other
                return self.version_string > other.version_string
        
        # Add LooseVersion to the mock module
        mock_version.LooseVersion = LooseVersion
        
        # Create distutils.errors submodule
        mock_errors = types.ModuleType('distutils.errors')
        sys.modules['distutils.errors'] = mock_errors
        
        # Add common error classes
        class DistutilsError(Exception): pass
        class DistutilsModuleError(DistutilsError): pass
        class DistutilsExecError(DistutilsError): pass
        class DistutilsPlatformError(DistutilsError): pass
        
        mock_errors.DistutilsError = DistutilsError
        mock_errors.DistutilsModuleError = DistutilsModuleError
        mock_errors.DistutilsExecError = DistutilsExecError
        mock_errors.DistutilsPlatformError = DistutilsPlatformError
        
        logger.info("Successfully created mock distutils module")
        return True
        
    except Exception as e:
        logger.error(f"Failed to patch distutils: {str(e)}")
        return False

def apply_all_patches() -> Dict[str, bool]:
    """
    Apply all compatibility patches and return their status.
    
    Returns:
        Dict[str, bool]: Dictionary of patch names and their success status
    """
    results = {}
    
    # First run diagnostics
    diagnostics = diagnose_forward_ref_classes()
    logger.info(f"ForwardRef diagnostics: {diagnostics}")
    
    # Apply direct pydantic patch
    results["direct_pydantic_patch"] = apply_direct_pydantic_patch()
    
    # Apply distutils patch
    results["distutils_patch"] = patch_distutils()
    
    # Log overall results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Applied {success_count}/{len(results)} compatibility patches")
    
    return results

# Apply all patches when the module is imported
patch_results = apply_all_patches() 