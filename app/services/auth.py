"""
Authentication utilities — JWT token generation and verification.
"""

import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app

SECRET_KEY = os.getenv('SECRET_KEY', 'smart-classroom-secret-key-2026')
TOKEN_EXPIRY_HOURS = 24


def generate_token(student_id: int, roll_no: str) -> str:
    """Generate a JWT token for an authenticated student."""
    payload = {
        'student_id': student_id,
        'roll_no': roll_no,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def auth_required(f):
    """Decorator that protects API endpoints with JWT authentication.
    Injects `current_student_id` into kwargs.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Token can be in Authorization header or query param
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        elif request.args.get('token'):
            token = request.args.get('token')

        if not token:
            return jsonify({'success': False, 'error': 'Authentication required. Please login.'}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token. Please login again.'}), 401

        kwargs['current_student_id'] = payload['student_id']
        return f(*args, **kwargs)

    return decorated
