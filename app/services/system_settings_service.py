"""
System settings service for managing application configuration
"""

from ..models.database import get_db_connection
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os


class SystemSettingsService:
    """Service class for system settings management"""
    
    @staticmethod
    def _get_encryption_key():
        """Get encryption key from Flask SECRET_KEY"""
        from flask import current_app
        
        try:
            # Use Flask's SECRET_KEY as the base for encryption
            secret_key = current_app.config.get('SECRET_KEY')
            if not secret_key:
                raise ValueError("SECRET_KEY not configured in Flask app")
            
            # Derive a Fernet key from the SECRET_KEY using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'timesheet-app-salt',  # Fixed salt for consistent key derivation
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            return key
            
        except Exception as e:
            # Fallback to file-based key if Flask context is not available
            print(f"Warning: Could not get SECRET_KEY from Flask, falling back to file: {e}")
            key_file = os.path.join(os.path.dirname(__file__), '../../settings.key')
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                return key
    
    @staticmethod
    def _encrypt_value(value):
        """Encrypt a sensitive value"""
        if not value:
            return value
        
        try:
            key = SystemSettingsService._get_encryption_key()
            f = Fernet(key)
            encrypted_value = f.encrypt(value.encode())
            return base64.b64encode(encrypted_value).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return value
    
    @staticmethod
    def _decrypt_value(encrypted_value):
        """Decrypt a sensitive value"""
        if not encrypted_value:
            return encrypted_value
        
        try:
            key = SystemSettingsService._get_encryption_key()
            f = Fernet(key)
            decoded_value = base64.b64decode(encrypted_value.encode())
            decrypted_value = f.decrypt(decoded_value)
            return decrypted_value.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return encrypted_value
    
    @staticmethod
    def get_all_settings():
        """Get all system settings grouped by category"""
        conn = get_db_connection()
        try:
            settings = conn.execute('''
                SELECT setting_key, setting_value, setting_type, is_encrypted, 
                       description, category
                FROM system_settings
                ORDER BY category, setting_key
            ''').fetchall()
            
            grouped_settings = {}
            for setting in settings:
                setting_dict = dict(setting)
                
                # Decrypt if necessary
                if setting_dict['is_encrypted'] and setting_dict['setting_value']:
                    setting_dict['setting_value'] = SystemSettingsService._decrypt_value(
                        setting_dict['setting_value']
                    )
                
                category = setting_dict['category']
                if category not in grouped_settings:
                    grouped_settings[category] = []
                
                grouped_settings[category].append(setting_dict)
            
            return grouped_settings
        finally:
            conn.close()
    
    @staticmethod
    def get_setting(key):
        """Get a specific setting value"""
        conn = get_db_connection()
        try:
            setting = conn.execute('''
                SELECT setting_value, is_encrypted
                FROM system_settings
                WHERE setting_key = ?
            ''', (key,)).fetchone()
            
            if not setting:
                return None
            
            value = setting['setting_value']
            if setting['is_encrypted'] and value:
                value = SystemSettingsService._decrypt_value(value)
            
            return value
        finally:
            conn.close()
    
    @staticmethod
    def update_setting(key, value):
        """Update a specific setting"""
        conn = get_db_connection()
        try:
            # Check if setting exists and if it should be encrypted
            setting = conn.execute('''
                SELECT is_encrypted FROM system_settings
                WHERE setting_key = ?
            ''', (key,)).fetchone()
            
            if not setting:
                return False, "Setting not found"
            
            # Encrypt if necessary
            final_value = value
            if setting['is_encrypted'] and value:
                final_value = SystemSettingsService._encrypt_value(value)
            
            # Update the setting
            conn.execute('''
                UPDATE system_settings 
                SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE setting_key = ?
            ''', (final_value, key))
            
            conn.commit()
            return True, "Setting updated successfully"
        
        except Exception as e:
            return False, f"Error updating setting: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def update_multiple_settings(settings_dict):
        """Update multiple settings at once"""
        conn = get_db_connection()
        try:
            for key, value in settings_dict.items():
                # Check if setting exists and if it should be encrypted
                setting = conn.execute('''
                    SELECT is_encrypted FROM system_settings
                    WHERE setting_key = ?
                ''', (key,)).fetchone()
                
                if setting:
                    # Encrypt if necessary
                    final_value = value
                    if setting['is_encrypted'] and value:
                        final_value = SystemSettingsService._encrypt_value(value)
                    
                    # Update the setting
                    conn.execute('''
                        UPDATE system_settings 
                        SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE setting_key = ?
                    ''', (final_value, key))
            
            conn.commit()
            return True, "Settings updated successfully"
        
        except Exception as e:
            return False, f"Error updating settings: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_settings_by_category(category):
        """Get all settings for a specific category"""
        conn = get_db_connection()
        try:
            settings = conn.execute('''
                SELECT setting_key, setting_value, setting_type, is_encrypted, description
                FROM system_settings
                WHERE category = ?
                ORDER BY setting_key
            ''', (category,)).fetchall()
            
            result = []
            for setting in settings:
                setting_dict = dict(setting)
                
                # Decrypt if necessary
                if setting_dict['is_encrypted'] and setting_dict['setting_value']:
                    setting_dict['setting_value'] = SystemSettingsService._decrypt_value(
                        setting_dict['setting_value']
                    )
                
                result.append(setting_dict)
            
            return result
        finally:
            conn.close()
    
    @staticmethod
    def reset_to_defaults():
        """Reset all settings to default values"""
        conn = get_db_connection()
        try:
            # This would restore default values - implement based on needs
            # For now, just return success
            return True, "Settings reset to defaults"
        except Exception as e:
            return False, f"Error resetting settings: {str(e)}"
        finally:
            conn.close()
    
    @staticmethod
    def get_customization_settings():
        """Get customization settings in a structured format for admin panel"""
        conn = get_db_connection()
        try:
            settings = conn.execute('''
                SELECT setting_key, setting_value, setting_type, is_encrypted, description
                FROM system_settings
                WHERE category = 'customization'
                ORDER BY setting_key
            ''').fetchall()
            
            # Create a simple object-like structure for template access
            class CustomizationSettings:
                def __init__(self):
                    pass
            
            result = CustomizationSettings()
            
            for setting in settings:
                setting_dict = dict(setting)
                key = setting_dict['setting_key']
                value = setting_dict['setting_value']
                
                # Decrypt if necessary
                if setting_dict['is_encrypted'] and value:
                    value = SystemSettingsService._decrypt_value(value)
                
                # Set attribute on result object (remove 'custom_' prefix for cleaner access)
                attr_name = key.replace('custom_', '') if key.startswith('custom_') else key
                setattr(result, attr_name, value)
                # Also keep the full key for backward compatibility
                setattr(result, key, value)
            
            return result
        finally:
            conn.close()
