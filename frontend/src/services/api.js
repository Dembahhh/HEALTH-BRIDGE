import axios from 'axios';
import { auth } from './firebase';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add auth token to every request
api.interceptors.request.use(async (config) => {
    try {
        const user = auth.currentUser;
        if (user) {
            const token = await user.getIdToken();
            config.headers.Authorization = `Bearer ${token}`;
        }
    } catch (error) {
        console.error('Error getting auth token:', error);
    }
    return config;
});

export const chatApi = {
    createSession: (type = 'general') => api.post('/chat/session', { session_type: type }),
    // Quick chat - single LLM call, fast responses (2-5 seconds)
    sendQuickMessage: (sessionId, content) => api.post('/chat/quick', { session_id: sessionId, content }, { timeout: 30000 }),
    // Full agent crew - comprehensive analysis (30-60+ seconds)
    sendMessage: (sessionId, content) => api.post('/chat/message', { session_id: sessionId, content }, { timeout: 120000 }),
    getSessionMessages: (sessionId) => api.get(`/chat/session/${sessionId}/messages`),
    getSessions: () => api.get('/chat/sessions'),
};

export default api;
