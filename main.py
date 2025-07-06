"""
Main entry point for Guerrilla T application
WSGI entry point for Gunicorn deployment
"""

import os
from app import create_app

# Create the application instance for WSGI servers
app = create_app()

if __name__ == '__main__':
    # For local development only
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.getenv('PORT', 8000)))
