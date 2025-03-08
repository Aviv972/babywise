# Babywise Split Deployment Strategy

## Overview

To overcome the limitations of Vercel's serverless environment with complex Python dependencies, we've implemented a split deployment strategy for the Babywise Assistant:

1. **Frontend Deployment (Current Repository)**
   - Static assets (HTML, CSS, JavaScript)
   - Lightweight API proxy for forwarding requests
   - Minimal dependencies for fast deployment

2. **Backend Deployment (Separate Repository)**
   - Full Python application with all dependencies
   - LangChain/LangGraph workflow
   - Database and Redis integration
   - Deployed to a separate Vercel project or alternative platform

## Implementation Details

### Frontend Proxy (This Repository)

The `api/index.py` file in this repository serves as a lightweight proxy that:

- Forwards API requests to the backend service
- Handles basic error scenarios
- Provides a health check endpoint
- Uses minimal dependencies (fastapi, httpx)

This approach allows the frontend to be deployed quickly on Vercel without the complexity of installing and initializing the full LangChain/LangGraph stack in a serverless function.

### Backend Service

The backend service (deployed separately) contains:

- The full Babywise Assistant implementation
- All required dependencies (LangChain, LangGraph, OpenAI, etc.)
- Database connections and Redis integration
- The complete workflow as described in the documentation

## Deployment Instructions

### Frontend Deployment (This Repository)

1. Deploy this repository to Vercel
2. Set the `BACKEND_URL` environment variable to point to your backend service
3. Verify that static assets are being served correctly
4. Test the API proxy functionality

### Backend Deployment

1. Create a separate repository for the backend code
2. Include all required dependencies in requirements.txt
3. Deploy to Vercel or an alternative platform that better supports complex Python dependencies
4. Set all required environment variables (OPENAI_API_KEY, REDIS_URL, etc.)
5. Verify that the backend API endpoints are accessible

## Benefits of This Approach

- **Faster Deployments**: Frontend changes can be deployed quickly without waiting for complex dependency installation
- **Improved Reliability**: Separating concerns reduces the risk of deployment failures
- **Better Resource Utilization**: The lightweight proxy uses minimal resources, while the backend can be scaled independently
- **Flexibility**: The backend can be moved to a more suitable platform if needed, without affecting the frontend

## Future Improvements

- Implement caching in the proxy to reduce load on the backend
- Add authentication between the proxy and backend
- Consider moving the backend to a container-based platform for better dependency management 