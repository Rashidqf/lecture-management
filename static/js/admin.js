// Admin Dashboard Management
class AdminManager {
    constructor() {
        this.currentUser = null;
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
        if (this.currentUser.role !== 'admin') {
            alert('Access denied. Admin access required.');
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

    // Load dashboard stats
    async loadDashboardStats() {
        try {
            const [teachers, students] = await Promise.all([
                api.getTeachers(),
                api.getStudents()
            ]);

            // Update stats display if elements exist
            const teacherCount = document.getElementById('teacherCount');
            const studentCount = document.getElementById('studentCount');
            
            if (teacherCount) teacherCount.textContent = teachers.length || 0;
            if (studentCount) studentCount.textContent = students.length || 0;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }
}

// Initialize admin manager
const adminManager = new AdminManager();


