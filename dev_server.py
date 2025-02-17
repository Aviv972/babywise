import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables from .env file for local development
load_dotenv()

# Verify environment variables are loaded
required_vars = ['OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'MODEL_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

if __name__ == "__main__":
    print("Starting development server...")
    print(f"Environment variables loaded: {', '.join(required_vars)}")
    uvicorn.run("src.server:app", host="0.0.0.0", port=8004, reload=True) 