# CORS Fix - Add this decorator to all routes
from functools import wraps
from flask import make_response

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Type, Authorization')
    return response

def cors_headers(f):
    """Decorator to add CORS headers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = make_response()
            return add_cors_headers(response)
        response = make_response(f(*args, **kwargs))
        return add_cors_headers(response)
    return decorated_function


