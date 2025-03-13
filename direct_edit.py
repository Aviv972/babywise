#!/usr/bin/env python3
"""
Script to directly edit api/index.py to remove the .env file creation code.
"""

# Read the current content of api/index.py
with open('api/index.py', 'r') as f:
    lines = f.readlines()

# Find the lines with the .env file creation code
env_file_start = None
env_file_end = None

for i, line in enumerate(lines):
    if "Create a mock .env file" in line:
        env_file_start = i
        break

if env_file_start is not None:
    # Find the end of the .env file creation code
    for i in range(env_file_start + 1, len(lines)):
        if "# Import compatibility module" in lines[i]:
            env_file_end = i
            break

    if env_file_end is not None:
        # Replace the .env file creation code with a comment
        new_lines = lines[:env_file_start]
        new_lines.append("# The compatibility module will handle environment setup for read-only filesystems\n\n")
        new_lines.extend(lines[env_file_end:])
        
        # Write the modified content back to api/index.py
        with open('api/index.py', 'w') as f:
            f.writelines(new_lines)
        
        print(f"Successfully edited api/index.py")
        print(f"Removed lines {env_file_start} to {env_file_end-1} and replaced with a comment")
    else:
        print("Could not find the end of the .env file creation code")
else:
    print("Could not find the .env file creation code") 