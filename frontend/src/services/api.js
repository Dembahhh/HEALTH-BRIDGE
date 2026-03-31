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

/**
 * Get Firebase auth token for non-axios requests (e.g. fetch-based SSE).
 * @returns {Promise<string|null>} Bearer token or null if not authenticated.
 */
async function getAuthToken() {
    try {
        const user = auth.currentUser;
        if (user) {
            return await user.getIdToken();
        }
    } catch (error) {
        console.error('Error getting auth token:', error);
    }
    return null;
}

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

    /**
     * Send a message via SSE streaming for progressive updates.
     *
     * Auto-routes between quick (single LLM) and full crew pipelines on the
     * server side based on question complexity.
     *
     * @param {string} sessionId  - Active chat session ID.
     * @param {string} content    - User message text.
     * @param {function} onChunk  - Called with each SSE event object.
     * @param {function} onComplete - Called when stream finishes successfully.
     * @param {function} onError  - Called on errors with Error object.
     * @returns {function} Abort function — call to cancel the stream.
     */
    sendStreamingMessage: (sessionId, content, onChunk, onComplete, onError) => {
        const controller = new AbortController();

        (async () => {
            try {
                const token = await getAuthToken();
                if (!token) {
                    onError(new Error('Not authenticated'));
                    return;
                }

                const response = await fetch(`${baseURL}/chat/stream`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                    body: JSON.stringify({ session_id: sessionId, content }),
                    signal: controller.signal,
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();

                    if (done) {
                        onComplete();
                        break;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    // Keep the last (potentially incomplete) line in the buffer
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed || !trimmed.startsWith('data: ')) continue;

                        const payload = trimmed.slice(6); // Strip "data: "

                        // Sentinel: stream finished
                        if (payload === '[DONE]') {
                            onComplete();
                            return;
                        }

                        try {
                            const parsed = JSON.parse(payload);
                            onChunk(parsed);
                        } catch (parseErr) {
                            console.warn('[SSE] Failed to parse chunk:', payload, parseErr);
                        }
                    }
                }
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('[SSE] Stream error:', error);
                    onError(error);
                }
            }
        })();

        // Return abort function for cancellation
        return () => controller.abort();
    },
};

export const trackingApi = {
    // Log a new BP, glucose, or medication entry
    logTracking: (data) => api.post('/tracking/log', data),
    
    // Get history with optional filters (?log_type=bp&limit=10)
    getHistory: (logType = null, limit = 50) => {
        let url = '/tracking/history?';
        if (logType) url += `log_type=${logType}&`;
        if (limit) url += `limit=${limit}`;
        return api.get(url);
    },
    
    // Get 7-day dashboard trends
    getTrendsSummary: () => api.get('/trends/summary'),
};

//  Lit encryptor registry 
// Allows api.js to encrypt outgoing data without importing React context.
// LitContext.jsx calls registerLitEncryptor on mount.
let _litEncryptor = null;
export const registerLitEncryptor = (fn) => { _litEncryptor = fn; };
export const unregisterLitEncryptor = () => { _litEncryptor = null; };
export const maybeEncrypt = async (value) => {
  if (!_litEncryptor || !value) return value;
  return _litEncryptor(value);
};

// Screening API 
export const screeningApi = {
  // Submit a new screening session (plaintext — backend saves it first)
  submitScreening: (data) =>
    api.post('/screening/submit', data),

  // Overwrite agent_summary + habit_plan_raw with encrypted blobs
  sealScreeningSummary: async (sessionId, { agentSummary, habitPlanRaw }) =>
    api.patch(`/screening/${sessionId}/seal`, {
      agent_summary: await maybeEncrypt(agentSummary),
      habit_plan_raw: await maybeEncrypt(habitPlanRaw),
    }),

  // Decrypt a session object's sensitive fields client-side
  decryptScreeningSession: async (session, decryptFn) => ({
    ...session,
    agent_summary: session.agent_summary
      ? await decryptFn(session.agent_summary)
      : null,
    habit_plan_raw: session.habit_plan_raw
      ? await decryptFn(session.habit_plan_raw)
      : null,
  }),
};

export default api;
