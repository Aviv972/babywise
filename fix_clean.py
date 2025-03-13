#!/usr/bin/env python3
"""
Script to create a clean version of api/index.py with no duplications.
"""

# Read the current content of api/index.py
with open('api/index.py', 'r') as f:
    lines = f.readlines()

# Find the lines we want to modify
env_file_section_start = None
env_file_section_end = None

for i, line in enumerate(lines):
    if "Create a mock .env file" in line:
        env_file_section_start = i
    elif env_file_section_start is not None and "# Import compatibility module" in line:
        env_file_section_end = i
        break

# Replace the .env file creation code with our new comment
if env_file_section_start is not None and env_file_section_end is not None:
    modified_lines = lines[:env_file_section_start]
    modified_lines.append("# The compatibility module will handle environment setup for read-only filesystems\n\n")
    modified_lines.extend(lines[env_file_section_end:])
    
    # Remove any duplicate comments about the compatibility module
    clean_lines = []
    skip_next = False
    for i, line in enumerate(modified_lines):
        if skip_next:
            skip_next = False
            continue
        
        if "# The compatibility module will handle environment" in line:
            # Check if the next line is also a comment about the compatibility module
            if i+1 < len(modified_lines) and "# The compatibility module will handle environment" in modified_lines[i+1]:
                skip_next = True
        
        clean_lines.append(line)
    
    # Write the modified content to a new file
    with open('api/index.py.clean', 'w') as f:
        f.writelines(clean_lines)
    
    print(f"Successfully created a clean version of api/index.py")
    print(f"Original lines {env_file_section_start} to {env_file_section_end-1} were replaced with a comment")
    print("Changes have been written to api/index.py.clean")
    print("To apply the changes, run:")
    print("  cp api/index.py.clean api/index.py")
else:
    print("Could not find the .env file creation code in api/index.py") 