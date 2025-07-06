"""
API authentication utilities
"""

from flask import request, jsonify
from functools import wraps
import os


def get_api_key():
    """Get the API key from environment or use default"""
    return os.getenv('API_KEY', 'timesheet-api-key-2025')


def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Missing Authorization header'}), 401
        
        # Check if it's a Bearer token
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid Authorization header format. Use: Bearer <token>'}), 401
        
        # Extract the token
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate the token
        if token != get_api_key():
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
