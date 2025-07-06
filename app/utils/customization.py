#!/usr/bin/env python3
"""
Helper function to inject customization CSS variables into templates
"""

def get_customization_css_variables(settings_service):
    """Get CSS variables from customization settings"""
    
    # Get customization settings
    try:
        # Try to get settings from the service
        if hasattr(settings_service, 'get_customization_settings'):
            customization = settings_service.get_customization_settings()
        else:
            # Fallback to getting settings by category
            customization_settings = settings_service.get_settings_by_category('customization')
            customization = {}
            for setting in customization_settings:
                key = setting['setting_key']
                value = setting['setting_value']
                # Remove 'custom_' prefix for cleaner access
                attr_name = key.replace('custom_', '') if key.startswith('custom_') else key
                customization[attr_name] = value
                customization[key] = value
    except:
        # If anything fails, use defaults
        customization = {}
    
    # Map customization settings to CSS variables
    css_variables = {
        # Background colors - rationalized palette
        '--primary-color': getattr(customization, 'custom_background_primary', None) or customization.get('background_primary', '#2c3e50'),
        '--secondary-color': getattr(customization, 'custom_background_secondary', None) or customization.get('background_secondary', '#34495e'),
        '--light-gray': getattr(customization, 'custom_background_light', None) or customization.get('background_light', '#f8f9fa'),
        '--white': getattr(customization, 'custom_background_white', None) or customization.get('background_white', '#ffffff'),
        
        # Header colors - rationalized palette
        '--header-primary': getattr(customization, 'custom_header_primary', None) or customization.get('header_primary', '#2c3e50'),
        '--header-secondary': getattr(customization, 'custom_header_secondary', None) or customization.get('header_secondary', '#3498db'),
        '--header-text': getattr(customization, 'custom_header_text', None) or customization.get('header_text', '#ffffff'),
        
        # Button colors - rationalized palette
        '--button-primary': getattr(customization, 'custom_button_primary', None) or customization.get('button_primary', '#3498db'),
        '--button-secondary': getattr(customization, 'custom_button_secondary', None) or customization.get('button_secondary', '#6c757d'),
        '--success-color': getattr(customization, 'custom_button_success', None) or customization.get('button_success', '#27ae60'),
        '--warning-color': getattr(customization, 'custom_button_warning', None) or customization.get('button_warning', '#f39c12'),
        '--danger-color': getattr(customization, 'custom_button_danger', None) or customization.get('button_danger', '#e74c3c'),
        
        # Text colors - rationalized palette
        '--text-primary': getattr(customization, 'custom_text_primary', None) or customization.get('text_primary', '#2c3e50'),
        '--text-secondary': getattr(customization, 'custom_text_secondary', None) or customization.get('text_secondary', '#7f8c8d'),
        '--text-muted': getattr(customization, 'custom_text_muted', None) or customization.get('text_muted', '#95a5a6'),
        '--text-light': getattr(customization, 'custom_text_light', None) or customization.get('text_light', '#ffffff'),
        
        # Accent and interactive colors - rationalized palette
        '--accent-color': getattr(customization, 'custom_accent_color', None) or customization.get('accent_color', '#3498db'),
        '--accent-hover': getattr(customization, 'custom_accent_color', None) or customization.get('accent_color', '#2980b9'),
        '--accent-light': getattr(customization, 'custom_accent_color', None) or customization.get('accent_color', '#5dade2'),
        '--accent-border': getattr(customization, 'custom_accent_color', None) or customization.get('accent_color', '#3498db'),
        '--info-color': getattr(customization, 'custom_accent_color', None) or customization.get('accent_color', '#3498db'),
        
        # Form and input colors - rationalized palette
        '--input-background': getattr(customization, 'custom_input_background', None) or customization.get('input_background', '#ffffff'),
        '--input-border': getattr(customization, 'custom_input_border', None) or customization.get('input_border', '#dee2e6'),
        '--input-focus': getattr(customization, 'custom_input_focus', None) or customization.get('input_focus', '#3498db'),
        
        # Card and container colors - rationalized palette
        '--card-background': getattr(customization, 'custom_card_background', None) or customization.get('card_background', '#ffffff'),
        '--card-border': getattr(customization, 'custom_card_border', None) or customization.get('card_border', '#e9ecef'),
        '--card-shadow': getattr(customization, 'custom_card_shadow', None) or customization.get('card_shadow', 'rgba(44, 62, 80, 0.1)'),
        
        # Border colors - rationalized palette
        '--border-light': getattr(customization, 'custom_border_light', None) or customization.get('border_light', '#e9ecef'),
        '--border-medium': getattr(customization, 'custom_border_medium', None) or customization.get('border_medium', '#dee2e6'),
        '--border-dark': getattr(customization, 'custom_border_dark', None) or customization.get('border_dark', '#adb5bd'),
        
        # Navigation colors - rationalized palette
        '--nav-background': getattr(customization, 'custom_nav_background', None) or customization.get('nav_background', '#f8f9fa'),
        '--nav-text': getattr(customization, 'custom_nav_text', None) or customization.get('nav_text', '#2c3e50'),
        '--nav-hover': getattr(customization, 'custom_nav_hover', None) or customization.get('nav_hover', '#e9ecef'),
        '--nav-active': getattr(customization, 'custom_nav_active', None) or customization.get('nav_active', '#3498db'),
        
        # Status colors - rationalized palette
        '--status-active': getattr(customization, 'custom_status_active', None) or customization.get('status_active', '#27ae60'),
        '--status-inactive': getattr(customization, 'custom_status_inactive', None) or customization.get('status_inactive', '#95a5a6'),
        '--status-pending': getattr(customization, 'custom_status_pending', None) or customization.get('status_pending', '#f39c12'),
        '--status-error': getattr(customization, 'custom_status_error', None) or customization.get('status_error', '#e74c3c'),
        
        # Font settings
        '--font-family': getattr(customization, 'custom_font_family', None) or customization.get('font_family', 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'),
        '--font-size-base': getattr(customization, 'custom_font_size_base', None) or customization.get('font_size_base', '14px'),
        '--font-size-small': getattr(customization, 'custom_font_size_small', None) or customization.get('font_size_small', '12px'),
        '--font-size-large': getattr(customization, 'custom_font_size_large', None) or customization.get('font_size_large', '16px'),
        '--font-size-xlarge': getattr(customization, 'custom_font_size_xlarge', None) or customization.get('font_size_xlarge', '18px'),
        '--font-size-h1': getattr(customization, 'custom_font_size_h1', None) or customization.get('font_size_h1', '2.5em'),
        '--font-size-h2': getattr(customization, 'custom_font_size_h2', None) or customization.get('font_size_h2', '2em'),
        '--font-size-h3': getattr(customization, 'custom_font_size_h3', None) or customization.get('font_size_h3', '1.5em'),
        '--font-weight-normal': getattr(customization, 'custom_font_weight_normal', None) or customization.get('font_weight_normal', '400'),
        '--font-weight-medium': getattr(customization, 'custom_font_weight_medium', None) or customization.get('font_weight_medium', '500'),
        '--font-weight-bold': getattr(customization, 'custom_font_weight_bold', None) or customization.get('font_weight_bold', '600'),
        '--font-weight-extra-bold': getattr(customization, 'custom_font_weight_extra_bold', None) or customization.get('font_weight_extra_bold', '700'),
    }
    
    return css_variables


def generate_custom_css(settings_service):
    """Generate custom CSS with all customization variables"""
    css_vars = get_customization_css_variables(settings_service)
    
    css = ":root {\n"
    for var_name, value in css_vars.items():
        css += f"    {var_name}: {value};\n"
    css += "}\n"
    
    # Add body font-family override
    font_family = css_vars.get('--font-family', 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif')
    css += f"\nbody {{ font-family: {font_family}; }}\n"
    
    # Add responsive font sizes
    css += """
/* Responsive font scaling */
@media (max-width: 768px) {
    :root {
        --font-size-h1: 2em;
        --font-size-h2: 1.5em;
        --font-size-h3: 1.25em;
        --font-size-base: 13px;
    }
}

@media (max-width: 480px) {
    :root {
        --font-size-h1: 1.75em;
        --font-size-h2: 1.25em;
        --font-size-h3: 1.1em;
        --font-size-base: 12px;
    }
}
"""
    
    return css
