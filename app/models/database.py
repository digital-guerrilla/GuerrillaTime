"""
Database utilities and initialization for Timesheet Tracker
"""

import sqlite3
import os
from .user import hash_password


def get_db_connection():
    """Get database connection"""
    database_path = os.getenv('DATABASE', 'timesheet.db')
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with required tables"""
    conn = get_db_connection()
    
    # Create users table with all current fields including 2FA support
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            temp_password TEXT NULL,
            is_disabled INTEGER DEFAULT 0,
            microsoft_id TEXT NULL,
            display_name TEXT NULL,
            auth_method TEXT DEFAULT 'password',
            password_disabled INTEGER DEFAULT 0,
            totp_secret TEXT NULL,
            totp_enabled INTEGER DEFAULT 0,
            backup_codes TEXT NULL
        )
    ''')
    
    # Check if we need to add new columns to existing users table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # Define all columns that should exist
    required_columns = [
        ('temp_password', 'TEXT NULL'),
        ('is_disabled', 'INTEGER DEFAULT 0'),
        ('microsoft_id', 'TEXT NULL'),
        ('display_name', 'TEXT NULL'),
        ('auth_method', 'TEXT DEFAULT "password"'),
        ('password_disabled', 'INTEGER DEFAULT 0'),
        ('totp_secret', 'TEXT NULL'),
        ('totp_enabled', 'INTEGER DEFAULT 0'),
        ('backup_codes', 'TEXT NULL')
    ]
    
    # Add missing columns
    for column_name, column_def in required_columns:
        if column_name not in existing_columns:
            try:
                alter_sql = f'ALTER TABLE users ADD COLUMN {column_name} {column_def}'
                print(f"Adding column: {alter_sql}")
                conn.execute(alter_sql)
                conn.commit()
                print(f"Successfully added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"Error adding column {column_name}: {e}")
                # Column might already exist, continue
                pass
    
    # Create timesheet table with user_id
    conn.execute('''
        CREATE TABLE IF NOT EXISTS timesheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            total_minutes REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, date, project_id)
        )
    ''')
    
    # Create daily_projects table with user_id
    conn.execute('''
        CREATE TABLE IF NOT EXISTS daily_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            project_id TEXT NOT NULL,
            project_name TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, date, project_id)
        )
    ''')
    
    # Create projects table for project management
    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            status TEXT DEFAULT 'live' CHECK(status IN ('live', 'finished')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create system_settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NULL,
            setting_type TEXT DEFAULT 'text',
            is_encrypted INTEGER DEFAULT 0,
            description TEXT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add status column to existing projects table if it doesn't exist
    try:
        conn.execute('ALTER TABLE projects ADD COLUMN status TEXT DEFAULT "live" CHECK(status IN ("live", "finished"))')
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists, which is fine
        pass
    
    conn.commit()
    
    # Seed default projects if table is empty
    seed_default_projects(conn)
    
    # Seed default system settings if table is empty
    seed_default_system_settings(conn)
    
    conn.close()


def seed_default_projects(conn):
    """Seed default projects if the projects table is empty"""
    count = conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
    
    if count == 0:
        default_projects = [
            ('PROJ001', 'Website Redesign'),
            ('PROJ002', 'Mobile App Development'),
            ('PROJ003', 'Database Migration'),
            ('PROJ004', 'API Integration'),
            ('PROJ005', 'Security Audit'),
            ('PROJ006', 'Performance Testing'),
            ('PROJ007', 'Documentation Update'),
            ('PROJ008', 'Bug Fixes'),
            ('PROJ009', 'User Training'),
            ('PROJ010', 'Code Review')
        ]
        
        conn.executemany('''
            INSERT INTO projects (project_id, project_name, status)
            VALUES (?, ?, 'live')
        ''', default_projects)
        
        conn.commit()
        print("Default projects seeded")


def seed_default_system_settings(conn):
    """Seed default system settings if the system_settings table is empty"""
    count = conn.execute('SELECT COUNT(*) FROM system_settings').fetchone()[0]
    
    if count == 0:
        # Default system settings
        default_settings = [
            # Customization settings
            ('custom_company_name', 'Guerrilla T', 'text', 0, 'Company name displayed in the application', 'customization'),
            ('custom_logo_url', '', 'text', 0, 'URL or path to company logo', 'customization'),
            ('custom_primary_color', '#007bff', 'color', 0, 'Primary brand color', 'customization'),
            ('custom_secondary_color', '#6c757d', 'color', 0, 'Secondary brand color', 'customization'),
            ('custom_success_color', '#28a745', 'color', 0, 'Success color', 'customization'),
            ('custom_danger_color', '#dc3545', 'color', 0, 'Danger/error color', 'customization'),
            ('custom_warning_color', '#ffc107', 'color', 0, 'Warning color', 'customization'),
            ('custom_info_color', '#17a2b8', 'color', 0, 'Info color', 'customization'),
            
            # OAuth settings
            ('oauth_allow_sso', 'false', 'checkbox', 0, 'Enable Microsoft OAuth single sign-on', 'oauth'),
            ('oauth_disable_passwords', 'false', 'checkbox', 0, 'Disable password authentication (SSO only)', 'oauth'),
            ('oauth_tenant_id', '', 'text', 0, 'Microsoft Azure tenant ID or domain', 'oauth'),
            ('oauth_client_id', '', 'text', 0, 'Microsoft Azure application client ID', 'oauth'),
            ('oauth_client_secret', '', 'password', 1, 'Microsoft Azure application client secret', 'oauth'),
            ('oauth_redirect_uri', '', 'text', 0, 'OAuth redirect URI (leave blank for auto-detection)', 'oauth'),
        ]
        
        conn.executemany('''
            INSERT INTO system_settings (setting_key, setting_value, setting_type, is_encrypted, description, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_settings)
        
        conn.commit()
        print("Default system settings seeded")


def create_admin_user():
    """Create admin user if it doesn't exist"""
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    if not admin_email or not admin_password:
        print("Warning: ADMIN_EMAIL and ADMIN_PASSWORD not set in .env file")
        return
    
    conn = get_db_connection()
    try:
        # Check if admin user exists
        existing_admin = conn.execute('''
            SELECT id FROM users WHERE email = ?
        ''', (admin_email,)).fetchone()
        
        if not existing_admin:
            hashed_password = hash_password(admin_password)
            conn.execute('''
                INSERT INTO users (email, password_hash, is_admin)
                VALUES (?, ?, 1)
            ''', (admin_email, hashed_password))
            conn.commit()
            print(f"Admin user created: {admin_email}")
    finally:
        conn.close()


