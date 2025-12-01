// Teacher Dashboard Management
class TeacherManager {
    constructor() {
        this.currentUser = null;
        this.currentBroadcast = null;
    }

    // Check authentication
    async checkAuth() {
        const userStr = sessionStorage.getItem('user');
        if (!userStr) {
            window.location.href = 'login .html';
            return false;
        }

        this.currentUser = JSON.parse(userStr);
        if (this.currentUser.role !== 'teacher') {
            alert('Access denied. Teacher access required.');
            window.location.href = 'login .html';
            return false;
        }

        return true;
    }

    // Logout
    async logout() {
        try {
            await api.logout();
            sessionStorage.clear();
            window.location.href = 'login .html';
        } catch (error) {
            console.error('Logout error:', error);
            sessionStorage.clear();
            window.location.href = 'login .html';
        }
    }

    // Start broadcast
    async startBroadcast(lectureTopic, courseTitle, courseId = null) {
        try {
            const result = await broadcastManager.startBroadcast(lectureTopic, courseTitle, courseId);
            if (result.success) {
                this.currentBroadcast = result.broadcast;
                return result;
            }
            return result;
        } catch (error) {
            console.error('Error starting broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // End broadcast
    async endBroadcast() {
        try {
            const result = await broadcastManager.endBroadcast();
            if (result.success) {
                this.currentBroadcast = null;
            }
            return result;
        } catch (error) {
            console.error('Error ending broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // Load recordings
    async loadRecordings() {
        try {
            return await api.getRecordings();
        } catch (error) {
            console.error('Error loading recordings:', error);
            return [];
        }
    }

    // Load attendance
    async loadAttendance(broadcastId) {
        try {
            return await api.getAttendance(broadcastId);
        } catch (error) {
            console.error('Error loading attendance:', error);
            return [];
        }
    }
}

// Initialize teacher manager
const teacherManager = new TeacherManager();


