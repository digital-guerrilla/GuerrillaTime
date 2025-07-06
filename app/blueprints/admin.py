from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from ..services.project_service import ProjectService
from ..services.user_service import UserService
from ..services.system_settings_service import SystemSettingsService
from ..services.microsoft_oauth_service import MicrosoftOAuthService
import csv
import io
import json
import requests

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@admin_bp.route('/admin/')
@login_required
def admin_panel():
    """Admin panel main page"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    return render_template('admin.html')


@admin_bp.route('/api/docs')
@login_required
def api_docs():
    """API documentation page for Power BI integration"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    return render_template('api_docs.html')


@admin_bp.route('/projects')
@login_required
def project_management():
    """Project management page"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    # Get status filter from query parameter
    status_filter = request.args.get('status', 'all')
    if status_filter not in ['all', 'live', 'finished']:
        status_filter = 'all'
    
    projects = ProjectService.get_projects_with_stats(status_filter)
    stats = ProjectService.get_project_statistics()
    
    return render_template('project_management.html', 
                         projects=projects,
                         total_time_minutes=stats['total_time_minutes'],
                         active_projects=stats['active_projects'],
                         current_filter=status_filter)


@admin_bp.route('/projects/add', methods=['POST'])
@login_required
def add_project():
    """Add a new project"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    project_id = request.form.get('project_id', '').strip().upper()
    project_name = request.form.get('project_name', '').strip()
    
    if not project_id or not project_name:
        flash('Both Project ID and Project Name are required.')
        return redirect(url_for('admin.project_management'))
    
    success, message = ProjectService.add_project(project_id, project_name)
    
    if success:
        flash(message)
    else:
        flash(f'Error: {message}')
    
    return redirect(url_for('admin.project_management'))


@admin_bp.route('/projects/edit', methods=['POST'])
@login_required
def edit_project():
    """Edit an existing project"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    project_id = request.form.get('project_id', '').strip()
    project_name = request.form.get('project_name', '').strip()
    
    if not project_id or not project_name:
        flash('Both Project ID and Project Name are required.')
        return redirect(url_for('admin.project_management'))
    
    success, message = ProjectService.update_project(project_id, project_name)
    
    if success:
        flash(message)
    else:
        flash(f'Error: {message}')
    
    return redirect(url_for('admin.project_management'))


@admin_bp.route('/projects/delete', methods=['POST'])
@login_required
def delete_project():
    """Delete a project"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    project_id = request.form.get('project_id', '').strip()
    
    if not project_id:
        flash('Project ID is required.')
        return redirect(url_for('admin.project_management'))
    
    success, message = ProjectService.delete_project(project_id)
    
    if success:
        flash(message)
    else:
        flash(f'Error: {message}')
    
    return redirect(url_for('admin.project_management'))


@admin_bp.route('/projects/upload', methods=['POST'])
@login_required
def upload_projects_csv():
    """Upload projects from CSV file"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    if 'csv_file' not in request.files:
        flash('No file selected.')
        return redirect(url_for('admin.project_management'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('admin.project_management'))
    
    if not file.filename or not file.filename.lower().endswith('.csv'):
        flash('Please upload a CSV file.')
        return redirect(url_for('admin.project_management'))
    
    try:
        # Read the CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        
        # Skip header row if present
        first_row = next(csv_input, None)
        if not first_row:
            flash('CSV file is empty.')
            return redirect(url_for('admin.project_management'))
        
        # Check if first row looks like headers
        if first_row[0].lower() in ['project_id', 'project id', 'id']:
            # Skip header row
            pass
        else:
            # First row is data, reset the stream
            stream.seek(0)
            csv_input = csv.reader(stream)
        
        added_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=1):
            if len(row) < 2:
                error_count += 1
                errors.append(f"Row {row_num}: Not enough columns (expected at least 2)")
                continue
            
            project_id = row[0].strip().upper()
            project_name = row[1].strip()
            
            if not project_id or not project_name:
                error_count += 1
                errors.append(f"Row {row_num}: Missing project ID or name")
                continue
            
            success, message = ProjectService.add_project(project_id, project_name)
            
            if success:
                added_count += 1
            else:
                error_count += 1
                errors.append(f"Row {row_num}: {message}")
        
        # Provide feedback
        if added_count > 0:
            flash(f'Successfully added {added_count} project(s).')
        
        if error_count > 0:
            flash(f'Failed to add {error_count} project(s). Errors: {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}')
        
        if added_count == 0 and error_count == 0:
            flash('No valid projects found in CSV file.')
    
    except Exception as e:
        flash(f'Error processing CSV file: {str(e)}')
    
    return redirect(url_for('admin.project_management'))


@admin_bp.route('/projects/status', methods=['POST'])
@login_required
def update_project_status():
    """Update project status (live/finished)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    project_id = request.form.get('project_id', '').strip()
    status = request.form.get('status', '').strip()
    
    if not project_id or not status:
        flash('Project ID and status are required.')
        return redirect(url_for('admin.project_management'))
    
    success, message = ProjectService.update_project_status(project_id, status)
    
    if success:
        flash(message)
    else:
        flash(f'Error: {message}')
    
    return redirect(url_for('admin.project_management'))


