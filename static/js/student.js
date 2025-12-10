// Student Dashboard Management
class StudentManager {
    constructor() {
        this.currentUser = null;
        this.activeBroadcasts = [];
    }

    // Check authentication
    async checkAuth() {
        // Try localStorage first, then sessionStorage for backward compatibility
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (!userStr) {
            window.location.href = 'login .html';
            return false;
        }

        this.currentUser = JSON.parse(userStr);
        if (this.currentUser.role !== 'student') {
            alert('Access denied. Student access required.');
            window.location.href = 'login .html';
            return false;
        }

        return true;
    }

    // Logout
    async logout() {
        try {
            await api.logout();
            localStorage.clear();
            sessionStorage.clear();
            window.location.href = 'login .html';
        } catch (error) {
            console.error('Logout error:', error);
            localStorage.clear();
            sessionStorage.clear();
            window.location.href = 'login .html';
        }
    }

    // Load active broadcasts
    async loadActiveBroadcasts() {
        try {
            this.activeBroadcasts = await api.getActiveBroadcasts();
            return this.activeBroadcasts;
        } catch (error) {
            console.error('Error loading broadcasts:', error);
            return [];
        }
    }

    // Join broadcast
    async joinBroadcast(broadcastId, username) {
        try {
            const result = await broadcastManager.joinBroadcast(broadcastId, username);
            return result;
        } catch (error) {
            console.error('Error joining broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // Load recordings
    async loadRecordings() {
        try {
            return await api.getStudentRecordings();
        } catch (error) {
            console.error('Error loading recordings:', error);
            return [];
        }
    }

    // Load transcriptions
    async loadTranscriptions() {
        try {
            return await api.getStudentTranscriptions();
        } catch (error) {
            console.error('Error loading transcriptions:', error);
            return [];
        }
    }

    // Load notes
    async loadNotes() {
        try {
            return await api.getStudentNotes();
        } catch (error) {
            console.error('Error loading notes:', error);
            return [];
        }
    }

    // Load instructors
    async loadInstructors() {
        try {
            return await api.getInstructors();
        } catch (error) {
            console.error('Error loading instructors:', error);
            return [];
        }
    }

    // Start polling for broadcasts
    startBroadcastPolling(callback, interval = 5000) {
        this.pollInterval = setInterval(async () => {
            const broadcasts = await this.loadActiveBroadcasts();
            if (callback) callback(broadcasts);
        }, interval);
    }

    stopBroadcastPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
}

// Initialize student manager
const studentManager = new StudentManager();

// Global refresh function for broadcasts
window.refreshBroadcastList = async function() {
    if (window.displayBroadcasts) {
        const broadcasts = await studentManager.loadActiveBroadcasts();
        window.displayBroadcasts(broadcasts);
    }
};


