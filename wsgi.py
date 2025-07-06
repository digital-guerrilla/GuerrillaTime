"""
WSGI entry point for production deployment with Gunicorn
"""

import os
from app import create_app

# Create the application instance
application = create_app()

# For compatibility with some WSGI servers
app = application

if __name__ == "__main__":
    application.run()
