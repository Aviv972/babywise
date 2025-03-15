#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, Optional, Any, List
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import time
from datetime import datetime
import json

# Setup logging (Vercel logs will capture this)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Function to log message and return response
def log_and_respond(message, response_data):
    logger.info(message)
    return response_data

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Log request info
        logger.info(f"GET request to {path}")
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()
        
        # Health check endpoint
        if path == '/api/health':
            response = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "environment": {
                    "python_version": "3.12",
                }
            }
            
        # Redis test endpoint
        elif path == '/api/redis-test':
            response = {
                "status": "ok",
                "message": "Redis connection simulated successful in minimal API mode"
            }
            
        # Context endpoint
        elif path.startswith('/api/chat/context'):
            query_params = parse_qs(parsed_url.query)
            thread_id = query_params.get('thread_id', ['thread_12345'])[0]
            response = log_and_respond(
                f"Get context for thread: {thread_id}",
                {
                    "context": [],
                    "thread_id": thread_id
                }
            )
            
        # Routine events endpoint
        elif path.startswith('/api/routines/events'):
            query_params = parse_qs(parsed_url.query)
            thread_id = query_params.get('thread_id', ['thread_12345'])[0]
            response = log_and_respond(
                f"Get routine events for thread: {thread_id}",
                {
                    "events": [],
                    "thread_id": thread_id
                }
            )
            
        # Routine summary endpoint
        elif path.startswith('/api/routines/summary/'):
            parts = path.split('/')
            thread_id = parts[4] if len(parts) > 4 else 'thread_12345'
            query_params = parse_qs(parsed_url.query)
            period = query_params.get('period', ['day'])[0]
            response = log_and_respond(
                f"Get routine summary for thread: {thread_id}, period: {period}",
                {
                    "summary": {
                        "sleep": [],
                        "feed": [],
                        "total_sleep_minutes": 0,
                        "total_feed_count": 0,
                        "period": period
                    },
                    "thread_id": thread_id
                }
            )
            
        # Default response for unknown endpoints
        else:
            response = {
                "error": "Endpoint not found",
                "path": path
            }
            
        self.wfile.write(json.dumps(response).encode())
        
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request_body = json.loads(post_data)
        path = self.path
        
        # Log request info
        logger.info(f"POST request to {path} with data: {request_body}")
        
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()
        
        # Chat endpoint
        if path == '/api/chat':
            message = request_body.get("message", "")
            thread_id = request_body.get("thread_id", "thread_12345")
            
            # Return a static response based on the message content
            if "סיכום" in message or "summary" in message.lower():
                response = {
                    "response": "זהו API מינימלי לבדיקת פריסה. סיכומי השגרה אינם זמינים כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                    "thread_id": thread_id
                }
            elif "שינה" in message or "sleep" in message.lower():
                response = {
                    "response": "זהו API מינימלי לבדיקת פריסה. מעקב שינה אינו זמין כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                    "thread_id": thread_id 
                }
            elif "האכלה" in message or "feed" in message.lower():
                response = {
                    "response": "זהו API מינימלי לבדיקת פריסה. מעקב האכלה אינו זמין כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                    "thread_id": thread_id
                }
            else:
                response = {
                    "response": "זהו API מינימלי לבדיקת פריסה. המערכת האינטליגנטית המלאה אינה זמינה כרגע בזמן שאנו מייעלים את הפריסה. נסה שוב מאוחר יותר.",
                    "thread_id": thread_id
                }
            
        # Chat reset endpoint
        elif path == '/api/chat/reset':
            thread_id = request_body.get("thread_id", "thread_12345")
            response = log_and_respond(
                f"Reset chat for thread: {thread_id}",
                {
                    "status": "ok",
                    "message": "Chat reset successful (minimal API)",
                    "thread_id": thread_id
                }
            )
            
        # Routine events endpoint
        elif path == '/api/routines/events':
            thread_id = request_body.get("thread_id", "thread_12345")
            event_type = request_body.get("event_type", "unknown")
            response = log_and_respond(
                f"Add routine event for thread: {thread_id}, type: {event_type}",
                {
                    "status": "ok", 
                    "message": "Event added successfully (minimal API)",
                    "event_id": f"mock_{int(time.time())}",
                    "thread_id": thread_id
                }
            )
            
        # Default response for unknown endpoints
        else:
            response = {
                "error": "Endpoint not found",
                "path": path
            }
            
        self.wfile.write(json.dumps(response).encode())
        
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers() 