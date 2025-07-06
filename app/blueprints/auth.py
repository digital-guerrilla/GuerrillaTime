"""
Authentication blueprint for login, registration, and logout
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from ..models.user import User, check_password, hash_password
from ..models.database import get_db_connection
from ..services.user_service import UserService
from ..services.microsoft_oauth_service import MicrosoftOAuthService
import secrets
import uuid

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password.')
            return render_template('login.html')
        
        conn = get_db_connection()
        try:
            user = conn.execute('''
                SELECT id, email, password_hash, is_admin, temp_password, is_disabled, 
                       auth_method, password_disabled, totp_enabled
                FROM users WHERE email = ?
            ''', (email,)).fetchone()
            
            if user:
                # Check if user is disabled
                if user['is_disabled']:
                    flash('Your account has been disabled. Please contact the administrator for assistance.')
                    return render_template('login.html')
                
                # Check if password authentication is disabled for this OAuth user
                password_disabled = user['password_disabled'] if 'password_disabled' in user.keys() else 0
                if password_disabled:
                    flash('Password authentication is disabled for your account. Please use Microsoft Sign-In to access your account.')
                    return render_template('login.html')
                
                # Check password
                if check_password(password, user['password_hash']):
                    # Check if 2FA is enabled
                    totp_enabled = user['totp_enabled'] if 'totp_enabled' in user.keys() else 0
                    if totp_enabled:
                        # Store user info in session for 2FA verification
                        session['pending_2fa_user_id'] = user['id']
                        session['pending_2fa_email'] = user['email']
                        session['pending_2fa_is_admin'] = bool(user['is_admin'])
                        return redirect(url_for('auth.verify_2fa'))
                    
                    user_obj = User(user['id'], user['email'], bool(user['is_admin']), bool(totp_enabled))
                    login_user(user_obj)
                    
                    # Check if user has temporary password and needs to change it
                    if user['temp_password']:
                        flash('Please change your temporary password.')
                        return redirect(url_for('auth.change_password'))
                    
                    next_page = request.args.get('next')
                    if next_page:
                        return redirect(next_page)
                    return redirect(url_for('main.index'))
                else:
                    flash('Invalid email or password.')
            else:
                flash('Invalid email or password.')
        finally:
            conn.close()
    
    # Get OAuth configuration for template
    try:
        oauth_service = MicrosoftOAuthService()
        oauth_enabled = oauth_service.is_enabled()
        password_auth_disabled = oauth_service.is_password_auth_disabled()
    except:
        oauth_enabled = False
        password_auth_disabled = False
    
    return render_template('login.html', 
                         oauth_enabled=oauth_enabled,
                         password_auth_disabled=password_auth_disabled)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password or not confirm_password:
            flash('Please fill in all fields.')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return render_template('register.html')
        
        conn = get_db_connection()
        try:
            # Check if user already exists
            existing_user = conn.execute('''
                SELECT id FROM users WHERE email = ?
            ''', (email,)).fetchone()
            
            if existing_user:
                flash('An account with this email already exists.')
                return render_template('register.html')
            
            # Create new user
            hashed_password = hash_password(password)
            conn.execute('''
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
            ''', (email, hashed_password))
            conn.commit()
            
            flash('Account created successfully! Please log in.')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred while creating your account.')
            print(f"Registration error: {e}")
        finally:
            conn.close()
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout handler"""
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password (required for temporary passwords)"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Please fill in all fields.')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.')
            return render_template('change_password.html')
        
        conn = get_db_connection()
        try:
            user = conn.execute('''
                SELECT password_hash FROM users WHERE id = ?
            ''', (current_user.id,)).fetchone()
            
            if not user or not check_password(current_password, user['password_hash']):
                flash('Current password is incorrect.')
                return render_template('change_password.html')
            
            # Update password
            hashed_password = hash_password(new_password)
            conn.execute('''
                UPDATE users 
                SET password_hash = ?, temp_password = NULL
                WHERE id = ?
            ''', (hashed_password, current_user.id))
            conn.commit()
            
            flash('Password changed successfully!')
            return redirect(url_for('main.index'))
        
        except Exception as e:
            flash('An error occurred while changing your password.')
            print(f"Password change error: {e}")
        finally:
            conn.close()
    
    return render_template('change_password.html')


