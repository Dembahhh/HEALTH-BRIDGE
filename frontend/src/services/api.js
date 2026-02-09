import axios from 'axios';
import { auth } from './firebase';

// API base URL resolution:
//   Local dev (.env):   VITE_API_URL=http://localhost:8000/api  → use directly
//   Docker (nginx):     VITE_API_URL=""                         → /api (nginx proxies)
//   Netlify (no var):   undefined                               → /api (Netlify _redirects proxies)
let resolvedUrl = import.meta.env.VITE_API_URL;

// Guard: strip accidental "VITE_API_URL=" prefix from value (common Netlify misconfiguration)
if (typeof resolvedUrl === 'string' && resolvedUrl.startsWith('VITE_API_URL=')) {
    resolvedUrl = resolvedUrl.slice('VITE_API_URL='.length);
}

const baseURL = (resolvedUrl !== undefined && resolvedUrl !== null && resolvedUrl !== '')
    ? resolvedUrl
    : '/api';

const api = axios.create({
    baseURL,
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
    // Auto-routed: picks quick or full based on question complexity
    sendAutoMessage: (sessionId, content) => api.post('/chat/auto', { session_id: sessionId, content }, { timeout: 120000 }),
    // Feedback on assistant messages
    submitFeedback: (messageId, sessionId, rating, comment = null) =>
        api.post('/chat/feedback', { message_id: messageId, session_id: sessionId, rating, comment }),
    getSessionMessages: (sessionId) => api.get(`/chat/session/${sessionId}/messages`),
    getSessions: () => api.get('/chat/sessions'),
};

export default api;
