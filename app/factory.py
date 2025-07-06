"""
Application Factory for Timesheet Tracker

Creates and configures the Flask application with all necessary components.
"""

from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import logging

# Load environment variables
load_dotenv()


def create_app(config_name='default'):
    """Create Flask application factory"""
    # Get the path to the project root (parent of 'app' directory)
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DATABASE'] = os.getenv('DATABASE', 'timesheet.db')
    
    # Configure logging for production
    if not app.debug and not app.testing:
        # Production logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        app.logger.setLevel(logging.INFO)
        app.logger.info('Guerrilla T Timesheet application startup')
    
    # Initialize extensions
    from .models.user import init_login_manager
    init_login_manager(app)
    
    # Initialize database
    from .models.database import init_database, create_admin_user
    init_database()
    create_admin_user()
    
    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.main import main_bp
    from .blueprints.api import api_bp
    from .blueprints.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Register template filters
    from .utils.filters import register_filters
    register_filters(app)
    
    return app