@auth_bp.route('/oauth/microsoft/login')
def microsoft_oauth_login():
    """Initiate Microsoft OAuth login"""
    try:
        oauth_service = MicrosoftOAuthService()
        
        if not oauth_service.is_enabled():
            flash('Microsoft OAuth is not enabled.')
            return redirect(url_for('auth.login'))
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Get authorization URL with fixed redirect URI
        redirect_uri = oauth_service.get_redirect_uri()
        auth_url = oauth_service.get_auth_url(redirect_uri)
        
        return redirect(auth_url)
        
    except Exception as e:
        flash(f'OAuth initialization failed: {str(e)}')
        return redirect(url_for('auth.login'))


@auth_bp.route('/oauth/microsoft/callback')
def microsoft_oauth_callback():
    """Handle Microsoft OAuth callback"""
    try:
        oauth_service = MicrosoftOAuthService()
        
        # Handle OAuth response
        redirect_uri = oauth_service.get_redirect_uri()
        user_info, error = oauth_service.handle_auth_response(request.args, redirect_uri)
        
        if error:
            # Check for common configuration errors
            error_msg = error
            if "AADSTS9002313" in error:
                error_msg += "\n\n💡 Invalid request - this usually means:"
                error_msg += "\n• The redirect URI doesn't match what's configured in Azure"
                error_msg += "\n• The client secret is incorrect or expired"
                error_msg += "\n• The application (client) ID is incorrect"
                error_msg += f"\n\nExpected redirect URI: {oauth_service.get_redirect_uri()}"
                error_msg += "\n\nPlease verify in Azure Portal:"
                error_msg += "\n1. App Registration > Authentication > Redirect URIs"
                error_msg += "\n2. App Registration > Certificates & secrets > Client secrets"
                error_msg += "\n3. App Registration > Overview > Application (client) ID"
            elif "AADSTS50011" in error or "redirect_uri" in error.lower():
                error_msg += "\n\n💡 This usually means the redirect URI is not configured in your Azure app. Please add this URI in Azure Portal:\n"
                error_msg += oauth_service.get_redirect_uri()
            elif "AADSTS70001" in error:
                error_msg += "\n\n💡 Application not found or not properly configured in Azure."
            elif "AADSTS90014" in error:
                error_msg += "\n\n💡 Required permission 'User.Read' is missing from your Azure app."
            elif "AADSTS700016" in error:
                error_msg += "\n\n💡 Application with this identifier was not found. Check your Client ID."
            
            flash(f'OAuth authentication failed: {error_msg}')
            return redirect(url_for('auth.login'))
        
        if not user_info or not user_info.get('email'):
            flash('Failed to retrieve user information from Microsoft.')
            return redirect(url_for('auth.login'))
        
        # Check if user exists or create new one
        user_obj = _handle_oauth_user(user_info)
        
        if user_obj:
            login_user(user_obj)
            flash(f'Successfully logged in with Microsoft as {user_info["email"]}')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Failed to create or link user account.')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        flash(f'OAuth callback error: {str(e)}')
        return redirect(url_for('auth.login'))


