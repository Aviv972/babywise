"""
Babywise Assistant - Compatibility Module

This module provides compatibility fixes for various Python version and dependency issues.
It follows the project's asynchronous programming guidelines and provides proper error handling.

Usage:
    import api.compatibility  # This will apply all necessary patches
"""

import sys
import os
import logging
import inspect
import types
from typing import Any, Dict, Optional, Callable, ForwardRef, cast
import traceback

# Configure logging
logger = logging.getLogger(__name__)

def setup_environment():
    """Set environment variables directly for read-only environments and patch dotenv."""
    os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    os.environ.setdefault("STORAGE_URL", os.environ.get("STORAGE_URL", ""))

    try:
        import dotenv

        def patched_load_dotenv(*args, **kwargs):
            logger.info("Patched load_dotenv called (no-op).")
            return True

        dotenv.load_dotenv = patched_load_dotenv
        logger.info("dotenv.load_dotenv successfully patched.")
    except ImportError:
        logger.info("dotenv not installed; no patch needed.")

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
            "is_multiple_classes": False,
            "python_version": sys.version
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

def patch_python312_forwardref() -> bool:
    """
    Apply a specific patch for Python 3.12's ForwardRef implementation.
    
    In Python 3.12, the ForwardRef._evaluate method signature changed,
    causing compatibility issues with older libraries like pydantic v1.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        # Only apply this patch for Python 3.12+
        if sys.version_info < (3, 12):
            logger.info("Python version is below 3.12, skipping Python 3.12 ForwardRef patch")
            return False
            
        logger.info("Applying Python 3.12 ForwardRef patch")
        
        # First, let's patch pydantic's evaluate_forwardref function directly
        try:
            import pydantic.typing
            
            # Store the original function
            original_evaluate_forwardref = pydantic.typing.evaluate_forwardref
            
            # Define a new implementation that's compatible with Python 3.12
            def patched_evaluate_forwardref(ref, globalns, localns):
                """
                Patched version of pydantic.typing.evaluate_forwardref that's compatible with Python 3.12.
                """
                logger.info(f"[PATCH] pydantic.typing.evaluate_forwardref called for {ref}")
                
                # Get the _name attribute from the ForwardRef
                name = getattr(ref, '_name', None)
                if name is None:
                    # Fall back to the original implementation
                    logger.info(f"[PATCH] No _name attribute found, falling back to original implementation")
                    return original_evaluate_forwardref(ref, globalns, localns)
                
                # Try to evaluate the name directly from the namespace
                if name in globalns:
                    logger.info(f"[PATCH] Found '{name}' in globalns, returning directly")
                    return globalns[name]
                if name in localns:
                    logger.info(f"[PATCH] Found '{name}' in localns, returning directly")
                    return localns[name]
                
                # If we can't find it, fall back to the original implementation
                logger.info(f"[PATCH] Could not find '{name}' in namespaces, falling back to original implementation")
                return original_evaluate_forwardref(ref, globalns, localns)
            
            # Replace the function
            pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref
            logger.info("Successfully patched pydantic.typing.evaluate_forwardref")
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not patch pydantic.typing.evaluate_forwardref: {str(e)}")
        
        # Now, let's also patch typing.ForwardRef._evaluate
        # Get the original ForwardRef._evaluate method
        original_evaluate = ForwardRef._evaluate
        
        # Define a new implementation that handles the recursive_guard parameter correctly
        def new_evaluate(self, globalns, localns, recursive_guard=None):
            """
            Patched version of ForwardRef._evaluate that handles the recursive_guard parameter correctly.
            This works with both Pydantic v1 and Python 3.12.
            """
            logger.info(f"[PATCH] ForwardRef._evaluate called for {self.__forward_arg__}")
            
            # If recursive_guard is None, create a new set
            if recursive_guard is None:
                recursive_guard = set()
            
            # Check if we're in a recursive loop
            if self.__forward_arg__ in recursive_guard:
                logger.info(f"[PATCH] Recursive reference detected for {self.__forward_arg__}")
                return None
            
            # Add the current forward reference to the recursive guard
            recursive_guard.add(self.__forward_arg__)
            
            # Try to evaluate the forward reference
            try:
                # First, try to evaluate using the original method
                try:
                    # Call the original method with the recursive_guard parameter
                    logger.info(f"[PATCH] Attempting to evaluate {self.__forward_arg__} using original method")
                    return original_evaluate(self, globalns, localns, recursive_guard)
                except TypeError as e:
                    # If we get a TypeError, it might be because the original method doesn't accept recursive_guard
                    if "got multiple values for argument 'recursive_guard'" in str(e):
                        logger.info(f"[PATCH] TypeError with recursive_guard, using direct evaluation for {self.__forward_arg__}")
                        # Try to evaluate the forward reference directly
                        if self.__forward_arg__ in globalns:
                            logger.info(f"[PATCH] Found {self.__forward_arg__} in globalns")
                            return globalns[self.__forward_arg__]
                        if self.__forward_arg__ in localns:
                            logger.info(f"[PATCH] Found {self.__forward_arg__} in localns")
                            return localns[self.__forward_arg__]
                        # If we can't find it, try to evaluate it as an expression
                        logger.info(f"[PATCH] Evaluating {self.__forward_arg__} as an expression")
                        return eval(self.__forward_arg__, globalns, localns)
                    else:
                        # If it's a different TypeError, re-raise it
                        logger.info(f"[PATCH] Unexpected TypeError: {e}")
                        raise
            except Exception as e:
                # If we get any other exception, log it and re-raise
                logger.info(f"[PATCH] Exception during evaluation: {e}")
                raise
            finally:
                # Remove the current forward reference from the recursive guard
                recursive_guard.remove(self.__forward_arg__)
        
        # Replace the method
        ForwardRef._evaluate = new_evaluate
        logger.info("Successfully applied Python 3.12 ForwardRef patch")
        return True
        
    except Exception as e:
        logger.error(f"Failed to apply Python 3.12 ForwardRef patch: {str(e)}")
        logger.error(traceback.format_exc())
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
        
        # Create StrictVersion class
        class StrictVersion:
            def __init__(self, version_string):
                self.version_string = version_string
                # Parse version string into components
                components = version_string.split('.')
                self.version = tuple(map(int, components))
                
            def __str__(self):
                return self.version_string
                
            def __repr__(self):
                return f"StrictVersion('{self.version_string}')"
                
            def __eq__(self, other):
                if isinstance(other, str):
                    return self.version_string == other
                return self.version == other.version
                
            def __lt__(self, other):
                if isinstance(other, str):
                    other = StrictVersion(other)
                return self.version < other.version
                
            def __gt__(self, other):
                if isinstance(other, str):
                    other = StrictVersion(other)
                return self.version > other.version
        
        # Add version classes to the mock module
        mock_version.LooseVersion = LooseVersion
        mock_version.StrictVersion = StrictVersion
        
        # Create distutils.errors submodule
        mock_errors = types.ModuleType('distutils.errors')
        sys.modules['distutils.errors'] = mock_errors
        
        # Add common error classes
        class DistutilsError(Exception): pass
        class DistutilsModuleError(DistutilsError): pass
        class DistutilsExecError(DistutilsError): pass
        class DistutilsPlatformError(DistutilsError): pass
        class DistutilsSetupError(DistutilsError): pass
        class DistutilsArgError(DistutilsError): pass
        class DistutilsFileError(DistutilsError): pass
        class DistutilsOptionError(DistutilsError): pass
        class DistutilsInternalError(DistutilsError): pass
        
        mock_errors.DistutilsError = DistutilsError
        mock_errors.DistutilsModuleError = DistutilsModuleError
        mock_errors.DistutilsExecError = DistutilsExecError
        mock_errors.DistutilsPlatformError = DistutilsPlatformError
        mock_errors.DistutilsSetupError = DistutilsSetupError
        mock_errors.DistutilsArgError = DistutilsArgError
        mock_errors.DistutilsFileError = DistutilsFileError
        mock_errors.DistutilsOptionError = DistutilsOptionError
        mock_errors.DistutilsInternalError = DistutilsInternalError
        
        # Create distutils.util submodule
        mock_util = types.ModuleType('distutils.util')
        sys.modules['distutils.util'] = mock_util
        
        # Add common utility functions
        def strtobool(val):
            """Convert a string representation of truth to true (1) or false (0).
            
            True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
            are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
            'val' is anything else.
            """
            val = val.lower()
            if val in ('y', 'yes', 't', 'true', 'on', '1'):
                return 1
            elif val in ('n', 'no', 'f', 'false', 'off', '0'):
                return 0
            else:
                raise ValueError(f"invalid truth value {val!r}")
        
        mock_util.strtobool = strtobool
        
        # Create distutils.sysconfig submodule
        mock_sysconfig = types.ModuleType('distutils.sysconfig')
        sys.modules['distutils.sysconfig'] = mock_sysconfig
        
        # Add common sysconfig functions
        def get_python_lib(plat_specific=0, standard_lib=0, prefix=None):
            """Return the directory for site-packages."""
            import site
            if standard_lib:
                return site.getsitepackages()[0]
            else:
                return site.getusersitepackages()
        
        mock_sysconfig.get_python_lib = get_python_lib
        
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
    
    # Set up environment variables and patch dotenv for read-only environments
    try:
        setup_environment()
        results["environment_setup"] = True
    except Exception as e:
        logger.error(f"Failed to set up environment: {str(e)}")
        results["environment_setup"] = False
    
    # Apply Python 3.12 ForwardRef patch
    results["python312_forwardref_patch"] = patch_python312_forwardref()
    
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