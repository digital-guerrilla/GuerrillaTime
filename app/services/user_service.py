"""
User service for user management operations
"""

from ..models.database import get_db_connection
from ..models.user import hash_password
import secrets
import string
import csv
import io


class UserService:
    """Service class for user management operations"""
    
    @staticmethod
    def generate_temporary_password(length=12):
        """Generate a random temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def get_all_users():
        """Get all users with their information"""
        conn = get_db_connection()
        try:
            users = conn.execute('''
                SELECT id, email, is_admin, created_at, 
                       CASE WHEN temp_password IS NOT NULL THEN 1 ELSE 0 END as has_temp_password,
                       temp_password
                FROM users 
                ORDER BY created_at DESC
            ''').fetchall()
            return [dict(user) for user in users]
        finally:
            conn.close()
    
    @staticmethod
    def get_all_users_detailed():
        """Get all users with detailed information including OAuth status"""
        conn = get_db_connection()
        try:
            users = conn.execute('''
                SELECT id, email, is_admin, created_at, is_disabled,
                       CASE WHEN temp_password IS NOT NULL THEN 1 ELSE 0 END as has_temp_password,
                       temp_password, microsoft_id, display_name,
                       COALESCE(auth_method, 'password') as auth_method,
                       COALESCE(password_disabled, 0) as password_disabled
                FROM users 
                ORDER BY created_at DESC
            ''').fetchall()
            return [dict(user) for user in users]
        finally:
            conn.close()
    
    @staticmethod
    def get_user_statistics():
        """Get user statistics including total time tracked"""
        conn = get_db_connection()
        try:
            stats = conn.execute('''
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN is_admin = 1 THEN 1 ELSE 0 END) as admin_users,
                    SUM(CASE WHEN temp_password IS NOT NULL THEN 1 ELSE 0 END) as users_with_temp_passwords,
                    SUM(CASE WHEN is_disabled = 0 THEN 1 ELSE 0 END) as active_users
                FROM users
            ''').fetchone()
            
            # Get total time tracked by all users
            total_time = conn.execute('''
                SELECT COALESCE(SUM(total_minutes), 0) as total_time_minutes
                FROM timesheet
            ''').fetchone()
            
            result = dict(stats) if stats else {
                'total_users': 0, 
                'admin_users': 0, 
                'users_with_temp_passwords': 0,
                'active_users': 0
            }
            
            result['total_time_minutes'] = total_time['total_time_minutes'] if total_time else 0
            
            return result
        finally:
            conn.close()
    
    @staticmethod
    def create_user(email, is_admin=False):
        """Create a new user with a temporary password"""
        conn = get_db_connection()
        try:
            # Check if user already exists
            existing_user = conn.execute('''
                SELECT id FROM users WHERE email = ?
            ''', (email,)).fetchone()
            
            if existing_user:
                return False, "User with this email already exists"
            
            # Generate temporary password
            temp_password = UserService.generate_temporary_password()
            hashed_password = hash_password(temp_password)
            
            # Create user
            cursor = conn.execute('''
                INSERT INTO users (email, password_hash, is_admin, temp_password)
                VALUES (?, ?, ?, ?)
            ''', (email, hashed_password, 1 if is_admin else 0, temp_password))
            
            conn.commit()
            return True, f"User created successfully. Temporary password: {temp_password}"
        
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def update_user(user_id, email=None, is_admin=None):
        """Update user information"""
        conn = get_db_connection()
        try:
            # Check if user exists
            user = conn.execute('''
                SELECT id FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return False, "User not found"
            
            # Check if email is already taken by another user
            if email:
                existing_user = conn.execute('''
                    SELECT id FROM users WHERE email = ? AND id != ?
                ''', (email, user_id)).fetchone()
                
                if existing_user:
                    return False, "Email is already in use by another user"
            
            # Build update query dynamically
            updates = []
            params = []
            
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            
            if is_admin is not None:
                updates.append("is_admin = ?")
                params.append(1 if is_admin else 0)
            
            if not updates:
                return False, "No updates provided"
            
            params.append(user_id)
            
            conn.execute(f'''
                UPDATE users SET {", ".join(updates)}
                WHERE id = ?
            ''', params)
            
            conn.commit()
            return True, "User updated successfully"
        
        except Exception as e:
            return False, f"Error updating user: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user"""
        conn = get_db_connection()
        try:
            # Check if user exists
            user = conn.execute('''
                SELECT id, email FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return False, "User not found"
            
            # Check if this is the last admin user
            admin_count = conn.execute('''
                SELECT COUNT(*) FROM users WHERE is_admin = 1
            ''').fetchone()[0]
            
            user_is_admin = conn.execute('''
                SELECT is_admin FROM users WHERE id = ?
            ''', (user_id,)).fetchone()[0]
            
            if user_is_admin and admin_count <= 1:
                return False, "Cannot delete the last admin user"
            
            # Delete user (timesheet entries will be preserved but user_id will be invalid)
            # In production, you might want to handle this differently
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            
            return True, f"User {user['email']} deleted successfully"
        
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def reset_user_password(user_id):
        """Reset user password to a new temporary password"""
        conn = get_db_connection()
        try:
            # Check if user exists
            user = conn.execute('''
                SELECT id, email FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return False, "User not found"
            
            # Generate new temporary password
            temp_password = UserService.generate_temporary_password()
            hashed_password = hash_password(temp_password)
            
            # Update user
            conn.execute('''
                UPDATE users 
                SET password_hash = ?, temp_password = ?
                WHERE id = ?
            ''', (hashed_password, temp_password, user_id))
            
            conn.commit()
            return True, f"Password reset successfully. New temporary password: {temp_password}"
        
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def clear_temporary_password(user_id):
        """Clear temporary password flag after user sets permanent password"""
        conn = get_db_connection()
        try:
            conn.execute('''
                UPDATE users 
                SET temp_password = NULL
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error clearing temporary password: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def has_temporary_password(user_id):
        """Check if user has a temporary password"""
        conn = get_db_connection()
        try:
            result = conn.execute('''
                SELECT temp_password FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            return result and result['temp_password'] is not None
        finally:
            conn.close()
    
    @staticmethod
    def import_users_from_csv(csv_content):
        """Import users from CSV content"""
        try:
            stream = io.StringIO(csv_content)
            csv_reader = csv.reader(stream)
            
            # Skip header row if present
            first_row = next(csv_reader, None)
            if not first_row:
                return False, "CSV file is empty"
            
            # Check if first row looks like headers
            if first_row[0].lower() in ['email', 'user_email', 'e-mail']:
                # Skip header row
                pass
            else:
                # First row is data, reset the stream
                stream.seek(0)
                csv_reader = csv.reader(stream)
            
            added_count = 0
            error_count = 0
            errors = []
            created_users = []
            
            for row_num, row in enumerate(csv_reader, start=1):
                if len(row) < 1:
                    error_count += 1
                    errors.append(f"Row {row_num}: Missing email")
                    continue
                
                email = row[0].strip().lower()
                is_admin = False
                
                # Check if second column indicates admin status
                if len(row) > 1:
                    admin_indicator = row[1].strip().lower()
                    if admin_indicator in ['true', '1', 'yes', 'admin']:
                        is_admin = True
                
                if not email:
                    error_count += 1
                    errors.append(f"Row {row_num}: Missing email")
                    continue
                
                success, message = UserService.create_user(email, is_admin)
                
                if success:
                    added_count += 1
                    # Extract temporary password from message
                    temp_password = message.split(": ")[-1]
                    created_users.append({
                        'email': email,
                        'temp_password': temp_password,
                        'is_admin': is_admin
                    })
                else:
                    error_count += 1
                    errors.append(f"Row {row_num}: {message}")
            
            return True, {
                'added_count': added_count,
                'error_count': error_count,
                'errors': errors[:10],  # Limit to first 10 errors
                'created_users': created_users
            }
        
        except Exception as e:
            return False, f"Error processing CSV: {str(e)}"
    
    @staticmethod
    def get_users_with_stats(status_filter='all'):
        """Get users with their time tracking statistics, filtered by status"""
        conn = get_db_connection()
        try:
            # Base query to get users with their time tracking statistics and OAuth info
            base_query = '''
                SELECT u.id, u.email, u.is_admin, u.created_at, u.is_disabled,
                       CASE WHEN u.temp_password IS NOT NULL THEN 1 ELSE 0 END as has_temp_password,
                       u.temp_password,
                       COALESCE(u.auth_method, 'password') as auth_method,
                       COALESCE(u.password_disabled, 0) as password_disabled,
                       u.microsoft_id,
                       u.display_name,
                       COALESCE(SUM(t.total_minutes), 0) as total_minutes
                FROM users u
                LEFT JOIN timesheet t ON u.id = t.user_id
            '''
            
            # Add WHERE clause based on filter
            if status_filter == 'active':
                where_clause = ' WHERE u.is_disabled = 0'
            elif status_filter == 'disabled':
                where_clause = ' WHERE u.is_disabled = 1'
            elif status_filter == 'oauth':
                where_clause = ' WHERE u.auth_method = "oauth" AND u.microsoft_id IS NOT NULL'
            else:  # 'all'
                where_clause = ''
            
            query = base_query + where_clause + '''
                GROUP BY u.id, u.email, u.is_admin, u.created_at, u.is_disabled, 
                         u.temp_password, u.auth_method, u.password_disabled, 
                         u.microsoft_id, u.display_name
                ORDER BY u.created_at DESC
            '''
            
            users = conn.execute(query).fetchall()
            return [dict(user) for user in users]
        finally:
            conn.close()
    
    @staticmethod
    def update_user_status(user_id, status):
        """Update user status (enable/disable)"""
        conn = get_db_connection()
        try:
            # Check if user exists
            user = conn.execute('''
                SELECT id, email FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return False, "User not found"
            
            # Update user status
            is_disabled = 1 if status == 'disabled' else 0
            conn.execute('''
                UPDATE users SET is_disabled = ? WHERE id = ?
            ''', (is_disabled, user_id))
            
            conn.commit()
            
            action = "disabled" if is_disabled else "enabled"
            return True, f"User {user['email']} has been {action} successfully"
        
        except Exception as e:
            return False, f"Error updating user status: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def enable_password_auth(user_id):
        """Re-enable password authentication for an OAuth user"""
        conn = get_db_connection()
        try:
            # Check if user exists and is OAuth user
            user = conn.execute('''
                SELECT id, email, auth_method, password_disabled 
                FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return False, "User not found"
            
            if user['auth_method'] != 'oauth':
                return False, "User is not an OAuth user"
            
            # Re-enable password authentication
            conn.execute('''
                UPDATE users 
                SET password_disabled = 0, auth_method = 'password'
                WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            return True, f"Password authentication re-enabled for {user['email']}"
            
        except Exception as e:
            return False, f"Error enabling password auth: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_oauth_users():
        """Get all OAuth users"""
        conn = get_db_connection()
        try:
            users = conn.execute('''
                SELECT id, email, display_name, microsoft_id, created_at, is_disabled
                FROM users 
                WHERE auth_method = 'oauth' AND microsoft_id IS NOT NULL
                ORDER BY created_at DESC
            ''').fetchall()
            return [dict(user) for user in users]
        finally:
            conn.close()
