# Project Structure

This document describes the organized project structure for the Guerrilla T application.

## Directory Structure

```
Timesheets/
├── app/                           # Main application package
│   ├── __init__.py               # Package initialization
│   ├── factory.py                # Application factory
│   ├── blueprints/               # Flask blueprints for route organization
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication routes (login, register, logout)
│   │   ├── main.py               # Main timesheet functionality routes
│   │   ├── admin.py              # Admin panel routes
│   │   └── api.py                # Power BI API endpoints
│   ├── models/                   # Data models and database utilities
│   │   ├── __init__.py
│   │   ├── user.py               # User model and authentication utilities
│   │   └── database.py           # Database connection and initialization
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── timesheet_service.py  # Timesheet data operations
│   │   ├── project_service.py    # Project management operations
│   │   └── export_service.py     # Excel export functionality
│   └── utils/                    # Helper utilities
│       ├── __init__.py
│       └── filters.py            # Template filters
├── templates/                    # Jinja2 templates
│   ├── index.html               # Main dashboard
│   ├── date_view.html           # Detailed date view
│   ├── login.html               # Login page
│   ├── register.html            # Registration page
│   ├── admin.html               # Admin panel
│   └── api_docs.html            # API documentation
├── run.py                       # Main entry point
├── app.py                       # Legacy monolithic file (can be removed)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables example
├── .gitignore                   # Git ignore rules
└── README.md                    # Project documentation
```

## Architecture Overview

### Application Factory Pattern
- **`app/factory.py`**: Creates and configures the Flask application
- **`app/__init__.py`**: Package initialization with version info
- **`run.py`**: Main entry point that creates and runs the application

### Blueprint Organization
Routes are organized into logical blueprints:

#### Authentication Blueprint (`app/blueprints/auth.py`)
- `/login` - User login
- `/register` - User registration  
- `/logout` - User logout

#### Main Blueprint (`app/blueprints/main.py`)
- `/` - Main dashboard
- `/date/<date>` - Date-specific dashboard
- `/view_date/<date>` - Detailed date view
- `/start_tracking` - Start time tracking
- `/stop_tracking` - Stop time tracking
- `/get_current_status` - Get tracking status
- `/add_project` - Add project to daily selection
- `/remove_project` - Remove project from daily selection
- `/edit_entry` - Edit time entry
- `/delete_entry` - Delete time entry
- `/export_excel` - Export to Excel

#### Admin Blueprint (`app/blueprints/admin.py`)
- `/admin/` - Admin panel
- `/admin/api/docs` - API documentation

#### API Blueprint (`app/blueprints/api.py`)
- `/api/powerbi/timesheet_data` - Timesheet data for Power BI
- `/api/powerbi/users` - User data for Power BI
- `/api/powerbi/projects` - Project data for Power BI
- `/api/powerbi/summary` - Summary statistics for Power BI

### Service Layer
Business logic is separated into service classes:

#### TimesheetService (`app/services/timesheet_service.py`)
- Time entry logging and retrieval
- Daily aggregations
- Entry editing and deletion
- Export data queries

#### ProjectService (`app/services/project_service.py`)
- Project management
- Daily project selections
- Available projects filtering

#### ExportService (`app/services/export_service.py`)
- Excel file generation
- Data formatting for exports

### Data Layer
Database operations and models:

#### Database Module (`app/models/database.py`)
- Database connection management
- Schema initialization
- Admin user creation

#### User Module (`app/models/user.py`)
- User model for Flask-Login
- Password hashing utilities
- Login manager initialization

### Utilities
Helper functions and filters:

#### Filters (`app/utils/filters.py`)
- Template filters (date manipulation, etc.)

## Benefits of This Structure

### Maintainability
- **Separation of Concerns**: Each module has a clear responsibility
- **Single Responsibility Principle**: Classes and functions do one thing well
- **Loose Coupling**: Components are independent and easily testable

### Scalability
- **Modular Design**: Easy to add new features without affecting existing code
- **Blueprint Architecture**: Routes can be easily added or modified
- **Service Pattern**: Business logic is reusable and testable

### Development Experience
- **Clear Organization**: Developers can quickly find relevant code
- **Import Structure**: Clean, logical imports between modules
- **Testing**: Each component can be unit tested independently

### Security
- **Authentication Centralized**: All auth logic in one place
- **Admin Controls**: Clear separation of admin vs. user functionality
- **API Security**: Consistent security checks across API endpoints

## Migration from Monolithic Structure

The original `app.py` file has been refactored into this modular structure:
- Routes moved to appropriate blueprints
- Business logic extracted to services
- Database operations centralized in models
- Authentication logic separated

This maintains all existing functionality while providing a much more maintainable codebase.
