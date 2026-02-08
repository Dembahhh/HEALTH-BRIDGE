import axios from 'axios';
import { auth } from './firebase';

// When VITE_API_URL is explicitly empty (Docker/nginx), use relative URL so
// requests go through the nginx proxy at /api/. When undefined (local dev),
// fall back to localhost:8000.
const apiBase = import.meta.env.VITE_API_URL !== undefined
    ? import.meta.env.VITE_API_URL
    : 'http://localhost:8000';

const api = axios.create({
    baseURL: `${apiBase}/api`,
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
    sendQuickMessage: (sessionId, content) => api.post('/chat/quick', { session_id: sessionId, content }, { timeout: 60000 }),
    // Full agent crew - comprehensive analysis (30-60+ seconds)
    sendMessage: (sessionId, content) => api.post('/chat/message', { session_id: sessionId, content }, { timeout: 120000 }),
    // Auto-routed: system decides quick vs full pipeline
    sendAutoMessage: (sessionId, content) => api.post('/chat/auto', { session_id: sessionId, content }, { timeout: 120000 }),
    // Feedback
    submitFeedback: (messageId, sessionId, rating, comment = null) => 
        api.post('/chat/feedback', { message_id: messageId, session_id: sessionId, rating, comment }),
    getSessionMessages: (sessionId) => api.get(`/chat/session/${sessionId}/messages`),
    getSessions: () => api.get('/chat/sessions'),
};

export default api;
