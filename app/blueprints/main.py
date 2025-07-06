"""
Main application blueprint for timesheet functionality
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime
import threading
import time
from ..services.timesheet_service import TimesheetService
from ..services.project_service import ProjectService
from ..services.export_service import ExportService
from ..services.system_settings_service import SystemSettingsService

main_bp = Blueprint('main', __name__)

# Health check endpoint for Docker containers
@main_bp.route('/health')
def health_check():
    """Health check endpoint for container orchestration"""
    try:
        # Simple check to ensure the application is responding
        # You could add database connectivity check here if needed
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'guerrilla-t-timesheet'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

# Global variables for tracking
current_project = None
start_time = None
sync_thread = None
stop_sync = False


def sync_current_time():
    """Background thread to sync current time every minute"""
    global current_project, start_time, stop_sync
    
    while not stop_sync:
        # Just wait - we'll only log when tracking stops
        # This simplifies the logic and prevents double-counting
        
        # Wait for 60 seconds
        for _ in range(60):
            if stop_sync:
                break
            time.sleep(1)


def _get_customization_settings():
    """Get customization settings for templates"""
    try:
        settings = SystemSettingsService.get_all_settings()
        customization = settings.get('customization', [])
        
        # Convert list to dictionary
        custom_settings = {}
        for setting in customization:
            custom_settings[setting['setting_key']] = setting['setting_value']
        
        return {
            'company_name': custom_settings.get('custom_company_name', 'Guerrilla T'),
            'accent_color': custom_settings.get('custom_accent_color', '#007bff'),
            'logo_url': custom_settings.get('custom_logo_url', None)
        }
    except:
        # Fallback to defaults if settings service fails
        return {
            'company_name': 'Guerrilla T',
            'accent_color': '#007bff',
            'logo_url': None
        }


@main_bp.route('/')
@login_required
def index():
    """Main dashboard page"""
    today = datetime.now().strftime('%Y-%m-%d')
    selected_projects = ProjectService.get_selected_projects(today, current_user.id)
    available_projects = ProjectService.get_available_projects(today, current_user.id)
    aggregates = TimesheetService.get_daily_aggregate(today, current_user.id)
    customization = _get_customization_settings()
    
    return render_template('index.html', 
                         selected_projects=selected_projects,
                         available_projects=available_projects,
                         aggregates=aggregates,
                         current_project=current_project,
                         selected_date=today,
                         customization=customization)


@main_bp.route('/date/<date_str>')
@login_required
def index_date(date_str):
    """Dashboard for specific date"""
    selected_projects = ProjectService.get_selected_projects(date_str, current_user.id)
    available_projects = ProjectService.get_available_projects(date_str, current_user.id)
    aggregates = TimesheetService.get_daily_aggregate(date_str, current_user.id)
    customization = _get_customization_settings()
    
    return render_template('index.html', 
                         selected_projects=selected_projects,
                         available_projects=available_projects,
                         aggregates=aggregates,
                         current_project=current_project,
                         selected_date=date_str,
                         customization=customization)


@main_bp.route('/view_date/<date_str>')
@login_required
def view_date(date_str):
    """Detailed view for specific date"""
    all_projects = ProjectService.get_projects()
    selected_projects = ProjectService.get_selected_projects(date_str, current_user.id)
    aggregates = TimesheetService.get_daily_aggregate(date_str, current_user.id)
    entries = TimesheetService.get_time_entries(date_str, current_user.id)
    customization = _get_customization_settings()
    
    return render_template('date_view.html',
                         all_projects=all_projects,
                         selected_projects=selected_projects,
                         aggregates=aggregates,
                         entries=entries,
                         selected_date=date_str,
                         customization=customization)


def _stop_tracking_internal():
    """Internal function to stop tracking without HTTP response"""
    global current_project, start_time, stop_sync
    
    if not current_project or not start_time:
        return False
    
    # Stop sync thread
    stop_sync = True
    
    end_time = datetime.now()
    today = datetime.now().strftime('%Y-%m-%d')
    projects = ProjectService.get_projects()
    
    # Log the final time entry
    TimesheetService.log_time_entry(
        current_project, 
        projects.get(current_project, 'Unknown'), 
        start_time, 
        end_time, 
        today, 
        current_user.id
    )
    
    # Reset tracking variables
    tracked_project = current_project
    current_project = None
    start_time = None
    
    return tracked_project


@main_bp.route('/start_tracking', methods=['POST'])
@login_required
def start_tracking():
    """Start time tracking for a project"""
    global current_project, start_time, sync_thread, stop_sync
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request data'})
    
    project_id = data.get('project_id')
    
    # Stop any existing tracking first
    previous_project = None
    if current_project:
        previous_project = _stop_tracking_internal()
    
    # Start tracking the new project
    current_project = project_id
    start_time = datetime.now()
    
    # Start sync thread
    stop_sync = False
    sync_thread = threading.Thread(target=sync_current_time)
    sync_thread.daemon = True
    sync_thread.start()
    
    message = f'Started tracking {project_id}'
    if previous_project:
        message = f'Stopped tracking {previous_project} and started tracking {project_id}'
    
    return jsonify({'success': True, 'message': message})


@main_bp.route('/stop_tracking', methods=['POST'])
@login_required
def stop_tracking():
    """Stop time tracking"""
    if not current_project or not start_time:
        return jsonify({'success': False, 'message': 'No active tracking'})
    
    tracked_project = _stop_tracking_internal()
    
    if tracked_project:
        return jsonify({'success': True, 'message': f'Stopped tracking {tracked_project}'})
    else:
        return jsonify({'success': False, 'message': 'No active tracking'})


@main_bp.route('/get_current_status')
@login_required
def get_current_status():
    """Get current tracking status"""
    if current_project and start_time:
        elapsed = datetime.now() - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        return jsonify({
            'tracking': True,
            'project_id': current_project,
            'elapsed_minutes': round(elapsed_minutes, 2)
        })
    return jsonify({'tracking': False})


@main_bp.route('/add_project', methods=['POST'])
@login_required
def add_project():
    """Add project to daily selection"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request data'})
    
    project_id = data.get('project_id')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if ProjectService.add_project_to_day(project_id, date_str, current_user.id):
        return jsonify({'success': True, 'message': f'Added {project_id} to today\'s projects'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add project'})


@main_bp.route('/remove_project', methods=['POST'])
@login_required
def remove_project():
    """Remove project from daily selection"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request data'})
    
    project_id = data.get('project_id')
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if ProjectService.remove_project_from_day(project_id, date_str, current_user.id):
        return jsonify({'success': True, 'message': f'Removed {project_id} from today\'s projects'})
    else:
        return jsonify({'success': False, 'message': 'Failed to remove project'})


@main_bp.route('/edit_entry', methods=['POST'])
@login_required
def edit_entry():
    """Edit a time entry"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request data'})
    
    date_str = data.get('date')
    entry_id = int(data.get('entry_id'))
    new_duration = float(data.get('duration'))
    
    if TimesheetService.update_entry(entry_id, date_str, new_duration, current_user.id):
        return jsonify({'success': True, 'message': 'Entry updated successfully'})
    else:
        return jsonify({'success': False, 'message': 'Entry not found'})


@main_bp.route('/delete_entry', methods=['POST'])
@login_required
def delete_entry():
    """Delete a time entry"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request data'})
    
    date_str = data.get('date')
    entry_id = int(data.get('entry_id'))
    
    if TimesheetService.delete_entry(entry_id, date_str, current_user.id):
        return jsonify({'success': True, 'message': 'Entry deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Entry not found'})


@main_bp.route('/export_excel', methods=['POST'])
@login_required
def export_excel():
    """Export user's time tracking data to Excel"""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        start_date = data.get('start_date') if data else None
        end_date = data.get('end_date') if data else None
    else:
        # Handle form data
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'success': False, 'message': 'Please provide both start and end dates'})
    
    try:
        # Validate date format
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_date > end_date:
            return jsonify({'success': False, 'message': 'Start date must be before end date'})
        
        # Generate Excel file
        excel_file = ExportService.generate_excel_export(start_date, end_date, current_user.id)
        
        # Create filename
        filename = "timesheet.xlsx"
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'})
    except Exception as e:
        print(f"Export error: {e}")
        return jsonify({'success': False, 'message': 'Error generating export file'})
