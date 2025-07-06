"""
API blueprint for Power BI and external integrations - Cursor-based pagination only
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from ..models.database import get_db_connection
from ..utils.auth import require_api_key

api_bp = Blueprint('api', __name__)


@api_bp.route('/powerbi/timesheet_data', methods=['GET'])
@require_api_key
def powerbi_timesheet_data():
    """API endpoint for Power BI to get all timesheet data with cursor-based pagination"""
    
    # Get optional query parameters for filtering
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id')
    project_id = request.args.get('project_id')
    
    # Get pagination parameters
    size = int(request.args.get('size', 2500))
    next_page_token = request.args.get('nextPageToken', '')
    
    # Validate size parameter
    if size < 1 or size > 5000:  # Max 5000 records per request
        size = 2500
    
    # Decode next_page_token to get offset (base64 encoded offset for security)
    try:
        if next_page_token:
            import base64
            offset = int(base64.b64decode(next_page_token.encode()).decode())
        else:
            offset = 0
    except:
        offset = 0
    
    conn = get_db_connection()
    
    try:
        # Build dynamic query based on filters
        query = '''
            SELECT 
                t.id,
                t.user_id,
                u.email as user_email,
                t.date,
                t.project_id,
                t.project_name,
                t.total_minutes,
                ROUND(t.total_minutes / 60.0, 2) as total_hours,
                t.last_updated,
                u.is_admin
            FROM timesheet t
            JOIN users u ON t.user_id = u.id
            WHERE 1=1
        '''
        
        params = []
        
        # Add filters if provided
        if start_date:
            query += ' AND t.date >= ?'
            params.append(start_date)
            
        if end_date:
            query += ' AND t.date <= ?'
            params.append(end_date)
            
        if user_id:
            query += ' AND t.user_id = ?'
            params.append(user_id)
            
        if project_id:
            query += ' AND t.project_id = ?'
            params.append(project_id)
        
        # Order by id for consistent pagination
        query += ' ORDER BY t.id LIMIT ? OFFSET ?'
        params.extend([size + 1, offset])  # Get one extra to check if there are more
        
        rows = conn.execute(query, params).fetchall()
        
        # Check if there are more records
        has_more = len(rows) > size
        if has_more:
            rows = rows[:-1]  # Remove the extra record
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            data.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'user_email': row['user_email'],
                'date': row['date'],
                'project_id': row['project_id'],
                'project_name': row['project_name'],
                'total_minutes': row['total_minutes'],
                'total_hours': row['total_hours'],
                'last_updated': row['last_updated'],
                'is_admin_user': bool(row['is_admin'])
            })
        
        # Generate next page token if there are more records
        import base64
        next_token = None
        if has_more:
            next_offset = offset + size
            next_token = base64.b64encode(str(next_offset).encode()).decode()
        
        # Build response in the format Power BI expects
        response = {
            'data': data,
            'metadata': {
                'nextPageToken': next_token,
                'size': len(data),
                'offset': offset,
                'hasMore': has_more,
                'filters_applied': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'user_id': user_id,
                    'project_id': project_id
                },
                'generated_at': datetime.now().isoformat(),
                'api_version': '2.0'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Power BI API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        conn.close()


@api_bp.route('/powerbi/users', methods=['GET'])
@require_api_key
def powerbi_users_data():
    """API endpoint for Power BI users with cursor-based pagination"""
    
    size = int(request.args.get('size', 2500))
    next_page_token = request.args.get('nextPageToken', '')
    
    if size < 1 or size > 5000:
        size = 2500
    
    # Decode offset from token
    try:
        if next_page_token:
            import base64
            offset = int(base64.b64decode(next_page_token.encode()).decode())
        else:
            offset = 0
    except:
        offset = 0
    
    conn = get_db_connection()
    
    try:
        # Get users with one extra to check for more
        rows = conn.execute('''
            SELECT 
                id,
                email,
                is_admin,
                created_at,
                (SELECT COUNT(*) FROM timesheet WHERE user_id = users.id) as total_entries,
                (SELECT SUM(total_minutes) FROM timesheet WHERE user_id = users.id) as total_minutes,
                (SELECT ROUND(SUM(total_minutes) / 60.0, 2) FROM timesheet WHERE user_id = users.id) as total_hours
            FROM users
            ORDER BY id
            LIMIT ? OFFSET ?
        ''', (size + 1, offset)).fetchall()
        
        # Check if there are more records
        has_more = len(rows) > size
        if has_more:
            rows = rows[:-1]
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            data.append({
                'id': row['id'],
                'email': row['email'],
                'is_admin': bool(row['is_admin']),
                'created_at': row['created_at'],
                'total_entries': row['total_entries'] or 0,
                'total_minutes': row['total_minutes'] or 0,
                'total_hours': row['total_hours'] or 0
            })
        
        # Generate next page token
        import base64
        next_token = None
        if has_more:
            next_offset = offset + size
            next_token = base64.b64encode(str(next_offset).encode()).decode()
        
        response = {
            'data': data,
            'metadata': {
                'nextPageToken': next_token,
                'size': len(data),
                'offset': offset,
                'hasMore': has_more,
                'generated_at': datetime.now().isoformat(),
                'api_version': '2.0'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Power BI Users API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        conn.close()


@api_bp.route('/powerbi/projects', methods=['GET'])
@require_api_key
def powerbi_projects_data():
    """API endpoint for Power BI projects with cursor-based pagination"""
    
    size = int(request.args.get('size', 2500))
    next_page_token = request.args.get('nextPageToken', '')
    
    if size < 1 or size > 5000:
        size = 2500
    
    # Decode offset from token
    try:
        if next_page_token:
            import base64
            offset = int(base64.b64decode(next_page_token.encode()).decode())
        else:
            offset = 0
    except:
        offset = 0
    
    conn = get_db_connection()
    
    try:
        # Get projects with aggregated data
        rows = conn.execute('''
            SELECT 
                project_id,
                project_name,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(*) as total_entries,
                SUM(total_minutes) as total_minutes,
                ROUND(SUM(total_minutes) / 60.0, 2) as total_hours,
                MIN(date) as first_entry_date,
                MAX(date) as last_entry_date,
                AVG(total_minutes) as avg_minutes_per_entry
            FROM timesheet
            GROUP BY project_id, project_name
            ORDER BY total_minutes DESC
            LIMIT ? OFFSET ?
        ''', (size + 1, offset)).fetchall()
        
        # Check if there are more records
        has_more = len(rows) > size
        if has_more:
            rows = rows[:-1]
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            data.append({
                'project_id': row['project_id'],
                'project_name': row['project_name'],
                'unique_users': row['unique_users'],
                'total_entries': row['total_entries'],
                'total_minutes': row['total_minutes'],
                'total_hours': row['total_hours'],
                'first_entry_date': row['first_entry_date'],
                'last_entry_date': row['last_entry_date'],
                'avg_minutes_per_entry': round(row['avg_minutes_per_entry'], 2) if row['avg_minutes_per_entry'] else 0
            })
        
        # Generate next page token
        import base64
        next_token = None
        if has_more:
            next_offset = offset + size
            next_token = base64.b64encode(str(next_offset).encode()).decode()
        
        response = {
            'data': data,
            'metadata': {
                'nextPageToken': next_token,
                'size': len(data),
                'offset': offset,
                'hasMore': has_more,
                'generated_at': datetime.now().isoformat(),
                'api_version': '2.0'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Power BI Projects API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        conn.close()


@api_bp.route('/powerbi/summary', methods=['GET'])
@require_api_key
def powerbi_summary_data():
    """API endpoint for Power BI to get overall summary statistics"""
    
    conn = get_db_connection()
    
    try:
        # Get overall statistics
        summary = conn.execute('''
            SELECT 
                COUNT(*) as total_entries,
                COUNT(DISTINCT user_id) as total_users,
                COUNT(DISTINCT project_id) as total_projects,
                SUM(total_minutes) as total_minutes,
                ROUND(SUM(total_minutes) / 60.0, 2) as total_hours,
                MIN(date) as earliest_entry,
                MAX(date) as latest_entry,
                AVG(total_minutes) as avg_minutes_per_entry
            FROM timesheet
        ''').fetchone()
        
        # Get recent activity (last 30 days)
        recent_activity = conn.execute('''
            SELECT 
                date,
                COUNT(*) as entries_count,
                SUM(total_minutes) as daily_minutes,
                ROUND(SUM(total_minutes) / 60.0, 2) as daily_hours
            FROM timesheet
            WHERE date >= date('now', '-30 days')
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        ''').fetchall()
        
        recent_data = []
        for row in recent_activity:
            recent_data.append({
                'date': row['date'],
                'entries_count': row['entries_count'],
                'daily_minutes': row['daily_minutes'],
                'daily_hours': row['daily_hours']
            })
        
        response = {
            'summary': {
                'total_entries': summary['total_entries'],
                'total_users': summary['total_users'],
                'total_projects': summary['total_projects'],
                'total_minutes': summary['total_minutes'],
                'total_hours': summary['total_hours'],
                'earliest_entry': summary['earliest_entry'],
                'latest_entry': summary['latest_entry'],
                'avg_minutes_per_entry': round(summary['avg_minutes_per_entry'], 2) if summary['avg_minutes_per_entry'] else 0
            },
            'recent_activity': recent_data,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'api_version': '2.0'
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Power BI Summary API error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        conn.close()


@api_bp.route('/powerbi/info', methods=['GET'])
@require_api_key
def powerbi_api_info():
    """API endpoint to get information about available endpoints and pagination"""
    
    return jsonify({
        'api_version': '2.0',
        'pagination_type': 'cursor_based',
        'description': 'All endpoints use cursor-based pagination with nextPageToken',
        'parameters': {
            'size': {
                'description': 'Number of records per request',
                'default': 2500,
                'maximum': 5000,
                'type': 'integer'
            },
            'nextPageToken': {
                'description': 'Token for next page (from previous response metadata)',
                'type': 'string',
                'note': 'Omit for first page, use value from previous response for subsequent pages'
            }
        },
        'endpoints': {
            '/api/powerbi/timesheet_data': {
                'description': 'Get timesheet entries with filtering and cursor pagination',
                'filters': {
                    'start_date': 'Filter by start date (YYYY-MM-DD)',
                    'end_date': 'Filter by end date (YYYY-MM-DD)',
                    'user_id': 'Filter by specific user ID',
                    'project_id': 'Filter by specific project ID'
                }
            },
            '/api/powerbi/users': {
                'description': 'Get user data with aggregated timesheet statistics'
            },
            '/api/powerbi/projects': {
                'description': 'Get project summary data with aggregated statistics'
            },
            '/api/powerbi/summary': {
                'description': 'Get overall statistics and recent activity (no pagination)'
            },
            '/api/powerbi/info': {
                'description': 'Get API documentation and endpoint information'
            }
        },
        'powerbi_m_code': {
            'description': 'Power BI M code for cursor-based pagination',
            'example': '''let
    Source = (endpoint as text, token as text, optional filters as record) =>
let
    baseUrl = "http://127.0.0.1:5000/api/powerbi/",
    headers = [#"Content-Type"="application/json", Authorization="Bearer " & token],
    
    // Build filter parameters
    filterParams = if filters = null then "" else 
        List.Accumulate(
            Record.FieldNames(filters),
            "",
            (state, current) => state & "&" & current & "=" & Text.From(Record.Field(filters, current))
        ),
    
    // Initial request
    initUrl = baseUrl & endpoint & "?size=2500&nextPageToken=" & filterParams,
    initReq = Json.Document(Web.Contents(initUrl, [Headers=headers])),
    initData = initReq[data],
    
    // Recursive function to gather all pages
    gather = (data as list, req) =>
    let
        newtoken = req[metadata][nextPageToken],
        nextUrl = baseUrl & endpoint & "?size=2500&nextPageToken=" & newtoken & filterParams,
        newReq = Json.Document(Web.Contents(nextUrl, [Headers=headers])),
        newdata = newReq[data],
        combinedData = List.Combine({data, newdata}),
        check = if newReq[metadata][nextPageToken] = null then combinedData else @gather(combinedData, newReq)
    in
        check,
    
    outputList = if initReq[metadata][nextPageToken] = null then initData else gather(initData, initReq),
    expand = Table.FromRecords(outputList)
in
    expand
in
    Source'''
        },
        'response_format': {
            'structure': {
                'data': 'Array of records',
                'metadata': {
                    'nextPageToken': 'Token for next page (null if last page)',
                    'size': 'Number of records in current response',
                    'offset': 'Current offset in dataset',
                    'hasMore': 'Boolean indicating if more pages exist',
                    'generated_at': 'ISO timestamp of response generation',
                    'api_version': 'API version number'
                }
            }
        },
        'examples': {
            'timesheet_basic': '/api/powerbi/timesheet_data?size=1000',
            'timesheet_filtered': '/api/powerbi/timesheet_data?start_date=2025-01-01&end_date=2025-12-31&size=2500',
            'timesheet_next_page': '/api/powerbi/timesheet_data?size=2500&nextPageToken=Mg==',
            'users': '/api/powerbi/users?size=500',
            'projects': '/api/powerbi/projects?size=100'
        },
        'generated_at': datetime.now().isoformat()
    })
