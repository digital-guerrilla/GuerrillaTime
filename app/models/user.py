"""
User model and authentication utilities for Timesheet Tracker
"""

from flask_login import LoginManager, UserMixin
import bcrypt
import os


class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, id, email, is_admin=False, totp_enabled=False):
        self.id = id
        self.email = email
        self.is_admin = is_admin
        self.totp_enabled = totp_enabled


def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password, hashed):
    """Check a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def init_login_manager(app):
    """Initialize Flask-Login"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database for Flask-Login"""
        from .database import get_db_connection
        
        conn = get_db_connection()
        try:
            user = conn.execute('''
                SELECT id, email, is_admin, totp_enabled FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if user:
                return User(
                    user['id'], 
                    user['email'], 
                    bool(user['is_admin']),
                    bool(user['totp_enabled'] if 'totp_enabled' in user.keys() else False)
                )
            return None
        finally:
            conn.close()
    
    return login_manager
