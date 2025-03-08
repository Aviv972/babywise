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
from typing import Any, Dict, Optional, Callable, ForwardRef, cast

# Configure logging
logger = logging.getLogger(__name__)

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
    
    # Apply ForwardRef patch
    results["forward_ref_patch"] = apply_forward_ref_patch()
    
    # Log overall results
    success_count = sum(1 for success in results.values() if success)
    logger.info(f"Applied {success_count}/{len(results)} compatibility patches")
    
    return results

# Apply all patches when the module is imported
patch_results = apply_all_patches() 