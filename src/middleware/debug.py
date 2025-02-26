from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import json

class DebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Debug response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        print(f"Response body: {json.loads(body)}")
        
        return response 