# User Management Routes
@admin_bp.route('/users')
@login_required
def user_management():
    """User management page"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    # Get status filter from query parameter
    status_filter = request.args.get('status', 'all')
    if status_filter not in ['all', 'active', 'disabled', 'oauth']:
        status_filter = 'all'
    
    # Use detailed user information that includes OAuth status
    users = UserService.get_users_with_stats(status_filter)
    stats = UserService.get_user_statistics()
    oauth_users = UserService.get_oauth_users()
    
    return render_template('user_management.html', 
                         users=users,
                         stats=stats,
                         oauth_users=oauth_users,
                         current_filter=status_filter,
                         total_user_time_minutes=stats.get('total_time_minutes', 0),
                         active_users_count=stats.get('active_users', 0))


@admin_bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    """Add a new user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    email = request.form.get('email', '').strip().lower()
    is_admin = request.form.get('is_admin') == 'on'
    
    if not email:
        flash('Email is required.')
        return redirect(url_for('admin.user_management'))
    
    success, message = UserService.create_user(email, is_admin)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/edit', methods=['POST'])
@login_required
def edit_user():
    """Edit an existing user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    user_id = request.form.get('user_id')
    email = request.form.get('email', '').strip().lower()
    is_admin = request.form.get('is_admin') == 'on'
    
    if not user_id or not email:
        flash('User ID and email are required.')
        return redirect(url_for('admin.user_management'))
    
    success, message = UserService.update_user(user_id, email, is_admin)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/delete', methods=['POST'])
@login_required
def delete_user():
    """Delete a user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    user_id = request.form.get('user_id')
    
    if not user_id:
        flash('User ID is required.')
        return redirect(url_for('admin.user_management'))
    
    # Prevent admin from deleting themselves
    if str(user_id) == str(current_user.id):
        flash('You cannot delete your own account.')
        return redirect(url_for('admin.user_management'))
    
    success, message = UserService.delete_user(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/reset-password', methods=['POST'])
@login_required
def reset_user_password():
    """Reset user password"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    user_id = request.form.get('user_id')
    
    if not user_id:
        flash('User ID is required.')
        return redirect(url_for('admin.user_management'))
    
    success, message = UserService.reset_user_password(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/upload', methods=['POST'])
@login_required
def upload_users_csv():
    """Upload users from CSV file"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    if 'csv_file' not in request.files:
        flash('No file selected.')
        return redirect(url_for('admin.user_management'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('admin.user_management'))
    
    if not file.filename or not file.filename.lower().endswith('.csv'):
        flash('Please upload a CSV file.')
        return redirect(url_for('admin.user_management'))
    
    try:
        csv_content = file.stream.read().decode("UTF8")
        success, result = UserService.import_users_from_csv(csv_content)
        
        if success:
            added_count = result['added_count']
            error_count = result['error_count']
            errors = result['errors']
            
            if added_count > 0:
                flash(f'Successfully added {added_count} user(s).', 'success')
            
            if error_count > 0:
                error_msg = f'Failed to add {error_count} user(s).'
                if errors:
                    error_msg += f' Errors: {"; ".join(errors)}'
                flash(error_msg, 'error')
            
            if added_count == 0 and error_count == 0:
                flash('No valid users found in CSV file.')
        else:
            flash(f'Error processing CSV file: {result}', 'error')
    
    except Exception as e:
        flash(f'Error processing CSV file: {str(e)}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/update-status', methods=['POST'])
@login_required
def update_user_status():
    """Update user status (enable/disable)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    user_id = request.form.get('user_id')
    status = request.form.get('status')
    
    if not user_id or not status:
        flash('User ID and status are required.')
        return redirect(url_for('admin.user_management'))
    
    # Prevent admin from disabling themselves
    if str(user_id) == str(current_user.id) and status == 'disabled':
        flash('You cannot disable your own account.')
        return redirect(url_for('admin.user_management'))
    
    success, message = UserService.update_user_status(user_id, status)
    
    if success:
        flash(message, 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/users/enable-password/<int:user_id>', methods=['POST'])
@login_required
def enable_password_auth(user_id):
    """Re-enable password authentication for an OAuth user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    success, message = UserService.enable_password_auth(user_id)
    
    if success:
        flash(message)
    else:
        flash(f'Error: {message}')
    
    return redirect(url_for('admin.user_management'))


# System Settings Routes
@admin_bp.route('/settings')
@login_required
def system_settings():
    """System settings page"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    # Get all settings grouped by category
    settings_grouped = SystemSettingsService.get_all_settings()
    
    # Convert to a more template-friendly format
    settings = {}
    for category, setting_list in settings_grouped.items():
        # Create a simple object-like structure for easier template access
        class SettingsCategory:
            def __init__(self):
                pass
        
        category_settings = SettingsCategory()
        for setting in setting_list:
            setattr(category_settings, setting['setting_key'], setting['setting_value'])
        
        settings[category] = category_settings
    
    return render_template('system_settings.html', settings=settings)


@admin_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update system settings"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    category = request.form.get('category')
    if not category:
        flash('Invalid settings category.')
        return redirect(url_for('admin.system_settings'))
    
    # Get all form data except category
    settings_to_update = {}
    for key, value in request.form.items():
        if key != 'category':
            settings_to_update[key] = value
    
    # Handle checkboxes (they don't appear in form data if unchecked)
    if category == 'oauth':
        # Ensure boolean settings are properly handled
        if 'oauth_allow_sso' not in settings_to_update:
            settings_to_update['oauth_allow_sso'] = 'false'
        if 'oauth_disable_passwords' not in settings_to_update:
            settings_to_update['oauth_disable_passwords'] = 'false'
    
    # Handle file uploads (logo)
    if category == 'customization' and 'logo_upload' in request.files:
        logo_file = request.files['logo_upload']
        if logo_file and logo_file.filename:
            import os
            import uuid
            
            # Get current logo to delete old file
            current_logo = SystemSettingsService.get_setting('custom_logo_url')
            if current_logo and current_logo.startswith('/static/uploads/'):
                old_file_path = current_logo[1:]  # Remove leading slash
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                    except:
                        pass  # Continue even if old file deletion fails
            
            # Save new logo file
            file_extension = logo_file.filename.split('.')[-1].lower()
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
            if file_extension not in allowed_extensions:
                flash('Invalid file type. Please upload a PNG, JPG, GIF, SVG, or WebP image.', 'error')
                return redirect(url_for('admin.system_settings'))
            
            filename = f"logo_{uuid.uuid4().hex[:8]}.{file_extension}"
            logo_path = os.path.join('static', 'uploads', filename)
            
            # Create uploads directory if it doesn't exist
            os.makedirs(os.path.dirname(logo_path), exist_ok=True)
            
            # Save file
            logo_file.save(logo_path)
            settings_to_update['custom_logo_url'] = f"/static/uploads/{filename}"
    
    # Update settings
    success, message = SystemSettingsService.update_multiple_settings(settings_to_update)
    
    if success:
        flash(f'{category.title()} settings updated successfully.', 'success')
    else:
        flash(f'Error updating settings: {message}', 'error')
    
    return redirect(url_for('admin.system_settings'))


@admin_bp.route('/settings/delete-logo', methods=['POST'])
@login_required
def delete_logo():
    """Delete the current company logo"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'})
    
    try:
        # Get current logo URL
        current_logo = SystemSettingsService.get_setting('custom_logo_url')
        
        if current_logo:
            # Delete the file if it exists
            import os
            if current_logo.startswith('/static/uploads/'):
                file_path = current_logo[1:]  # Remove leading slash
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Remove from database
            success, message = SystemSettingsService.update_multiple_settings({
                'custom_logo_url': ''
            })
            
            if success:
                return jsonify({'success': True, 'message': 'Logo deleted successfully.'})
            else:
                return jsonify({'success': False, 'message': f'Error updating database: {message}'})
        else:
            return jsonify({'success': False, 'message': 'No logo found to delete.'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting logo: {str(e)}'})


@admin_bp.route('/settings/reset', methods=['POST'])
@login_required
def reset_settings():
    """Reset settings to defaults"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.index'))
    
    success, message = SystemSettingsService.reset_to_defaults()
    
    if success:
        flash('Settings reset to defaults successfully.', 'success')
    else:
        flash(f'Error resetting settings: {message}', 'error')
    
    return redirect(url_for('admin.system_settings'))


@admin_bp.route('/test-oauth-config', methods=['POST'])
@login_required
def test_oauth_config():
    """Test OAuth configuration"""
    if not current_user.is_admin:
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        oauth_service = MicrosoftOAuthService()
        success, message = oauth_service.test_configuration()
        
        return {
            'success': success,
            'message': message
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Test failed: {str(e)}'
        }


@admin_bp.route('/disable-password-auth', methods=['POST'])
@login_required
def disable_password_auth():
    """Disable password authentication for existing users when SSO-only mode is enabled"""
    if not current_user.is_admin:
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        oauth_service = MicrosoftOAuthService()
        
        if not oauth_service.is_enabled():
            return {
                'success': False,
                'message': 'Microsoft OAuth must be enabled before disabling password authentication'
            }
        
        # This would be called when admin enables "Disable Password Authentication" 
        # The actual disabling is handled by the setting itself
        # This route could be used for additional cleanup if needed
        
        return {
            'success': True,
            'message': 'Password authentication disabled. Users will now be required to use Microsoft Sign-In.'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


@admin_bp.route('/debug-oauth-tenant', methods=['POST'])
@login_required
def debug_oauth_tenant():
    """Debug OAuth tenant configuration specifically"""
    if not current_user.is_admin:
        return {'success': False, 'message': 'Access denied'}, 403
    
    try:
        oauth_service = MicrosoftOAuthService()
        settings = oauth_service._get_oauth_settings()
        
        if not settings or not settings.get('oauth_tenant_id'):
            return {
                'success': False,
                'message': 'No tenant ID configured'
            }
        
        tenant_id = settings['oauth_tenant_id'].strip()
        
        # Get detailed guidance
        guidance = oauth_service.get_tenant_guidance(tenant_id)
        
        # Test the specific URL that's failing
        test_url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid_configuration"
        
        try:
            response = requests.get(test_url, timeout=10)
            status_msg = f"URL Test Result: {response.status_code}"
            if response.status_code != 200:
                status_msg += f"\nResponse: {response.text[:500]}"
        except Exception as e:
            status_msg = f"URL Test Failed: {str(e)}"
        
        debug_info = f"""
Tenant ID Debug Information:
============================
Configured Tenant ID: '{tenant_id}'
Length: {len(tenant_id)} characters

{guidance}

Test URL: {test_url}
{status_msg}

Common Solutions:
• Copy tenant ID directly from Azure Portal > Entra ID > Overview
• Ensure no extra spaces or characters
• Use the Directory (tenant) ID, not the Application ID
• For personal Microsoft accounts, try 'consumers' as tenant ID
        """
        
        return {
            'success': True,
            'message': debug_info.strip()
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Debug failed: {str(e)}'
        }


@admin_bp.route('/custom.css')
def custom_css():
    """Serve custom CSS with dynamic variables"""
    from ..utils.customization import generate_custom_css
    from flask import Response
    
    try:
        css = generate_custom_css(SystemSettingsService)
        response = Response(css, mimetype='text/css')
        # Cache for 5 minutes
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
    except Exception as e:
        # Return empty CSS on error
        return Response('/* Error generating custom CSS */', mimetype='text/css')