def _handle_oauth_user(user_info):
    """Handle OAuth user - link existing account or create new one"""
    conn = get_db_connection()
    try:
        email = user_info['email']
        microsoft_id = user_info['id']
        name = user_info.get('name', email)
        
        # Check if user already exists by email
        existing_user = conn.execute('''
            SELECT id, email, is_admin, is_disabled, microsoft_id, auth_method, password_disabled 
            FROM users WHERE email = ?
        ''', (email,)).fetchone()
        
        if existing_user:
            # User exists - check if disabled
            if existing_user['is_disabled']:
                flash('Your account has been disabled. Please contact the administrator.')
                return None
            
            # Link Microsoft account and update to OAuth authentication
            if not existing_user['microsoft_id']:
                # First time linking OAuth to existing account
                try:
                    conn.execute('''
                        UPDATE users 
                        SET microsoft_id = ?, display_name = ?, auth_method = 'oauth', password_disabled = 1
                        WHERE id = ?
                    ''', (microsoft_id, name, existing_user['id']))
                    conn.commit()
                    flash(f'Microsoft account linked successfully. Password authentication has been disabled for enhanced security.')
                except Exception as update_error:
                    print(f"DEBUG: Error updating user: {update_error}")
                    return None
            else:
                # Already linked - just update display name if needed
                try:
                    current_display_name = existing_user['display_name'] if 'display_name' in existing_user.keys() else None
                    if current_display_name != name:
                        conn.execute('''
                            UPDATE users SET display_name = ? WHERE id = ?
                        ''', (name, existing_user['id']))
                        conn.commit()
                except Exception as update_error:
                    print(f"DEBUG: Error updating display name: {update_error}")
                    # Don't fail for display name update errors
            
            # Create and return user object
            try:
                existing_totp_enabled = existing_user['totp_enabled'] if 'totp_enabled' in existing_user.keys() else 0
                user_obj = User(existing_user['id'], existing_user['email'], bool(existing_user['is_admin']), bool(existing_totp_enabled))
                print(f"DEBUG: Successfully created user object for {existing_user['email']}")
                return user_obj
            except Exception as user_creation_error:
                print(f"DEBUG: Error creating user object: {user_creation_error}")
                return None
        
        else:
            # Create new user with OAuth authentication
            try:
                # Generate a random password (disabled for OAuth users)
                random_password = secrets.token_urlsafe(32)
                hashed_password = hash_password(random_password)
                
                conn.execute('''
                    INSERT INTO users (email, password_hash, microsoft_id, display_name, 
                                     temp_password, auth_method, password_disabled)
                    VALUES (?, ?, ?, ?, 0, 'oauth', 1)
                ''', (email, hashed_password, microsoft_id, name))
                conn.commit()
                
                # Get the new user
                new_user = conn.execute('''
                    SELECT id, email, is_admin 
                    FROM users WHERE email = ?
                ''', (email,)).fetchone()
                
                if new_user:
                    # OAuth users don't have 2FA enabled by default (since they use OAuth for additional security)
                    user_obj = User(new_user['id'], new_user['email'], bool(new_user['is_admin']), False)
                    flash(f'New OAuth account created for {email}. Welcome!')
                    return user_obj
                else:
                    print("ERROR: Failed to retrieve newly created user from database")
                    return None
                    
            except Exception as create_error:
                print(f"ERROR: Failed to create new OAuth user: {create_error}")
                return None
    
    except Exception as e:
        print(f"ERROR: Exception in _handle_oauth_user for {user_info.get('email', 'unknown')}: {e}")
        return None
    
    finally:
        conn.close()


@auth_bp.route('/oauth/debug-uri')
def debug_oauth_uri():
    """Debug route to show the exact redirect URI"""
    oauth_service = MicrosoftOAuthService()
    redirect_uri = oauth_service.get_redirect_uri()
    
    return f"""
    <h1>OAuth Debug Information</h1>
    <p><strong>Redirect URI that should be configured in Azure:</strong></p>
    <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px;">{redirect_uri}</pre>
    
    <h3>Steps to configure in Azure Portal:</h3>
    <ol>
        <li>Go to Azure Portal > Entra ID > App registrations</li>
        <li>Select your application</li>
        <li>Go to Authentication</li>
        <li>Under "Redirect URIs", click "Add a platform"</li>
        <li>Select "Web"</li>
        <li>Enter the redirect URI above</li>
        <li>Save the configuration</li>
    </ol>
    
    <p><a href="{url_for('auth.login')}">Back to Login</a></p>
    """


@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """Verify 2FA TOTP token"""
    if 'pending_2fa_user_id' not in session:
        flash('No pending 2FA verification.')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        backup_code = request.form.get('backup_code', '').strip()
        
        from ..services.two_factor_service import TwoFactorService
        user_id = session['pending_2fa_user_id']
        
        verified = False
        
        if token:
            # Verify TOTP token
            user_2fa_info = TwoFactorService.get_user_2fa_info(user_id)
            if user_2fa_info and TwoFactorService.verify_token(user_2fa_info['secret'], token):
                verified = True
        
        elif backup_code:
            # Verify backup code
            if TwoFactorService.use_backup_code(user_id, backup_code):
                verified = True
                flash('Backup code used successfully. Consider regenerating your backup codes.')
        
        if verified:
            # Login the user
            user_obj = User(
                session['pending_2fa_user_id'],
                session['pending_2fa_email'],
                session['pending_2fa_is_admin'],
                True  # totp_enabled
            )
            login_user(user_obj)
            
            # Clear session data
            session.pop('pending_2fa_user_id', None)
            session.pop('pending_2fa_email', None)
            session.pop('pending_2fa_is_admin', None)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid verification code. Please try again.')
    
    return render_template('verify_2fa.html')


