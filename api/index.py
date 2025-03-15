from flask import Flask, Response, request, jsonify
import time
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": "3.12",
        }
    })

@app.route('/api/redis-test', methods=['GET'])
def redis_test():
    """Test Redis connectivity"""
    return jsonify({
        "status": "ok",
        "message": "Redis connection simulated successful in minimal API mode"
    })

@app.route('/api/chat/context', methods=['GET'])
def get_context():
    """Get context endpoint"""
    thread_id = request.args.get('thread_id', 'thread_12345')
    print(f"Get context for thread: {thread_id}")
    return jsonify({
        "context": [],
        "thread_id": thread_id
    })

@app.route('/api/routines/events', methods=['GET'])
def get_routine_events():
    """Get routine events endpoint"""
    thread_id = request.args.get('thread_id', 'thread_12345')
    print(f"Get routine events for thread: {thread_id}")
    return jsonify({
        "events": [],
        "thread_id": thread_id
    })

@app.route('/api/routines/summary/<thread_id>', methods=['GET'])
def get_routine_summary(thread_id):
    """Get routine summary endpoint"""
    period = request.args.get('period', 'day')
    print(f"Get routine summary for thread: {thread_id}, period: {period}")
    return jsonify({
        "summary": {
            "sleep": [],
            "feed": [],
            "total_sleep_minutes": 0,
            "total_feed_count": 0,
            "period": period
        },
        "thread_id": thread_id
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    request_body = request.json
    message = request_body.get("message", "")
    thread_id = request_body.get("thread_id", "thread_12345")
    
    print(f"Chat request: {message} for thread: {thread_id}")
    
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
    
    return jsonify(response)

@app.route('/api/chat/reset', methods=['POST'])
def reset_chat():
    """Reset chat endpoint"""
    request_body = request.json
    thread_id = request_body.get("thread_id", "thread_12345")
    print(f"Reset chat for thread: {thread_id}")
    return jsonify({
        "status": "ok",
        "message": "Chat reset successful (minimal API)",
        "thread_id": thread_id
    })

@app.route('/api/routines/events', methods=['POST'])
def add_routine_event():
    """Add routine event endpoint"""
    request_body = request.json
    thread_id = request_body.get("thread_id", "thread_12345")
    event_type = request_body.get("event_type", "unknown")
    print(f"Add routine event for thread: {thread_id}, type: {event_type}")
    return jsonify({
        "status": "ok", 
        "message": "Event added successfully (minimal API)",
        "event_id": f"mock_{int(time.time())}",
        "thread_id": thread_id
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({
        "error": "Endpoint not found",
        "path": path
    }) 