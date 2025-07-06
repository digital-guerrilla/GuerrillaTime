# Microsoft OAuth Troubleshooting Guide

## Current Configuration Summary
- **Tenant ID**: ed070760-986f-487a-a260-4aa8ba12d0cb
- **Client ID**: 808022f6-eed8-448b-b308-13de19ae121d
- **Redirect URI**: http://localhost:5000/oauth/microsoft/callback
- **Error**: AADSTS9002313: Invalid request. Request is malformed or invalid.

## Root Cause
The error AADSTS9002313 indicates a configuration mismatch between your application and Azure App Registration.

## Step-by-Step Fix

### 1. Verify Azure App Registration Settings

Go to **Azure Portal > Microsoft Entra ID > App registrations > [Your App]**

#### Check Authentication Settings:
1. Click on **"Authentication"** in the left sidebar
2. Under **"Redirect URIs"**, verify you have:
   ```
   Platform: Web
   Redirect URI: http://localhost:5000/oauth/microsoft/callback
   ```
3. If this URI is missing, click **"Add a platform"** → **"Web"** → Add the URI above

#### Check Application Overview:
1. Click on **"Overview"** in the left sidebar
2. Verify these match your settings:
   - **Application (client) ID**: 808022f6-eed8-448b-b308-13de19ae121d
   - **Directory (tenant) ID**: ed070760-986f-487a-a260-4aa8ba12d0cb

#### Check Client Secret:
1. Click on **"Certificates & secrets"** in the left sidebar
2. Under **"Client secrets"**, verify you have an active secret
3. If expired or missing, create a new one and update your settings

### 2. Common Solutions

#### Option A: Fix Redirect URI
The most common cause is redirect URI mismatch. Ensure EXACTLY this URI is configured:
```
http://localhost:5000/oauth/microsoft/callback
```

**Common mistakes:**
- Using `https://` instead of `http://`
- Using `127.0.0.1` instead of `localhost`
- Missing trailing path `/callback`
- Wrong port number

#### Option B: Use Multi-Tenant Configuration
If you want to support broader authentication, try changing the tenant ID to:
- `common` - for both personal and work accounts
- `organizations` - for work/school accounts only

#### Option C: Verify Client Secret
1. Generate a new client secret in Azure Portal
2. Update your system settings with the new secret
3. Test again

### 3. Test Configuration

Run this command to test your current configuration:
```bash
python debug_oauth.py
```

### 4. Alternative Debugging Steps

1. **Check for exact URI match**: The redirect URI must match EXACTLY (case-sensitive)
2. **Verify tenant exists**: Make sure the tenant ID is correct
3. **Check application permissions**: Ensure "User.Read" permission is granted
4. **Test with different tenant**: Try "common" if your current tenant has issues

## Next Steps

1. **First**: Verify the redirect URI in Azure Portal matches exactly: `http://localhost:5000/oauth/microsoft/callback`
2. **Second**: If still failing, try changing tenant ID to "common" in your system settings
3. **Third**: Generate a new client secret and update your configuration

## Need Help?

If the issue persists after these steps:
1. Check the Azure Portal audit logs for more details
2. Verify your Azure subscription and permissions
3. Consider creating a new App Registration with fresh credentials
