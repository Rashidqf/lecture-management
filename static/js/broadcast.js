// Real-time Broadcast Management
class BroadcastManager {
    constructor() {
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.currentBroadcast = null;
        this.isRecording = false;
        this.stream = null;
    }

    // Teacher: Start Broadcast
    async startBroadcast(lectureTopic, courseTitle, courseId = null) {
        try {
            // Get user info from sessionStorage as fallback
            const userId = sessionStorage.getItem('userId');
            const username = sessionStorage.getItem('username');
            
            // Start broadcast via API
            const result = await api.startBroadcast({
                lecture_topic: lectureTopic,
                course_title: courseTitle,
                course_id: courseId,
                user_id: userId,  // Include user_id as fallback if session cookie fails
                username: username  // Include username as additional verification
            });

            if (result.success) {
                this.currentBroadcast = result.broadcast;
                
                // Get user media
                this.stream = await navigator.mediaDevices.getUserMedia({ 
                    audio: true,
                    video: false 
                });

                // Setup WebSocket connection
                api.joinBroadcastRoom(this.currentBroadcast.id, (data) => {
                    console.log('Joined broadcast room');
                });

                // Start recording
                this.startRecording();

                return {
                    success: true,
                    broadcast: this.currentBroadcast,
                    broadcastUrl: `${window.location.origin}${this.currentBroadcast.broadcast_url}`
                };
            }

            return result;
        } catch (error) {
            console.error('Error starting broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // Teacher: End Broadcast
    async endBroadcast() {
        if (!this.currentBroadcast) return;

        try {
            // Stop recording
            const audioBlob = await this.stopRecording();
            
            // Upload audio file
            let audioFilePath = null;
            if (audioBlob) {
                const formData = new FormData();
                formData.append('file', audioBlob, `broadcast_${this.currentBroadcast.id}.webm`);
                formData.append('title', `${this.currentBroadcast.lecture_topic} - ${this.currentBroadcast.course_title}`);
                
                const uploadResult = await api.uploadAudio(
                    formData.get('file'),
                    formData.get('title')
                );
                
                if (uploadResult.success) {
                    audioFilePath = uploadResult.recording.file_path;
                }
            }

            // End broadcast
            const result = await api.endBroadcast(this.currentBroadcast.id, audioFilePath);

            // Stop stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
                this.stream = null;
            }

            // Leave WebSocket room
            api.leaveBroadcastRoom(this.currentBroadcast.id);

            this.currentBroadcast = null;
            return result;
        } catch (error) {
            console.error('Error ending broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // Start Recording with Real-time Streaming using Web Audio API
    startRecording() {
        if (!this.stream) return;

        this.recordedChunks = [];
        
        // ALSO use MediaRecorder to save audio file while streaming
        try {
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                console.log('MediaRecorder stopped, total chunks:', this.recordedChunks.length);
            };
            
            // Start recording in chunks (every 1 second)
            this.mediaRecorder.start(1000);
            console.log('MediaRecorder started for saving audio file');
        } catch (error) {
            console.error('Error starting MediaRecorder:', error);
            // Fallback: try without mimeType
            try {
                this.mediaRecorder = new MediaRecorder(this.stream);
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        this.recordedChunks.push(event.data);
                    }
                };
                this.mediaRecorder.start(1000);
                console.log('MediaRecorder started (fallback mode)');
            } catch (err) {
                console.error('MediaRecorder not supported:', err);
            }
        }
        
        // Use Web Audio API to extract raw PCM audio data (better for real-time streaming)
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Create audio source from stream
        this.audioSource = this.audioContext.createMediaStreamSource(this.stream);
        
        // Create script processor node to capture audio data
        const bufferSize = 4096; // 4096 samples = ~93ms at 44.1kHz
        this.scriptProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);
        
        // Process audio data
        this.scriptProcessor.onaudioprocess = (event) => {
            if (!this.isRecording || !this.currentBroadcast) return;
            
            const inputBuffer = event.inputBuffer;
            const inputData = inputBuffer.getChannelData(0); // Get mono channel
            
            // Convert Float32Array to Int16Array (PCM format)
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                // Convert from -1.0 to 1.0 range to -32768 to 32767
                const s = Math.max(-1, Math.min(1, inputData[i]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            
            // Send PCM audio data via WebSocket
            if (api.socket && api.socket.connected) {
                try {
                    // Convert Int16Array to Uint8Array (little-endian, which is standard)
                    const bytes = new Uint8Array(pcmData.buffer);
                    
                    // Convert to base64 for WebSocket transmission
                    let binary = '';
                    for (let i = 0; i < bytes.byteLength; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64data = btoa(binary);
                    
                    api.socket.emit('audio_chunk', {
                        broadcast_id: this.currentBroadcast.id,
                        audio_data: base64data,
                        format: 'pcm', // Raw PCM data
                        sample_rate: this.audioContext.sampleRate,
                        channels: 1,
                        timestamp: Date.now()
                    });
                } catch (error) {
                    console.error('Error sending audio chunk:', error);
                }
            }
        };
        
        // Connect audio processing chain
        this.audioSource.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioContext.destination); // Connect to output to avoid errors
        
        this.isRecording = true;
        console.log('Started real-time audio streaming using Web Audio API (PCM format)');
    }

    // Stop Recording
    async stopRecording() {
        return new Promise((resolve) => {
            if (!this.isRecording) {
                resolve(null);
                return;
            }

            // Stop audio processing
            if (this.scriptProcessor) {
                this.scriptProcessor.disconnect();
                this.scriptProcessor = null;
            }
            
            if (this.audioSource) {
                this.audioSource.disconnect();
                this.audioSource = null;
            }
            
            // Stop MediaRecorder and create audio blob
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
                
                // Wait for all chunks to be available
                this.mediaRecorder.onstop = () => {
                    this.isRecording = false;
                    
                    // Create audio blob from recorded chunks
                    if (this.recordedChunks.length > 0) {
                        const audioBlob = new Blob(this.recordedChunks, { 
                            type: this.mediaRecorder.mimeType || 'audio/webm' 
                        });
                        console.log('Audio recording saved:', audioBlob.size, 'bytes');
                        resolve(audioBlob);
                    } else {
                        console.warn('No audio chunks recorded');
                        resolve(null);
                    }
                    
                    // Clear chunks for next recording
                    this.recordedChunks = [];
                };
            } else {
                this.isRecording = false;
                resolve(null);
            }
        });
    }

    // Student: Get Active Broadcasts
    async getActiveBroadcasts() {
        try {
            const broadcasts = await api.getActiveBroadcasts();
            return broadcasts;
        } catch (error) {
            console.error('Error fetching broadcasts:', error);
            return [];
        }
    }

    // Student: Join Broadcast
    async joinBroadcast(broadcastId, username) {
        try {
            // Join via API
            const result = await api.joinBroadcast(broadcastId, username);

            if (result.success) {
                // Join WebSocket room
                api.joinBroadcastRoom(broadcastId, (data) => {
                    console.log('Joined broadcast room');
                });

                // Setup chat message listener
                api.onChatMessage((message) => {
                    this.displayChatMessage(message);
                });

                // Load chat history
                api.getChatHistory(broadcastId, (messages) => {
                    messages.forEach(msg => this.displayChatMessage(msg));
                });

                return result;
            }

            return result;
        } catch (error) {
            console.error('Error joining broadcast:', error);
            return { success: false, message: error.message };
        }
    }

    // Send Chat Message
    sendMessage(broadcastId, username, message) {
        if (!message.trim()) return;
        
        api.sendChatMessage(broadcastId, username, message);
    }

    // Display Chat Message
    displayChatMessage(message) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message';
        messageDiv.innerHTML = `
            <strong>${message.username}:</strong> ${message.message}
            <small class="text-muted">${new Date(message.created_at).toLocaleTimeString()}</small>
        `;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Poll for active broadcasts (for real-time updates)
    startPolling(callback, interval = 5000) {
        this.pollInterval = setInterval(async () => {
            const broadcasts = await this.getActiveBroadcasts();
            if (callback) callback(broadcasts);
        }, interval);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
}

// Initialize global broadcast manager
const broadcastManager = new BroadcastManager();

// Listen for new broadcasts
window.onNewBroadcast = (broadcastData) => {
    // Refresh broadcast list for students
    if (window.refreshBroadcastList) {
        window.refreshBroadcastList();
    }
};

// Listen for broadcast ended
window.onBroadcastEnded = (data) => {
    // Refresh broadcast list
    if (window.refreshBroadcastList) {
        window.refreshBroadcastList();
    }
    
    // Show notification
    if (window.showNotification) {
        window.showNotification('Broadcast has ended', 'info');
    }
};

