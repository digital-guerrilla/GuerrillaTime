# Guerrilla T ⚡

*Smart Time Tracking by Digital Guerrilla*

A modern Flask-based web application for tracking time spent on various projects with user authentication and powerful Power BI integration.

## Features

- **User Authentication**: Secure login/register system with encrypted passwords
- **User Management**: Admin users can create, edit, and delete user accounts
- **Temporary Passwords**: New users receive temporary passwords that must be changed on first login
- **CSV User Import**: Bulk user creation via CSV file upload
- **Password Reset**: Admins can reset user passwords to temporary ones
- **User Isolation**: Each user's data is completely separate and private
- **Admin Panel**: Master admin account with access to control panel (expandable)
- **Daily Project Selection**: Choose which projects to work on each day from a dropdown
- **Persistent Project Lists**: Each day maintains its own project selection per user
- **Time Tracking**: Start/stop time tracking with a single click
- **Real-time Updates**: See elapsed time update in real-time
- **Cumulative Time**: Single entry per project per day that accumulates time from multiple sessions
- **Historical View**: Navigate to previous days and view/edit time entries
- **Project Management**: Add/remove projects from daily list without losing time data
- **Data Persistence**: All data stored in SQLite database (user accounts, project selections and time data)
- **Single Project Tracking**: Only one project can be tracked at a time

## Project Structure

```
Timesheets/
├── app.py              # Main Flask application with authentication
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (admin credentials, secrets)
├── templates/
│   ├── index.html      # Main dashboard with project selection
│   ├── date_view.html  # Detailed day view
│   ├── login.html      # User login page
│   ├── register.html   # User registration page
│   └── admin.html      # Admin control panel
├── timesheet.db        # SQLite database
└── README.md          # This file
```

## Installation

use the docker-compose.yaml to spin up a docker container

## Usage

### User Registration & Login
- **Register**: Create a new user account with email and password
- **Login**: Access your personal timesheet dashboard
- **Data Isolation**: Each user only sees their own projects and time data

### Admin Features
- **Admin Login**: Use the credentials from your `.env` file
- **Admin Panel**: Access via the "Admin Panel" button (visible only to admins)
- **User Management**: (Coming soon) View and manage all users

### Main Dashboard
- **Add Projects**: Use the dropdown to select and add projects to today's working list
- **Remove Projects**: Click the "×" button on project cards to remove from today's list
- **Start Tracking**: Click "Start Tracking" on any project card
- **Stop Tracking**: Click "Stop Tracking" when done
- **View Date**: Use the date picker to view a specific date
- **Daily Summary**: See total time for each project

### Date View
- **Edit Entries**: Modify the total time for any project
- **Delete Entries**: Remove project entries completely
- **Navigation**: Move between dates using the navigation buttons

### Project Management
- **Daily Lists**: Each day has its own project selection
- **Persistent Data**: Time data is preserved even when projects are removed from daily lists
- **Flexible Selection**: Add/remove projects as needed throughout the day

## User Management

### Creating Users
Admin users can create new users in two ways:

1. **Manual Entry**: Create individual users through the admin panel
2. **CSV Upload**: Bulk create users by uploading a CSV file

### Temporary Passwords
- When a new user is created, they receive a randomly generated temporary password
- Users must change this password on their first login
- Temporary passwords are displayed to admins and stored securely until changed

### Password Management
- Users are forced to change temporary passwords on first login
- Admins can reset any user's password, generating a new temporary password
- Password reset removes the current password and creates a new temporary one

### CSV User Import Format
```csv
Email,Admin
user1@company.com,false
admin@company.com,true
user2@company.com,no
```
- First column: Email address (required)
- Second column: Admin status (optional, accepts: true/false, 1/0, yes/no, admin)
- Header row is optional and automatically detected

### Admin Privileges
Admin users can:
- Create, edit, and delete other users
- Reset user passwords
- Access user management panel
- View user statistics
- Import users via CSV

### First-Time Setup
If you need to create your first admin user, run:
```bash
python create_admin.py
```

### Future OAuth Integration
The system is designed to support OAuth/SSO integration by matching email addresses. This will allow users to authenticate via:
- Google OAuth
- Microsoft Azure AD
- Other OAuth providers

When OAuth is implemented, users will still need to be created in the system first, but authentication will be handled by the OAuth provider.

## Data Storage

The application uses SQLite database for persistent storage with user authentication:

### Users Table (`users`)
- **Columns**: id, email, password_hash, is_admin, created_at
- **Purpose**: Stores user accounts with encrypted passwords
- **Security**: Passwords hashed using bcrypt

### Time Entries Table (`timesheet`)
- **Columns**: id, user_id, date, project_id, project_name, total_minutes, last_updated
- **Purpose**: Stores cumulative time per project per day per user
- **Key Features**: One entry per user per project per day with automatic aggregation

### Daily Project Selections Table (`daily_projects`)
- **Columns**: id, user_id, date, project_id, project_name, added_at  
- **Purpose**: Tracks which projects are active for each day per user
- **Key Features**: Maintains independent daily project lists per user

The database is automatically created on first run and supports:
- ACID compliance for data integrity
- Concurrent access handling
- Automatic schema creation
- Data persistence across application restarts

## Customization

### Adding Projects
Edit the `get_projects()` function in `app.py` to modify the available projects:

```python
def get_projects():
    return {
        'PROJ001': 'Your Project Name',
        'PROJ002': 'Another Project',
        # Add more projects here
    }
```

### API Integration
The application is designed to easily integrate with external APIs:
- Replace `get_projects()` with actual API calls
- Modify data storage functions to send to external APIs

## Features in Detail

### Daily Project Selection
- Choose which projects to work on each day from a dropdown menu
- Projects can be added or removed from the daily list as needed
- Each day maintains its own independent project selection
- Time data is preserved even when projects are removed from daily lists

### Cumulative Time Tracking
- Single entry per project per day that accumulates time from multiple tracking sessions
- No more multiple entries cluttering the view
- Real-time elapsed time display while tracking
- Automatic addition to existing time when stopping and starting again

### Persistent Data Management
- Daily project selections stored separately from time data
- Time data retained indefinitely even if projects are removed from daily lists
- Easy migration between different days and project combinations

## Browser Compatibility

The application works with all modern browsers including:
- Chrome
- Firefox
- Safari
- Edge

## Troubleshooting

### Application won't start
- Ensure Python is installed and in PATH
- Install dependencies: `pip install -r requirements.txt`
- Check for port conflicts (default port 5000)

### Data not saving
- Check file permissions in the application directory
- Ensure sufficient disk space
- Verify the SQLite database file is not locked by other applications
