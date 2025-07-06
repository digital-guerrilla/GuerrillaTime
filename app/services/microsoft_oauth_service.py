"""
Microsoft OAuth Service using MSAL
Handles authentication, token management, and user profile retrieval
"""

import msal
import requests
from flask import current_app, session, url_for
from ..services.system_settings_service import SystemSettingsService
import logging

logger = logging.getLogger(__name__)

class MicrosoftOAuthService:
    def __init__(self):
        self.settings_service = SystemSettingsService()
        self._msal_app = None
        self._scopes = ["User.Read"]  # Basic profile information
    
    def _get_oauth_settings(self):
        """Get OAuth settings as a dictionary"""
        settings_list = self.settings_service.get_settings_by_category('oauth')
        
        # Convert list to dictionary for easier access
        settings = {}
        if settings_list:
            for setting in settings_list:
                settings[setting['setting_key']] = setting['setting_value']
        
        return settings
    
    def _get_msal_app(self):
        """Get MSAL application instance with current settings"""
        if not self._msal_app:
            settings = self._get_oauth_settings()
            
            if not settings or not settings.get('oauth_tenant_id') or not settings.get('oauth_client_id'):
                raise ValueError("Microsoft OAuth not configured. Please configure in System Settings.")
            
            tenant_id = settings['oauth_tenant_id'].strip()
            client_id = settings['oauth_client_id'].strip()
            client_secret = settings['oauth_client_secret'].strip()
            
            # Validate tenant ID format
            if not self._validate_tenant_id(tenant_id):
                raise ValueError(f"Invalid tenant ID format: '{tenant_id}'. Expected a GUID or domain name.")
            
            authority = f"https://login.microsoftonline.com/{tenant_id}"
            
            try:
                self._msal_app = msal.ConfidentialClientApplication(
                    client_id=client_id,
                    client_credential=client_secret,
                    authority=authority
                )
            except Exception as e:
                raise ValueError(f"Failed to create MSAL application: {str(e)}. Check your Tenant ID, Client ID, and Client Secret.")
        
        return self._msal_app
    
    def is_enabled(self):
        """Check if Microsoft OAuth is enabled and configured"""
        try:
            settings = self._get_oauth_settings()
            
            return (settings and 
                   settings.get('oauth_allow_sso') == 'true' and
                   settings.get('oauth_tenant_id') and 
                   settings.get('oauth_client_id') and 
                   settings.get('oauth_client_secret'))
        except Exception as e:
            logger.error(f"Error checking OAuth configuration: {e}")
            return False
    
    def is_password_auth_disabled(self):
        """Check if password authentication is disabled (SSO only mode)"""
        try:
            settings = self._get_oauth_settings()
            
            return settings and settings.get('oauth_disable_passwords') == 'true'
        except Exception as e:
            logger.error(f"Error checking password auth status: {e}")
            return False
    
    def get_auth_url(self, redirect_uri):
        """Get Microsoft OAuth authorization URL"""
        try:
            msal_app = self._get_msal_app()
            
            # Get state from session
            state = session.get('oauth_state')
            if not state:
                # This shouldn't happen as state should be set in the route
                logger.warning("No state found in session, using fallback")
                state = 'fallback_state'
            
            # Debug: Log the parameters being used
            logger.info(f"OAuth request parameters:")
            logger.info(f"  Redirect URI: {redirect_uri}")
            logger.info(f"  Scopes: {self._scopes}")
            logger.info(f"  State: {state}")
            
            # Validate redirect URI format
            if not redirect_uri or not redirect_uri.startswith('http'):
                raise ValueError(f"Invalid redirect URI: {redirect_uri}")
            
            auth_url = msal_app.get_authorization_request_url(
                scopes=self._scopes,
                redirect_uri=redirect_uri,
                state=state
            )
            
            logger.info(f"Generated auth URL: {auth_url}")
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            raise
    
    def handle_auth_response(self, request_args, redirect_uri):
        """Handle OAuth callback and get user information"""
        try:
            msal_app = self._get_msal_app()
            
            # Debug: Log the callback parameters
            logger.info(f"OAuth callback parameters:")
            logger.info(f"  Redirect URI: {redirect_uri}")
            logger.info(f"  Request args: {dict(request_args)}")
            
            # Validate state parameter for CSRF protection
            received_state = request_args.get('state')
            expected_state = session.get('oauth_state')
            
            logger.info(f"State validation:")
            logger.info(f"  Expected state: {expected_state}")
            logger.info(f"  Received state: {received_state}")
            
            if not received_state or not expected_state or received_state != expected_state:
                logger.error("State validation failed - possible CSRF attack")
                return None, "Authentication failed: Invalid state parameter"
            
            # Extract the authorization code from request args
            authorization_code = request_args.get('code')
            
            if not authorization_code:
                logger.error("No authorization code found in callback")
                return None, "Authentication failed: No authorization code received"
            
            logger.info(f"Authorization code received: {authorization_code[:20]}...")
            
            # Get token from authorization code (using just the code, not the full response)
            result = msal_app.acquire_token_by_authorization_code(
                authorization_code,
                scopes=self._scopes,
                redirect_uri=redirect_uri
            )
            
            # Debug: Log the result (without sensitive info)
            if "error" in result:
                logger.error(f"Token acquisition failed:")
                logger.error(f"  Error: {result.get('error')}")
                logger.error(f"  Error description: {result.get('error_description')}")
                logger.error(f"  Error codes: {result.get('error_codes', [])}")
                logger.error(f"  Correlation ID: {result.get('correlation_id')}")
                logger.error(f"  Trace ID: {result.get('trace_id')}")
                logger.error(f"  Sub error: {result.get('suberror')}")
                logger.error(f"  Claims: {result.get('claims')}")
                # Print to console as well for easier debugging
                print(f"OAUTH ERROR: {result.get('error')} - {result.get('error_description')}")
                print(f"ERROR CODES: {result.get('error_codes', [])}")
            else:
                logger.info("Token acquisition successful")
                print("OAUTH SUCCESS: Token acquired successfully")
            
            if "error" in result:
                error_desc = result.get('error_description', result.get('error'))
                logger.error(f"OAuth error: {error_desc}")
                return None, f"Authentication failed: {error_desc}"
            
            # Clear the state from session after successful token acquisition
            session.pop('oauth_state', None)
            
            # Get user profile information
            access_token = result.get('access_token')
            user_info = self._get_user_profile(access_token)
            
            if not user_info:
                return None, "Failed to retrieve user profile information"
            
            return user_info, None
            
        except Exception as e:
            logger.error(f"Error handling auth response: {e}")
            return None, str(e)
    
    def _get_user_profile(self, access_token):
        """Get user profile from Microsoft Graph API"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                profile = response.json()
                return {
                    'id': profile.get('id'),
                    'email': profile.get('mail') or profile.get('userPrincipalName'),
                    'name': profile.get('displayName'),
                    'given_name': profile.get('givenName'),
                    'family_name': profile.get('surname')
                }
            else:
                logger.error(f"Failed to get user profile: {response.status_code} {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    def test_configuration(self):
        """Test OAuth configuration without full authentication flow"""
        try:
            settings = self._get_oauth_settings()
            
            if not settings:
                return False, "No OAuth settings found"
            
            required_fields = ['oauth_tenant_id', 'oauth_client_id', 'oauth_client_secret']
            missing_fields = [field for field in required_fields if not settings.get(field)]
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Validate tenant ID format
            tenant_id = settings['oauth_tenant_id'].strip()
            if not self._validate_tenant_id(tenant_id):
                return False, f"Invalid tenant ID format: '{tenant_id}'. Expected a GUID (e.g., 12345678-1234-1234-1234-123456789012) or domain name (e.g., yourdomain.onmicrosoft.com)"
            
            # Test MSAL app creation
            try:
                msal_app = self._get_msal_app()
                success_msg = "✅ Microsoft OAuth configuration is valid\n"
                success_msg += f"✅ Tenant ID format is correct: {tenant_id}\n"
            except Exception as e:
                return False, f"MSAL app creation failed: {str(e)}"
            
            # Test authority endpoint accessibility with better error handling
            try:
                authority_url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid_configuration"
                success_msg += f"🔍 Testing authority URL: {authority_url}\n"
                
                response = requests.get(authority_url, timeout=10)
                
                if response.status_code == 200:
                    success_msg += "✅ Tenant authority is accessible\n"
                    # Try to parse the response to ensure it's valid
                    try:
                        config = response.json()
                        if 'authorization_endpoint' in config:
                            success_msg += "✅ Authority configuration is valid\n"
                        else:
                            success_msg += "⚠️  Authority response is missing expected fields\n"
                    except:
                        success_msg += "⚠️  Authority response is not valid JSON\n"
                elif response.status_code == 404:
                    return False, f"❌ Tenant not found (404). Please check your Tenant ID.\n\nCommon issues:\n• Tenant ID should be a GUID or domain name\n• For personal Microsoft accounts, use 'consumers'\n• For work/school accounts, use your organization's tenant ID\n\nCurrent tenant ID: '{tenant_id}'"
                elif response.status_code == 400:
                    return False, f"❌ Bad request (400). The tenant ID format may be incorrect.\n\nCurrent tenant ID: '{tenant_id}'\nExpected format: GUID (12345678-1234-1234-1234-123456789012) or domain (yourdomain.onmicrosoft.com)"
                else:
                    success_msg += f"⚠️  Tenant authority check failed (Status: {response.status_code})\n"
                    success_msg += f"Response: {response.text[:200]}...\n"
                    success_msg += "This may indicate a configuration issue.\n"
            except requests.exceptions.Timeout:
                success_msg += "⚠️  Tenant authority check timed out\n"
                success_msg += "This may be a network issue.\n"
            except requests.exceptions.RequestException as e:
                success_msg += f"⚠️  Tenant authority check failed: {str(e)}\n"
                success_msg += "This may be a network or configuration issue.\n"
            except Exception as e:
                success_msg += f"⚠️  Tenant authority check failed: {str(e)}\n"
            
            # Add setup instructions
            success_msg += "\n📋 Next steps:\n"
            success_msg += f"1. Add this redirect URI to your Azure app: {self._get_redirect_uri()}\n"
            success_msg += "2. Ensure your app has 'User.Read' permission\n"
            success_msg += "3. Test the full login flow"
            
            return True, success_msg
            
        except Exception as e:
            logger.error(f"Error testing OAuth configuration: {e}")
            return False, str(e)
    
    def debug_settings(self):
        """Debug method to see what settings are actually stored"""
        try:
            settings_list = self.settings_service.get_settings_by_category('oauth')
            
            debug_info = "OAuth Settings Debug:\n"
            debug_info += "===================\n"
            
            if not settings_list:
                debug_info += "❌ No OAuth settings found in database\n"
                return debug_info
            
            debug_info += f"Found {len(settings_list)} OAuth settings:\n\n"
            
            for setting in settings_list:
                debug_info += f"Key: '{setting['setting_key']}'\n"
                debug_info += f"Value: '{setting['setting_value']}'\n"
                debug_info += f"Type: {setting['setting_type']}\n"
                debug_info += f"Encrypted: {setting['is_encrypted']}\n"
                debug_info += "---\n"
            
            # Also show the converted dictionary
            settings_dict = self._get_oauth_settings()
            debug_info += "\nConverted to dictionary:\n"
            for key, value in settings_dict.items():
                if 'secret' in key.lower():
                    debug_info += f"  {key}: [HIDDEN]\n"
                else:
                    debug_info += f"  {key}: '{value}'\n"
            
            return debug_info
            
        except Exception as e:
            return f"Debug failed: {str(e)}"
    
    def _validate_tenant_id(self, tenant_id):
        """Validate tenant ID format"""
        import re
        
        # Remove any whitespace
        tenant_id = tenant_id.strip()
        
        # Check for GUID format
        guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        if re.match(guid_pattern, tenant_id):
            return True
        
        # Check for domain format (e.g., yourdomain.onmicrosoft.com)
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]\.onmicrosoft\.com$'
        if re.match(domain_pattern, tenant_id):
            return True
        
        # Check for special tenant IDs
        special_tenants = ['common', 'organizations', 'consumers']
        if tenant_id.lower() in special_tenants:
            return True
        
        # Check for custom domain (basic validation)
        custom_domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$'
        if re.match(custom_domain_pattern, tenant_id):
            return True
        
        return False
    
    def get_redirect_uri(self):
        """Public method to get the redirect URI for OAuth flows (always uses localhost for Azure compatibility)"""
        return self._get_redirect_uri()
    
    def _get_redirect_uri(self):
        """Get the redirect URI from settings or use default"""
        try:
            settings = self._get_oauth_settings()
            
            # Check if redirect URI is configured in settings
            if settings and settings.get('oauth_redirect_uri'):
                return settings['oauth_redirect_uri'].strip()
            
            # Fallback to default
            from flask import request
            if request:
                # Ensure we use localhost for Azure compatibility
                base_url = request.url_root.rstrip('/')
                if '127.0.0.1' in base_url:
                    base_url = base_url.replace('127.0.0.1', 'localhost')
                return base_url + '/oauth/microsoft/callback'
            else:
                return "http://localhost:5000/oauth/microsoft/callback"
        except Exception as e:
            logger.error(f"Error getting redirect URI from settings: {e}")
            # Fallback to default
            return "http://localhost:5000/oauth/microsoft/callback"
    
    def get_tenant_guidance(self, tenant_id):
        """Get guidance for common tenant ID issues"""
        tenant_id = tenant_id.strip() if tenant_id else ""
        
        guidance = []
        
        if not tenant_id:
            guidance.append("• Tenant ID is required")
        elif len(tenant_id) < 36:
            guidance.append("• Tenant ID appears too short for a GUID")
        elif len(tenant_id) > 100:
            guidance.append("• Tenant ID appears too long")
        elif " " in tenant_id:
            guidance.append("• Tenant ID contains spaces - remove all spaces")
        elif not self._validate_tenant_id(tenant_id):
            guidance.append("• Tenant ID format is invalid")
            guidance.append("• Expected formats:")
            guidance.append("  - GUID: 12345678-1234-1234-1234-123456789012")
            guidance.append("  - Domain: yourdomain.onmicrosoft.com")
            guidance.append("  - Special: common, organizations, consumers")
        
        if guidance:
            guidance.insert(0, "Tenant ID Issues:")
            
        return "\n".join(guidance) if guidance else "Tenant ID format appears correct"
