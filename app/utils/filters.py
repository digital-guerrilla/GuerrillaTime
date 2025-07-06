"""
Template filters for Timesheet Tracker
"""

from datetime import datetime, timedelta


def dateadd_filter(date_str, days):
    """Add days to a date string"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        new_date = date_obj + timedelta(days=days)
        return new_date.strftime('%Y-%m-%d')
    except:
        return date_str


def register_filters(app):
    """Register template filters with Flask app"""
    app.template_filter('dateadd')(dateadd_filter)