def ensure_oauth_settings_exist():
    """Ensure OAuth settings exist in the database (for existing databases)"""
    conn = get_db_connection()
    try:
        # Check if OAuth settings exist
        oauth_count = conn.execute('''
            SELECT COUNT(*) FROM system_settings WHERE category = 'oauth'
        ''').fetchone()[0]
        
        if oauth_count == 0:
            print("OAuth settings not found, adding them...")
            # OAuth settings to add
            oauth_settings = [
                ('oauth_allow_sso', 'false', 'checkbox', 0, 'Enable Microsoft OAuth single sign-on', 'oauth'),
                ('oauth_disable_passwords', 'false', 'checkbox', 0, 'Disable password authentication (SSO only)', 'oauth'),
                ('oauth_tenant_id', '', 'text', 0, 'Microsoft Azure tenant ID or domain', 'oauth'),
                ('oauth_client_id', '', 'text', 0, 'Microsoft Azure application client ID', 'oauth'),
                ('oauth_client_secret', '', 'password', 1, 'Microsoft Azure application client secret', 'oauth'),
                ('oauth_redirect_uri', '', 'text', 0, 'OAuth redirect URI (leave blank for auto-detection)', 'oauth'),
            ]
            
            conn.executemany('''
                INSERT INTO system_settings (setting_key, setting_value, setting_type, is_encrypted, description, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', oauth_settings)
            
            conn.commit()
            print("OAuth settings added to existing database")
    finally:
        conn.close()
