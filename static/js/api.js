// API Client for Lecture Flow
const API_BASE_URL = 'http://127.0.0.1:5000/api';
const WS_URL = 'http://127.0.0.1:5000';

class LectureFlowAPI {
    constructor() {
        this.socket = null;
        this.currentBroadcastId = null;
    }

    // Authentication
    async login(email, password) {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            mode: 'cors',
            body: JSON.stringify({ email, password })
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    async logout() {
        const response = await fetch(`${API_BASE_URL}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        return response.json();
    }

    async signup(userData) {
        const response = await fetch(`${API_BASE_URL}/signup`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            mode: 'cors',
            body: JSON.stringify(userData)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    // Admin - Teachers
    async getTeachers() {
        const response = await fetch(`${API_BASE_URL}/admin/teachers`, {
            credentials: 'include'
        });
        return response.json();
    }

    async registerTeacher(teacherData) {
        const response = await fetch(`${API_BASE_URL}/admin/teachers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(teacherData)
        });
        return response.json();
    }

    async updateTeacher(teacherId, teacherData) {
        const response = await fetch(`${API_BASE_URL}/admin/teachers/${teacherId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(teacherData)
        });
        return response.json();
    }

    async deleteTeacher(teacherId) {
        const response = await fetch(`${API_BASE_URL}/admin/teachers/${teacherId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return response.json();
    }

    // Admin - Students
    async getStudents() {
        const response = await fetch(`${API_BASE_URL}/admin/students`, {
            credentials: 'include'
        });
        return response.json();
    }

    async registerStudent(studentData) {
        const response = await fetch(`${API_BASE_URL}/admin/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(studentData)
        });
        return response.json();
    }

    async updateStudent(studentId, studentData) {
        const response = await fetch(`${API_BASE_URL}/admin/students/${studentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(studentData)
        });
        return response.json();
    }

    async deleteStudent(studentId) {
        const response = await fetch(`${API_BASE_URL}/admin/students/${studentId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return response.json();
    }

    // Admin - Recordings
    async getAllRecordings() {
        const response = await fetch(`${API_BASE_URL}/admin/recordings`, {
            credentials: 'include'
        });
        return response.json();
    }

    // Admin - Transcriptions
    async getAllTranscriptions() {
        const response = await fetch(`${API_BASE_URL}/admin/transcriptions`, {
            credentials: 'include'
        });
        return response.json();
    }

    // Admin - Broadcasts
    async getAllBroadcasts() {
        const response = await fetch(`${API_BASE_URL}/admin/broadcasts`, {
            credentials: 'include'
        });
        return response.json();
    }

    // Teacher - Broadcasts
    async startBroadcast(broadcastData) {
        const response = await fetch(`${API_BASE_URL}/teacher/broadcasts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(broadcastData)
        });
        return response.json();
    }

    async endBroadcast(broadcastId, audioFilePath = null) {
        const response = await fetch(`${API_BASE_URL}/teacher/broadcasts/${broadcastId}/end`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ audio_file_path: audioFilePath })
        });
        return response.json();
    }

    // Teacher-specific methods (backward compatibility - now use unified endpoints)
    async getTeacherRecordings() {
        return this.getRecordings();
    }

    // Helper method to get user ID from localStorage or sessionStorage
    getUserId() {
        return localStorage.getItem('userId') || sessionStorage.getItem('userId');
    }

    // Helper method to get user role from localStorage or sessionStorage
    getUserRole() {
        return localStorage.getItem('userRole') || sessionStorage.getItem('userRole');
    }

    // Unified endpoints - work for all roles (admin, teacher, student)
    async getRecordings() {
        // Get user_id from localStorage (preferred) or sessionStorage (fallback)
        const userId = this.getUserId();
        const url = userId ? 
            `${API_BASE_URL}/recordings?user_id=${userId}` : 
            `${API_BASE_URL}/recordings`;
        
        const response = await fetch(url, {
            credentials: 'include',
            headers: userId ? { 
                'X-User-Id': userId,
                'X-User-Role': this.getUserRole() || ''
            } : {}
        });
        
        if (response.status === 401) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Session expired. Please login again.');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }

    async getTranscriptions() {
        // Get user_id from localStorage (preferred) or sessionStorage (fallback)
        const userId = this.getUserId();
        const url = userId ? 
            `${API_BASE_URL}/transcriptions?user_id=${userId}` : 
            `${API_BASE_URL}/transcriptions`;
        
        const response = await fetch(url, {
            credentials: 'include',
            headers: userId ? { 
                'X-User-Id': userId,
                'X-User-Role': this.getUserRole() || ''
            } : {}
        });
        
        if (response.status === 401) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Session expired. Please login again.');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }

    async getNotes() {
        // Get user_id from localStorage (preferred) or sessionStorage (fallback)
        const userId = this.getUserId();
        const url = userId ? 
            `${API_BASE_URL}/notes?user_id=${userId}` : 
            `${API_BASE_URL}/notes`;
        
        const response = await fetch(url, {
            credentials: 'include',
            headers: userId ? { 
                'X-User-Id': userId,
                'X-User-Role': this.getUserRole() || ''
            } : {}
        });
        
        if (response.status === 401) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Session expired. Please login again.');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }

    async getTeacherTranscriptions() {
        return this.getTranscriptions();
    }

    async getTeacherNotes() {
        return this.getNotes();
    }

    async getTeacherBroadcasts(status = 'all') {
        const response = await fetch(`${API_BASE_URL}/teacher/broadcasts?status=${status}`, {
            credentials: 'include'
        });
        return response.json();
    }

    async getAttendance(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/${broadcastId}`, {
            credentials: 'include'
        });
        return response.json();
    }

    // Student - Broadcasts
    async getActiveBroadcasts() {
        const response = await fetch(`${API_BASE_URL}/student/broadcasts`, {
            credentials: 'include'
        });
        return response.json();
    }

    async joinBroadcast(broadcastId, username) {
        const response = await fetch(`${API_BASE_URL}/student/broadcasts/${broadcastId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username })
        });
        return response.json();
    }

    // Student-specific methods (backward compatibility - now use unified endpoints)
    async getStudentRecordings() {
        return this.getRecordings();
    }

    async getStudentTranscriptions() {
        return this.getTranscriptions();
    }

    async getStudentNotes() {
        return this.getNotes();
    }

    // Broadcast Status and Downloads
    async getBroadcastStatus(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/broadcasts/${broadcastId}/status`, {
            credentials: 'include'
        });
        return response.json();
    }

    async triggerTranscription(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/broadcasts/${broadcastId}/transcribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        return response.json();
    }

    async triggerNotesGeneration(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/broadcasts/${broadcastId}/generate-notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        return response.json();
    }

    async getTranscript(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/broadcasts/${broadcastId}/transcript`, {
            credentials: 'include'
        });
        return response.json();
    }

    async getNotesForBroadcast(broadcastId) {
        const response = await fetch(`${API_BASE_URL}/broadcasts/${broadcastId}/notes`, {
            credentials: 'include'
        });
        return response.json();
    }

    async generateNotesFromText(text, title) {
        const userId = this.getUserId();
        const response = await fetch(`${API_BASE_URL}/notes/generate-from-text`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(userId ? { 'X-User-Id': userId, 'X-User-Role': this.getUserRole() || '' } : {})
            },
            credentials: 'include',
            body: JSON.stringify({ text: text, title: title || 'Generated Notes' })
        });
        return response.json();
    }

    async getInstructors() {
        const response = await fetch(`${API_BASE_URL}/instructors`, {
            credentials: 'include'
        });
        return response.json();
    }

    // File Upload
    async uploadAudio(file, title, broadcastId = null, userId = null) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', title);
        if (broadcastId) {
            formData.append('broadcast_id', broadcastId);
        }
        if (userId) {
            formData.append('user_id', userId);
        }

        const response = await fetch(`${API_BASE_URL}/upload/audio`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        return response.json();
    }

    async deleteRecording(recordingId) {
        const response = await fetch(`${API_BASE_URL}/recordings/${recordingId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return response.json();
    }

    // Transcription
    async createTranscription(transcriptionData) {
        const response = await fetch(`${API_BASE_URL}/transcriptions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(transcriptionData)
        });
        return response.json();
    }

    // Notes
    async createNote(noteData) {
        const response = await fetch(`${API_BASE_URL}/notes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(noteData)
        });
        return response.json();
    }

    async deleteNote(noteId) {
        const response = await fetch(`${API_BASE_URL}/notes/${noteId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        return response.json();
    }

    // WebSocket Connection
    connectWebSocket() {
        if (typeof io === 'undefined') {
            console.error('Socket.IO not loaded');
            return;
        }

        this.socket = io(WS_URL, {
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('Connected to WebSocket server');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from WebSocket server');
        });

        return this.socket;
    }

    // WebSocket - Broadcast Events
    joinBroadcastRoom(broadcastId, callback) {
        if (!this.socket) this.connectWebSocket();
        
        this.socket.emit('join_broadcast', { broadcast_id: broadcastId });
        this.currentBroadcastId = broadcastId;

        this.socket.on('joined_broadcast', (data) => {
            console.log('Joined broadcast room:', data);
            if (callback) callback(data);
        });

        this.socket.on('new_broadcast', (data) => {
            console.log('New broadcast started:', data);
            if (window.onNewBroadcast) window.onNewBroadcast(data);
        });

        this.socket.on('broadcast_ended', (data) => {
            console.log('Broadcast ended:', data);
            if (window.onBroadcastEnded) window.onBroadcastEnded(data);
        });

        this.socket.on('attendance_update', (data) => {
            console.log('Attendance update:', data);
            if (window.onAttendanceUpdate) window.onAttendanceUpdate(data);
        });
    }

    leaveBroadcastRoom(broadcastId) {
        if (this.socket) {
            this.socket.emit('leave_broadcast', { broadcast_id: broadcastId });
            this.currentBroadcastId = null;
        }
    }

    // WebSocket - Chat
    sendChatMessage(broadcastId, username, message) {
        if (!this.socket) this.connectWebSocket();
        
        this.socket.emit('chat_message', {
            broadcast_id: broadcastId,
            username: username,
            message: message
        });
    }

    onChatMessage(callback) {
        if (!this.socket) this.connectWebSocket();
        
        this.socket.on('new_message', (data) => {
            if (callback) callback(data);
        });
    }

    getChatHistory(broadcastId, callback) {
        if (!this.socket) this.connectWebSocket();
        
        this.socket.emit('get_chat_history', { broadcast_id: broadcastId });
        
        this.socket.on('chat_history', (messages) => {
            if (callback) callback(messages);
        });
    }
}

// Initialize global API instance
const api = new LectureFlowAPI();

