# API Usage Examples with Bearer Token Authentication

## Basic Authentication
All API endpoints require a Bearer token in the Authorization header:

```bash
Authorization: Bearer timesheet-api-key-2025
```

## Curl Examples

### 1. Get API Information
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     http://127.0.0.1:5000/api/powerbi/info
```

### 2. Get Timesheet Data (with pagination)
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     "http://127.0.0.1:5000/api/powerbi/timesheet_data?page=1&per_page=10"
```

### 3. Get Timesheet Data (with filters and pagination)
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     "http://127.0.0.1:5000/api/powerbi/timesheet_data?start_date=2025-01-01&end_date=2025-12-31&page=1&per_page=50"
```

### 4. Get Users Data
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     "http://127.0.0.1:5000/api/powerbi/users?page=1&per_page=20"
```

### 5. Get Projects Data
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     "http://127.0.0.1:5000/api/powerbi/projects?page=1&per_page=25"
```

### 6. Get Summary Data
```bash
curl -H "Authorization: Bearer timesheet-api-key-2025" \
     "http://127.0.0.1:5000/api/powerbi/summary?activity_days=30&activity_page=1&activity_per_page=10"
```

## Power BI Setup

1. **Open Power BI Desktop** → Get Data → Web
2. **URL**: `http://127.0.0.1:5000/api/powerbi/timesheet_data`
3. **Authentication**: Choose "Anonymous"
4. **Advanced Options** → Add Header:
   - **Name**: `Authorization`
   - **Value**: `Bearer timesheet-api-key-2025`

## Environment Configuration

Set the API key using environment variable:
```bash
export API_KEY=your-secure-api-key-here
```

Or in Windows:
```cmd
set API_KEY=your-secure-api-key-here
```

## Response Format

All endpoints return JSON with this structure:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 100,
    "total_records": 250,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  },
  "metadata": {
    "records_on_page": 100,
    "generated_at": "2025-07-05T17:45:00",
    "api_version": "1.0"
  }
}
```
