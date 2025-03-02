#!/usr/bin/env python3
"""
Test script for command parser
"""

import sys
from backend.workflow.command_parser import detect_command

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_command_parser.py \"message\" [language]")
        sys.exit(1)
    
    message = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Testing command detection for message: '{message}'")
    if language:
        print(f"Specified language: {language}")
    
    command = detect_command(message)
    
    if command:
        print("Command detected:")
        for key, value in command.items():
            print(f"  {key}: {value}")
    else:
        print("No command detected")

if __name__ == "__main__":
    main() 