@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Setup 2FA for the current user"""
    from ..services.two_factor_service import TwoFactorService
    
    # Check if 2FA is already enabled
    if TwoFactorService.is_2fa_enabled(current_user.id):
        flash('2FA is already enabled for your account.')
        return redirect(url_for('auth.manage_2fa'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        secret = session.get('temp_2fa_secret')
        
        if not secret:
            flash('Setup session expired. Please start again.')
            return redirect(url_for('auth.setup_2fa'))
        
        if TwoFactorService.verify_token(secret, token):
            # Enable 2FA for the user
            backup_codes = TwoFactorService.enable_2fa_for_user(current_user.id, secret)
            
            # Clear temporary session data
            session.pop('temp_2fa_secret', None)
            
            # Update current user object
            current_user.totp_enabled = True
            
            flash('2FA has been successfully enabled for your account!')
            return render_template('2fa_backup_codes.html', backup_codes=backup_codes)
        else:
            flash('Invalid verification code. Please try again.')
    
    # Generate new secret and QR code
    secret = TwoFactorService.generate_secret()
    session['temp_2fa_secret'] = secret
    qr_code = TwoFactorService.generate_qr_code(current_user.email, secret)
    
    return render_template('setup_2fa.html', qr_code=qr_code, secret=secret)


@auth_bp.route('/manage-2fa')
@login_required
def manage_2fa():
    """Manage 2FA settings"""
    from ..services.two_factor_service import TwoFactorService
    
    is_enabled = TwoFactorService.is_2fa_enabled(current_user.id)
    backup_codes_count = 0
    
    if is_enabled:
        user_2fa_info = TwoFactorService.get_user_2fa_info(current_user.id)
        if user_2fa_info:
            backup_codes_count = len(user_2fa_info['backup_codes'])
    
    return render_template('manage_2fa.html', 
                         is_2fa_enabled=is_enabled, 
                         backup_codes_count=backup_codes_count)


@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for the current user"""
    from ..services.two_factor_service import TwoFactorService
    
    password = request.form.get('password', '')
    
    if not password:
        flash('Password is required to disable 2FA.')
        return redirect(url_for('auth.manage_2fa'))
    
    # Verify current password
    conn = get_db_connection()
    try:
        user = conn.execute('''
            SELECT password_hash FROM users WHERE id = ?
        ''', (current_user.id,)).fetchone()
        
        if not user or not check_password(password, user['password_hash']):
            flash('Incorrect password.')
            return redirect(url_for('auth.manage_2fa'))
        
        # Disable 2FA
        TwoFactorService.disable_2fa_for_user(current_user.id)
        current_user.totp_enabled = False
        
        flash('2FA has been disabled for your account.')
        return redirect(url_for('auth.manage_2fa'))
    
    finally:
        conn.close()


@auth_bp.route('/regenerate-backup-codes', methods=['POST'])
@login_required
def regenerate_backup_codes():
    """Regenerate backup codes for the current user"""
    from ..services.two_factor_service import TwoFactorService
    
    if not TwoFactorService.is_2fa_enabled(current_user.id):
        flash('2FA is not enabled for your account.')
        return redirect(url_for('auth.manage_2fa'))
    
    password = request.form.get('password', '')
    
    if not password:
        flash('Password is required to regenerate backup codes.')
        return redirect(url_for('auth.manage_2fa'))
    
    # Verify current password
    conn = get_db_connection()
    try:
        user = conn.execute('''
            SELECT password_hash FROM users WHERE id = ?
        ''', (current_user.id,)).fetchone()
        
        if not user or not check_password(password, user['password_hash']):
            flash('Incorrect password.')
            return redirect(url_for('auth.manage_2fa'))
        
        # Regenerate backup codes
        backup_codes = TwoFactorService.regenerate_backup_codes(current_user.id)
        
        flash('New backup codes have been generated. Please save them securely.')
        return render_template('2fa_backup_codes.html', backup_codes=backup_codes)
    
    finally:
        conn.close()
