# Unified Endpoints - Recordings, Transcriptions, Notes

## Overview
All recordings, transcriptions, and notes are now accessible to **all roles** (Admin, Teacher, Student) through unified endpoints.

## Authorization Logic

### Admin
- **Can see ALL data** from all users
- Includes user information with each record
- Full access to all recordings, transcriptions, and notes

### Teacher & Student
- **Can see only their own data**
- Filtered by `user_id`
- No access to other users' data

## Unified Endpoints

### 1. Recordings
```
GET /api/recordings
```
- **Admin**: Returns all recordings with user info
- **Teacher/Student**: Returns only their own recordings

### 2. Transcriptions
```
GET /api/transcriptions
```
- **Admin**: Returns all transcriptions with user and broadcast info
- **Teacher/Student**: Returns only their own transcriptions

### 3. Notes
```
GET /api/notes
```
- **Admin**: Returns all notes with user, broadcast, and transcription info
- **Teacher/Student**: Returns only their own notes

## Backward Compatibility

All role-specific endpoints still work and now use the unified endpoints internally:

### Teacher Endpoints
- `/api/teacher/recordings` → Uses `/api/recordings`
- `/api/teacher/transcriptions` → Uses `/api/transcriptions`
- `/api/teacher/notes` → Uses `/api/notes`

### Student Endpoints
- `/api/student/recordings` → Uses `/api/recordings`
- `/api/student/transcriptions` → Uses `/api/transcriptions`
- `/api/student/notes` → Uses `/api/notes`

### Admin Endpoints
- `/api/admin/recordings` → Uses `/api/recordings`
- `/api/admin/transcriptions` → Uses `/api/transcriptions`
- `/api/admin/notes` → Uses `/api/notes` (new)

## Frontend API Methods

### Unified Methods (Recommended)
```javascript
// Works for all roles
api.getRecordings()
api.getTranscriptions()
api.getNotes()
```

### Role-Specific Methods (Backward Compatible)
```javascript
// Teacher
api.getTeacherRecordings()  // → calls getRecordings()
api.getTeacherTranscriptions()  // → calls getTranscriptions()
api.getTeacherNotes()  // → calls getNotes()

// Student
api.getStudentRecordings()  // → calls getRecordings()
api.getStudentTranscriptions()  // → calls getTranscriptions()
api.getStudentNotes()  // → calls getNotes()
```

## Authentication

All endpoints:
1. Try to get `user_id` from Flask session
2. Fallback to `X-User-Id` header (from localStorage)
3. Fallback to `user_id` query parameter
4. Verify user exists and restore session if needed

## Response Format

### Admin Response (with user info)
```json
[
  {
    "id": 1,
    "user_id": 3,
    "title": "Lecture Recording",
    "file_path": "...",
    "user": {
      "id": 3,
      "username": "teacher1",
      "email": "teacher@example.com",
      "role": "teacher"
    }
  }
]
```

### Teacher/Student Response (own data only)
```json
[
  {
    "id": 1,
    "user_id": 3,
    "title": "Lecture Recording",
    "file_path": "..."
  }
]
```

## Benefits

1. **Single Source of Truth**: One endpoint per resource type
2. **Role-Based Access**: Automatic filtering based on user role
3. **Backward Compatible**: Old endpoints still work
4. **Consistent API**: Same structure for all roles
5. **Easy to Use**: Frontend can use same methods for all roles

## Files Modified

1. **backend/app.py**:
   - Added `get_authenticated_user()` helper function
   - Created unified endpoints: `/api/recordings`, `/api/transcriptions`, `/api/notes`
   - Updated all role-specific endpoints to use unified endpoints

2. **static/js/api.js**:
   - Added unified methods: `getRecordings()`, `getTranscriptions()`, `getNotes()`
   - Updated role-specific methods to call unified methods
   - All methods send `user_id` and `user_role` in headers

## Testing

Test with different roles:
1. **Admin**: Should see all data from all users
2. **Teacher**: Should see only their own recordings/transcriptions/notes
3. **Student**: Should see only their own recordings/transcriptions/notes

All endpoints work with:
- Flask session cookies
- `X-User-Id` header (from localStorage)
- `user_id` query parameter


