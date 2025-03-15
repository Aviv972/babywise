#!/bin/bash
# Custom build script for Vercel deployment

echo "Starting custom build process..."

# Install core dependencies first
pip install --no-cache-dir fastapi==0.115.11 uvicorn==0.34.0 starlette==0.46.1 redis==5.2.1

# Install minimal LangChain components
pip install --no-cache-dir langchain-core==0.3.45 langchain-openai==0.3.8 langgraph==0.3.11

# Install OpenAI
pip install --no-cache-dir openai==1.66.3

# Install database dependencies
pip install --no-cache-dir sqlalchemy==2.0.39 aiosqlite==0.21.0

# Install web related dependencies
pip install --no-cache-dir python-multipart==0.0.20 python-jose==3.4.0 passlib==1.7.4 httpx==0.28.1 jinja2==3.1.6 aiofiles==24.1.0

# Install utilities
pip install --no-cache-dir python-dotenv==1.0.1 typing-extensions==4.12.2

# Cleanup pip cache
pip cache purge

echo "Custom build completed successfully!" 