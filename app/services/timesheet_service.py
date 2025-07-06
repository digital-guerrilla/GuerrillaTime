"""
Timesheet service for managing time tracking data
"""

from datetime import datetime
from ..models.database import get_db_connection


class TimesheetService:
    """Service class for timesheet operations"""
    
    @staticmethod
    def log_time_entry(project_id, project_name, start_time, end_time, date_str, user_id):
        """Log or update time entry to database"""
        conn = get_db_connection()
        
        duration = (end_time - start_time).total_seconds() / 60  # Duration in minutes
        
        try:
            # Try to update existing entry
            result = conn.execute('''
                UPDATE timesheet 
                SET total_minutes = total_minutes + ?, 
                    last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = ? AND date = ? AND project_id = ?
            ''', (duration, user_id, date_str, project_id))
            
            # If no rows were updated, insert new entry
            if result.rowcount == 0:
                conn.execute('''
                    INSERT INTO timesheet (user_id, date, project_id, project_name, total_minutes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, date_str, project_id, project_name, duration))
            
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def get_daily_aggregate(date_str, user_id):
        """Get aggregated time for each project on a specific date"""
        conn = get_db_connection()
        
        try:
            rows = conn.execute('''
                SELECT project_id, project_name, total_minutes
                FROM timesheet
                WHERE user_id = ? AND date = ?
            ''', (user_id, date_str)).fetchall()
            
            aggregates = {}
            for row in rows:
                aggregates[row['project_id']] = {
                    'project_name': row['project_name'],
                    'total_minutes': row['total_minutes']
                }
            
            return aggregates
        finally:
            conn.close()
    
    @staticmethod
    def get_time_entries(date_str, user_id):
        """Get all time entries for a specific date"""
        conn = get_db_connection()
        
        try:
            rows = conn.execute('''
                SELECT id, project_id, project_name, total_minutes, last_updated
                FROM timesheet
                WHERE user_id = ? AND date = ?
                ORDER BY project_id
            ''', (user_id, date_str)).fetchall()
            
            entries = []
            for i, row in enumerate(rows):
                entries.append({
                    'id': i,  # Using index for consistency
                    'db_id': row['id'],  # Keep database ID for updates
                    'project_id': row['project_id'],
                    'project_name': row['project_name'],
                    'total_minutes': row['total_minutes'],
                    'last_updated': row['last_updated']
                })
            
            return entries
        finally:
            conn.close()
    
    @staticmethod
    def update_entry(entry_id, date_str, new_duration, user_id):
        """Update a time entry"""
        conn = get_db_connection()
        
        try:
            # Get all entries for the date to find the correct one by index
            rows = conn.execute('''
                SELECT id, project_id
                FROM timesheet
                WHERE user_id = ? AND date = ?
                ORDER BY project_id
            ''', (user_id, date_str)).fetchall()
            
            if entry_id < len(rows):
                db_id = rows[entry_id]['id']
                
                # Update the entry
                conn.execute('''
                    UPDATE timesheet
                    SET total_minutes = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_duration, db_id))
                
                conn.commit()
                return True
            return False
        finally:
            conn.close()
    
    @staticmethod
    def delete_entry(entry_id, date_str, user_id):
        """Delete a time entry"""
        conn = get_db_connection()
        
        try:
            # Get all entries for the date to find the correct one by index
            rows = conn.execute('''
                SELECT id, project_id
                FROM timesheet
                WHERE user_id = ? AND date = ?
                ORDER BY project_id
            ''', (user_id, date_str)).fetchall()
            
            if entry_id < len(rows):
                db_id = rows[entry_id]['id']
                
                # Delete the entry
                conn.execute('''
                    DELETE FROM timesheet
                    WHERE id = ?
                ''', (db_id,))
                
                conn.commit()
                return True
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_export_data(start_date, end_date, user_id):
        """Get time tracking data for export between date range"""
        conn = get_db_connection()
        
        try:
            rows = conn.execute('''
                SELECT date, project_id, project_name, total_minutes
                FROM timesheet
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY project_id, date
            ''', (user_id, start_date, end_date)).fetchall()
            
            return rows
        finally:
            conn.close()
