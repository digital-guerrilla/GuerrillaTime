"""
Models package for Timesheet Tracker

Contains database models and user management functionality.
"""

from .user import User
from .database import get_db_connection

__all__ = ['User', 'get_db_connection']
