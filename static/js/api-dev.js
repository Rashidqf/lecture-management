// Development API Client - Without credentials for file:// protocol
// Use this if you're opening HTML files directly (file://)

const API_BASE_URL = 'http://localhost:5000/api';
const WS_URL = 'http://localhost:5000';

// Check if we're using file:// protocol
const isFileProtocol = window.location.protocol === 'file:';

class LectureFlowAPI {
    constructor() {
        this.socket = null;
        this.currentBroadcastId = null;
        // Don't use credentials for file:// protocol
        this.useCredentials = !isFileProtocol;
    }

    // Authentication
    async login(email, password) {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: this.useCredentials ? 'include' : 'omit',
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
            credentials: this.useCredentials ? 'include' : 'omit'
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
            credentials: this.useCredentials ? 'include' : 'omit',
            mode: 'cors',
            body: JSON.stringify(userData)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    // ... rest of the methods with credentials: this.useCredentials ? 'include' : 'omit'
}

// For file:// protocol, we'll use sessionStorage instead of server sessions
if (isFileProtocol) {
    console.warn('Running in file:// protocol. Using sessionStorage for authentication.');
}


