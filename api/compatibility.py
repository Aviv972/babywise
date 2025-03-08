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

def apply_pydantic_typing_patch() -> bool:
    """
    Apply patch for pydantic.typing.evaluate_forwardref to handle the 'recursive_guard' parameter.
    
    This fixes compatibility issues between newer Python versions and older Pydantic versions.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        logger.info("Attempting to patch pydantic.typing.evaluate_forwardref")
        
        # Import pydantic.typing
        import pydantic.typing
        
        # Get the original evaluate_forwardref function
        original_evaluate_forwardref = pydantic.typing.evaluate_forwardref
        
        # Define a patched version
        def patched_evaluate_forwardref(type_, globalns, localns):
            """
            Patched version of evaluate_forwardref that handles the recursive_guard parameter.
            
            This function intercepts calls to ForwardRef._evaluate and adds the recursive_guard
            parameter if it's missing.
            """
            # Get the original _evaluate method
            original_evaluate = type_._evaluate
            
            # Check if it needs patching (doesn't have recursive_guard parameter)
            try:
                signature = inspect.signature(original_evaluate)
                if "recursive_guard" not in signature.parameters:
                    logger.info("Patching ForwardRef._evaluate method")
                    
                    # Define a patched _evaluate method
                    def patched_evaluate(self, globalns, localns, recursive_guard=None):
                        if recursive_guard is None:
                            recursive_guard = set()
                        return original_evaluate(self, globalns, localns)
                    
                    # Replace the _evaluate method
                    type_.__class__._evaluate = patched_evaluate
            except Exception as e:
                logger.error(f"Error checking/patching _evaluate method: {str(e)}")
            
            # Call the original function with the potentially patched _evaluate method
            try:
                return original_evaluate_forwardref(type_, globalns, localns)
            except TypeError as e:
                # If we still get a TypeError about recursive_guard, try to handle it directly
                if "recursive_guard" in str(e):
                    logger.warning(f"Caught TypeError: {str(e)}, attempting direct call")
                    # Try to call _evaluate directly with the recursive_guard parameter
                    return type_._evaluate(globalns, localns, set())
                else:
                    # Re-raise other TypeErrors
                    raise
        
        # Replace the evaluate_forwardref function
        pydantic.typing.evaluate_forwardref = patched_evaluate_forwardref
        logger.info("Successfully patched pydantic.typing.evaluate_forwardref")
        return True
        
    except Exception as e:
        logger.error(f"Failed to patch pydantic.typing: {str(e)}")
        return False

def apply_forward_ref_patch() -> bool:
    """
    Apply patch for ForwardRef._evaluate to handle the 'recursive_guard' parameter.
    
    This fixes compatibility issues between newer Python versions and older Pydantic versions.
    
    Returns:
        bool: True if patch was applied successfully, False otherwise
    """
    try:
        logger.info("Checking if ForwardRef._evaluate needs patching")
        
        # Get the original _evaluate method
        original_evaluate = getattr(ForwardRef, "_evaluate", None)
        
        # Check if the method exists and needs patching
        if original_evaluate is None:
            logger.warning("ForwardRef._evaluate method not found")
            return False
            
        # Check if the method already has the recursive_guard parameter
        signature = inspect.signature(original_evaluate)
        if "recursive_guard" in signature.parameters:
            logger.info("ForwardRef._evaluate already has recursive_guard parameter, no patching needed")
            return True
            
        # Define the patched method
        def patched_evaluate(self, globalns, localns, recursive_guard=None):
            """
            Patched version of ForwardRef._evaluate that handles the recursive_guard parameter.
            
            Args:
                globalns: Global namespace
                localns: Local namespace
                recursive_guard: Set of seen ForwardRefs (default: None)
                
            Returns:
                The evaluated type
            """
            if recursive_guard is None:
                recursive_guard = set()
            return original_evaluate(self, globalns, localns)
        
        # Apply the patch
        ForwardRef._evaluate = patched_evaluate
        logger.info("Successfully patched ForwardRef._evaluate")
        return True
        
    except Exception as e:
        logger.error(f"Failed to patch ForwardRef._evaluate: {str(e)}")
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
    
    # Apply ForwardRef patch
    results["forward_ref_patch"] = apply_forward_ref_patch()
    
    # Apply pydantic.typing patch
    results["pydantic_typing_patch"] = apply_pydantic_typing_patch()
    
    # Log overall results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Applied {success_count}/{len(results)} compatibility patches")
    
    return results

# Apply all patches when the module is imported
patch_results = apply_all_patches() 