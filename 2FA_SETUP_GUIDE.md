# Two-Factor Authentication (2FA) Setup Guide

This timesheet application now supports Two-Factor Authentication (2FA) using Time-based One-Time Password (TOTP) for enhanced security.

## Features

- **TOTP Support**: Compatible with popular authenticator apps like Google Authenticator, Authy, Microsoft Authenticator, etc.
- **Backup Codes**: 8 single-use backup codes for account recovery
- **Non-OAuth Users Only**: 2FA is only available for users with password-based authentication (not Microsoft OAuth users)
- **User-Controlled**: Each user can enable/disable 2FA for their own account

## How to Enable 2FA

1. **Login to your account** with your username and password
2. **Access 2FA Settings**: 
   - Click on your "Account" dropdown in the top-right corner
   - Select "Two-Factor Authentication"
3. **Setup Process**:
   - Click "Enable Two-Factor Authentication"
   - Scan the QR code with your authenticator app
   - Enter the 6-digit code from your app to verify setup
4. **Save Backup Codes**: You'll receive 8 backup codes - save these securely!

## Database Changes

The following fields have been added to the `users` table:
- `totp_secret`: Stores the user's TOTP secret (encrypted)
- `totp_enabled`: Boolean flag indicating if 2FA is enabled
- `backup_codes`: JSON array of backup codes for account recovery

## Login Process with 2FA

When 2FA is enabled:
1. Enter your email and password as usual
2. You'll be redirected to a 2FA verification page
3. Enter the 6-digit code from your authenticator app
4. If you can't access your app, use a backup code instead

## Managing 2FA

Users can manage their 2FA settings through the account menu:
- **View Status**: See if 2FA is enabled/disabled
- **Backup Codes**: Check how many backup codes remain
- **Regenerate Codes**: Generate new backup codes (requires password)
- **Disable 2FA**: Turn off 2FA completely (requires password)

## Security Considerations

- Each backup code can only be used once
- TOTP tokens are valid for 30 seconds with a 1-period window (±30 seconds)
- Disabling 2FA removes all backup codes
- Password is required to disable 2FA or regenerate backup codes
- 2FA settings are per-user and don't affect OAuth users

## Technical Implementation

- **Library**: Uses `pyotp` for TOTP generation/verification
- **QR Codes**: Generated using `qrcode` library
- **Storage**: Secrets stored securely in the database
- **Session Management**: Temporary session data for 2FA verification flow

## Troubleshooting

### Can't scan QR code?
- Use the manual entry code provided below the QR code
- Make sure your authenticator app supports TOTP

### Lost authenticator device?
- Use one of your backup codes to login
- Immediately regenerate new backup codes after logging in
- Consider setting up 2FA on a new device

### Backup codes running low?
- Regenerate backup codes from the 2FA management page
- Old codes will be invalidated when new ones are generated

### Time sync issues?
- Ensure your device's time is synchronized
- TOTP codes are time-based and require accurate time

## Compatible Authenticator Apps

- Google Authenticator (iOS/Android)
- Authy (iOS/Android/Desktop)
- Microsoft Authenticator (iOS/Android)
- 1Password (with TOTP support)
- LastPass Authenticator
- Any RFC 6238 compliant TOTP app

## Admin Notes

- Admins cannot force enable/disable 2FA for other users
- 2FA status is visible in the user interface with badges
- No special admin controls are needed - users self-manage their 2FA
- OAuth users automatically have password authentication disabled and cannot use 2FA
