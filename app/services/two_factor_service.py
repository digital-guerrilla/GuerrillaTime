"""
Two-Factor Authentication service using TOTP (Time-based One-Time Password)
"""

import pyotp
import qrcode
import io
import base64
import json
import secrets
from ..models.database import get_db_connection


class TwoFactorService:
    """Service for managing TOTP-based 2FA"""
    
    @staticmethod
    def generate_secret():
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(email, secret, issuer_name="Timesheet Tracker"):
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for display in HTML
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_token(secret, token):
        """Verify a TOTP token"""
        if not secret or not token:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            # Allow a window of 1 period (30 seconds) before and after
            return totp.verify(token, valid_window=1)
        except:
            return False
    
    @staticmethod
    def generate_backup_codes(count=8):
        """Generate backup codes for 2FA recovery"""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            codes.append(code)
        return codes
    
    @staticmethod
    def enable_2fa_for_user(user_id, secret):
        """Enable 2FA for a user"""
        backup_codes = TwoFactorService.generate_backup_codes()
        backup_codes_json = json.dumps(backup_codes)
        
        conn = get_db_connection()
        try:
            conn.execute('''
                UPDATE users 
                SET totp_secret = ?, totp_enabled = 1, backup_codes = ?
                WHERE id = ?
            ''', (secret, backup_codes_json, user_id))
            conn.commit()
            return backup_codes
        finally:
            conn.close()
    
    @staticmethod
    def disable_2fa_for_user(user_id):
        """Disable 2FA for a user"""
        conn = get_db_connection()
        try:
            conn.execute('''
                UPDATE users 
                SET totp_secret = NULL, totp_enabled = 0, backup_codes = NULL
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def is_2fa_enabled(user_id):
        """Check if 2FA is enabled for a user"""
        conn = get_db_connection()
        try:
            result = conn.execute('''
                SELECT totp_enabled FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            return bool(result and result['totp_enabled'])
        finally:
            conn.close()
    
    @staticmethod
    def get_user_2fa_info(user_id):
        """Get 2FA information for a user"""
        conn = get_db_connection()
        try:
            result = conn.execute('''
                SELECT totp_secret, totp_enabled, backup_codes 
                FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if result:
                return {
                    'secret': result['totp_secret'],
                    'enabled': bool(result['totp_enabled']),
                    'backup_codes': json.loads(result['backup_codes']) if result['backup_codes'] else []
                }
            return None
        finally:
            conn.close()
    
    @staticmethod
    def use_backup_code(user_id, code):
        """Use a backup code and remove it from the list"""
        conn = get_db_connection()
        try:
            result = conn.execute('''
                SELECT backup_codes FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not result or not result['backup_codes']:
                return False
            
            backup_codes = json.loads(result['backup_codes'])
            
            if code.upper() in backup_codes:
                # Remove the used code
                backup_codes.remove(code.upper())
                
                # Update the database
                conn.execute('''
                    UPDATE users SET backup_codes = ? WHERE id = ?
                ''', (json.dumps(backup_codes), user_id))
                conn.commit()
                return True
            
            return False
        finally:
            conn.close()
    
    @staticmethod
    def regenerate_backup_codes(user_id):
        """Regenerate backup codes for a user"""
        backup_codes = TwoFactorService.generate_backup_codes()
        backup_codes_json = json.dumps(backup_codes)
        
        conn = get_db_connection()
        try:
            conn.execute('''
                UPDATE users SET backup_codes = ? WHERE id = ?
            ''', (backup_codes_json, user_id))
            conn.commit()
            return backup_codes
        finally:
            conn.close()
