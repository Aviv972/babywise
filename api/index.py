from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import os

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Verify environment variables before importing app
print("\n=== Vercel Environment Check ===")
required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'MODEL_NAME']
for var in required_vars:
    value = os.getenv(var)
    is_present = bool(value)
    print(f"{var} present: {is_present}")
    if not is_present:
        print(f"Warning: {var} is missing!")

try:
    from src.server import app
    print("Successfully imported FastAPI app")
except Exception as e:
    print(f"Error importing app: {str(e)}")
    raise

# This file is used by Vercel as the entry point
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Export for Vercel
app = app 