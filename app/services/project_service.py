"""
Project service for managing projects and daily selections
"""

from ..models.database import get_db_connection
from datetime import datetime


class ProjectService:
    """Service class for project operations"""
    
    @staticmethod
    def get_projects(status_filter='live'):
        """Get available projects from database, filtered by status"""
        conn = get_db_connection()
        
        try:
            if status_filter == 'all':
                rows = conn.execute('''
                    SELECT project_id, project_name, status
                    FROM projects
                    ORDER BY status, project_id
                ''').fetchall()
            else:
                rows = conn.execute('''
                    SELECT project_id, project_name, status
                    FROM projects
                    WHERE status = ?
                    ORDER BY project_id
                ''', (status_filter,)).fetchall()
            
            projects = {}
            for row in rows:
                projects[row['project_id']] = row['project_name']
            
            return projects
        finally:
            conn.close()
    
    @staticmethod
    def get_projects_with_stats(status_filter='all'):
        """Get projects with time statistics for admin panel"""
        conn = get_db_connection()
        
        try:
            if status_filter == 'all':
                query = '''
                    SELECT 
                        p.project_id,
                        p.project_name,
                        p.status,
                        COALESCE(SUM(t.total_minutes), 0) as total_minutes,
                        MAX(t.last_updated) as last_activity
                    FROM projects p
                    LEFT JOIN timesheet t ON p.project_id = t.project_id
                    GROUP BY p.project_id, p.project_name, p.status
                    ORDER BY p.status, p.project_id
                '''
                rows = conn.execute(query).fetchall()
            else:
                query = '''
                    SELECT 
                        p.project_id,
                        p.project_name,
                        p.status,
                        COALESCE(SUM(t.total_minutes), 0) as total_minutes,
                        MAX(t.last_updated) as last_activity
                    FROM projects p
                    LEFT JOIN timesheet t ON p.project_id = t.project_id
                    WHERE p.status = ?
                    GROUP BY p.project_id, p.project_name, p.status
                    ORDER BY p.project_id
                '''
                rows = conn.execute(query, (status_filter,)).fetchall()
            
            projects = []
            for row in rows:
                project_data = {
                    'project_id': row['project_id'],
                    'project_name': row['project_name'],
                    'status': row['status'],
                    'total_minutes': row['total_minutes'] or 0,
                    'last_activity': datetime.fromisoformat(row['last_activity']) if row['last_activity'] else None
                }
                projects.append(project_data)
            
            return projects
        finally:
            conn.close()
    
    @staticmethod
    def add_project(project_id, project_name, status='live'):
        """Add a new project to the database"""
        conn = get_db_connection()
        
        try:
            conn.execute('''
                INSERT INTO projects (project_id, project_name, status)
                VALUES (?, ?, ?)
            ''', (project_id.upper(), project_name, status))
            
            conn.commit()
            return True, "Project added successfully"
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                return False, f"Project ID '{project_id}' already exists"
            return False, f"Error adding project: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def update_project(project_id, project_name):
        """Update an existing project"""
        conn = get_db_connection()
        
        try:
            result = conn.execute('''
                UPDATE projects 
                SET project_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ?
            ''', (project_name, project_id))
            
            if result.rowcount == 0:
                conn.close()
                return False, "Project not found"
            
            # Also update project names in related tables
            conn.execute('''
                UPDATE daily_projects 
                SET project_name = ?
                WHERE project_id = ?
            ''', (project_name, project_id))
            
            conn.execute('''
                UPDATE timesheet 
                SET project_name = ?
                WHERE project_id = ?
            ''', (project_name, project_id))
            
            conn.commit()
            return True, "Project updated successfully"
        except Exception as e:
            return False, f"Error updating project: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def delete_project(project_id):
        """Delete a project and all associated data"""
        conn = get_db_connection()
        
        try:
            # First check if there's any time tracked for this project
            time_check = conn.execute('''
                SELECT SUM(total_minutes) as total_time
                FROM timesheet
                WHERE project_id = ?
            ''', (project_id,)).fetchone()
            
            total_time = time_check['total_time'] if time_check['total_time'] else 0
            
            # Delete from all related tables
            conn.execute('DELETE FROM daily_projects WHERE project_id = ?', (project_id,))
            conn.execute('DELETE FROM timesheet WHERE project_id = ?', (project_id,))
            conn.execute('DELETE FROM projects WHERE project_id = ?', (project_id,))
            
            conn.commit()
            
            if total_time > 0:
                return True, f"Project deleted successfully. {total_time:.1f} minutes of tracked time was also removed."
            else:
                return True, "Project deleted successfully."
                
        except Exception as e:
            return False, f"Error deleting project: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_project_statistics():
        """Get overall project statistics"""
        conn = get_db_connection()
        
        try:
            stats = conn.execute('''
                SELECT 
                    COUNT(DISTINCT p.project_id) as total_projects,
                    COALESCE(SUM(t.total_minutes), 0) as total_time_minutes,
                    COUNT(DISTINCT CASE WHEN t.total_minutes > 0 THEN p.project_id END) as active_projects
                FROM projects p
                LEFT JOIN timesheet t ON p.project_id = t.project_id
            ''').fetchone()
            
            return {
                'total_projects': stats['total_projects'],
                'total_time_minutes': stats['total_time_minutes'] or 0,
                'active_projects': stats['active_projects'] or 0
            }
        finally:
            conn.close()
    
    @staticmethod
    def get_selected_projects(date_str, user_id):
        """Get projects selected for a specific date"""
        conn = get_db_connection()
        
        try:
            rows = conn.execute('''
                SELECT project_id, project_name
                FROM daily_projects
                WHERE user_id = ? AND date = ?
                ORDER BY project_id
            ''', (user_id, date_str)).fetchall()
            
            selected = {}
            for row in rows:
                selected[row['project_id']] = row['project_name']
            
            return selected
        finally:
            conn.close()
    
    @staticmethod
    def add_project_to_day(project_id, date_str, user_id):
        """Add a project to the daily selection (only live projects)"""
        conn = get_db_connection()
        all_projects = ProjectService.get_projects('live')  # Only get live projects
        
        if project_id not in all_projects:
            conn.close()
            return False
        
        try:
            # Use INSERT OR IGNORE to prevent duplicates
            conn.execute('''
                INSERT OR IGNORE INTO daily_projects (user_id, date, project_id, project_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, date_str, project_id, all_projects[project_id]))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding project: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def remove_project_from_day(project_id, date_str, user_id):
        """Remove a project from daily selection (without deleting time data)"""
        conn = get_db_connection()
        
        try:
            conn.execute('''
                DELETE FROM daily_projects
                WHERE user_id = ? AND date = ? AND project_id = ?
            ''', (user_id, date_str, project_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing project: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_available_projects(date_str, user_id):
        """Get projects that can be added to the daily selection (only live projects)"""
        all_projects = ProjectService.get_projects('live')  # Only get live projects
        selected = ProjectService.get_selected_projects(date_str, user_id)
        
        available = {}
        for project_id, project_name in all_projects.items():
            if project_id not in selected:
                available[project_id] = project_name
        
        return available
    
    @staticmethod
    def update_project_status(project_id, status):
        """Update project status (live/finished)"""
        conn = get_db_connection()
        
        try:
            if status not in ['live', 'finished']:
                return False, "Invalid status. Must be 'live' or 'finished'"
            
            result = conn.execute('''
                UPDATE projects 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ?
            ''', (status, project_id))
            
            if result.rowcount == 0:
                return False, "Project not found"
            
            conn.commit()
            status_text = "live" if status == "live" else "finished"
            return True, f"Project marked as {status_text}"
        except Exception as e:
            return False, f"Error updating project status: {str(e)}"
        finally:
            conn.close()
