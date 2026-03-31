import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import ReactMarkdown from 'react-markdown';
import ThemeToggle from '../components/ThemeToggle';
import { ArrowLeft, Send, Sparkles, RotateCcw, Loader2, ShieldCheck } from 'lucide-react';
import { chatApi } from '../services/api';
import { useLitEncryption } from '../context/LitContext';
import useLitDecryptedMessages from '../hooks/useLitDecryptedMessages';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';

// Define allowed elements whitelist (safe formatting only, no raw HTML)
const MARKDOWN_SANITIZE_SCHEMA = {
  ...defaultSchema,
  allowedElements: [
    'p', 'br', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'blockquote', 'code', 'pre', 'hr'
    // Notably absent: 'a' (links), 'img', 'script', 'iframe'
  ],
};

const INITIAL_MESSAGE = {
  role: 'assistant',
  content: "Hello! I'm your AI health coach. I'm here to help you understand your health better and provide personalized recommendations. How can I assist you today?"
};

export default function ChatPage() {
  const { user } = useSelector((state) => state.auth);
  const uid = user?.uid;
  const storageKey = uid ? `chatSessionId_${uid}` : null;
  const { encryptField, litReady } = useLitEncryption();

  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => storageKey ? localStorage.getItem(storageKey) : null);
  const [error, setError] = useState(null);

  // Streaming state
  const [streamStatus, setStreamStatus] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const abortStreamRef = useRef(null);
  const messagesEndRef = useRef(null);
  const sessionInitialized = useRef(false);
  const lastUidRef = useRef(uid);

  // displayMessages — decrypted copy for rendering
  // messages — source of truth (may contain encrypted blobs)
  const decryptedMessages = useLitDecryptedMessages(messages, uid);
  const [displayMessages, setDisplayMessages] = useState([INITIAL_MESSAGE]);

  // Keep displayMessages in sync with decryptedMessages
  useEffect(() => {
    setDisplayMessages(decryptedMessages);
  }, [decryptedMessages]);

  // Encrypt an AI response — returns encrypted blob, or plaintext if Lit not ready
  const sealAiContent = useCallback(async (plaintext) => {
    if (!litReady || !uid) return plaintext;
    try {
      return await encryptField(plaintext);
    } catch (err) {
      console.warn('[ChatPage] Encrypt failed, storing plaintext:', err);
      return plaintext; // fail open
    }
  }, [litReady, uid, encryptField]);

  // Reset session when user identity changes
  useEffect(() => {
    if (uid && uid !== lastUidRef.current) {
      lastUidRef.current = uid;
      const key = `chatSessionId_${uid}`;
      const savedSession = localStorage.getItem(key);
      setSessionId(savedSession);
      setMessages([INITIAL_MESSAGE]);
      setDisplayMessages([INITIAL_MESSAGE]);
      setError(null);
      setStreamStatus('');
      setIsStreaming(false);
      sessionInitialized.current = false;
    }
  }, [uid]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [displayMessages, streamStatus]);

  // Initialize or restore chat session
  const initializeSession = useCallback(async () => {
    if (sessionInitialized.current || !storageKey) return;
    sessionInitialized.current = true;
    console.log('[ChatPage] Initializing session for user:', uid, 'existing sessionId:', sessionId);
    try {
      // 1. Try loading from localStorage-cached session ID
      if (sessionId) {
        console.log('[ChatPage] Loading existing session messages...');
        const response = await chatApi.getSessionMessages(sessionId);
        if (response.data.messages && response.data.messages.length > 0) {
          setMessages(response.data.messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })));
          console.log('[ChatPage] Loaded', response.data.messages.length, 'messages');
          return;
        }
      }

      // 2. No local session — try restoring from backend
      if (!sessionId) {
        console.log('[ChatPage] No local session, checking backend for recent sessions...');
        const sessionsResp = await chatApi.getSessions();
        const sessions = sessionsResp.data.sessions || [];
        if (sessions.length > 0) {
          const latest = sessions[0];
          console.log('[ChatPage] Restoring most recent session:', latest.session_id);
          const msgsResp = await chatApi.getSessionMessages(latest.session_id);
          if (msgsResp.data.messages && msgsResp.data.messages.length > 0) {
            setSessionId(latest.session_id);
            localStorage.setItem(storageKey, latest.session_id);
            setMessages(msgsResp.data.messages.map(msg => ({
              role: msg.role,
              content: msg.content
            })));
            console.log('[ChatPage] Restored', msgsResp.data.messages.length, 'messages from backend');
            return;
          }
        }
      }

      // 3. Nothing found — create a new session
      console.log('[ChatPage] Creating new session...');
      const response = await chatApi.createSession('general');
      const newSessionId = response.data.session_id;
      console.log('[ChatPage] Created session:', newSessionId);
      setSessionId(newSessionId);
      localStorage.setItem(storageKey, newSessionId);
    } catch (err) {
      console.error('[ChatPage] Failed to initialize session:', err);
      setError('Failed to initialize chat session. Please refresh.');
      if (sessionId) {
        localStorage.removeItem(storageKey);
        setSessionId(null);
        sessionInitialized.current = false;
      }
    }
  }, [sessionId, storageKey, uid]);

  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // -------------------------------------------------------------------
  // Streaming send handler
  // -------------------------------------------------------------------
  const handleSend = async () => {
    console.log('[ChatPage] handleSend called, input:', input, 'isLoading:', isLoading);
    if (!input.trim() || isLoading || isStreaming) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setDisplayMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);
    setIsStreaming(true);
    setStreamStatus('');
    setError(null);

    try {
      let currentSessionId = sessionId;
      console.log('[ChatPage] Current sessionId:', currentSessionId);
      if (!currentSessionId) {
        console.log('[ChatPage] No session, creating one...');
        const sessionResponse = await chatApi.createSession('general');
        currentSessionId = sessionResponse.data.session_id;
        console.log('[ChatPage] Created session:', currentSessionId);
        setSessionId(currentSessionId);
        if (storageKey) localStorage.setItem(storageKey, currentSessionId);
      }

      console.log('[ChatPage] Starting SSE stream for session:', currentSessionId);
      const abort = chatApi.sendStreamingMessage(
        currentSessionId,
        currentInput,
        // onChunk
        async (chunk) => {
          console.log('[ChatPage] SSE chunk:', chunk.type, chunk.content?.slice(0, 80));
          if (chunk.type === 'start' || chunk.type === 'progress') {
            setStreamStatus(chunk.content);
          } else if (chunk.type === 'complete') {
            const plaintext = chunk.content;
            // Encrypt for storage, keep plaintext for immediate display
            const sealed = await sealAiContent(plaintext);
            setMessages(prev => [...prev, { role: 'assistant', content: sealed }]);
            setDisplayMessages(prev => [...prev, { role: 'assistant', content: plaintext }]);
            setStreamStatus('');
            setIsStreaming(false);
            setIsLoading(false);
          } else if (chunk.type === 'error') {
            setError(chunk.content);
            setStreamStatus('');
            setIsStreaming(false);
            setIsLoading(false);
          }
        },
        // onComplete
        () => {
          console.log('[ChatPage] SSE stream complete');
          setStreamStatus('');
          setIsStreaming(false);
          setIsLoading(false);
        },
        // onError — fallback to non-streaming
        async (err) => {
          console.error('[ChatPage] SSE stream error, falling back:', err);
          setStreamStatus('');
          try {
            const response = await chatApi.sendAutoMessage(currentSessionId, currentInput);
            const plaintext = response.data.content;
            const sealed = await sealAiContent(plaintext);
            setMessages(prev => [...prev, { role: 'assistant', content: sealed }]);
            setDisplayMessages(prev => [...prev, { role: 'assistant', content: plaintext }]);
          } catch (fallbackErr) {
            console.error('[ChatPage] Fallback also failed:', fallbackErr);
            setError(fallbackErr.response?.data?.detail || 'Failed to get response. Please try again.');
          } finally {
            setIsStreaming(false);
            setIsLoading(false);
          }
        }
      );
      abortStreamRef.current = abort;
    } catch (err) {
      console.error('[ChatPage] Failed to send message:', err);
      setError(err.response?.data?.detail || 'Failed to get response. Please try again.');
      setStreamStatus('');
      setIsStreaming(false);
      if (err.response?.status === 404 || err.response?.status === 403) {
        if (storageKey) localStorage.removeItem(storageKey);
        setSessionId(null);
        sessionInitialized.current = false;
      }
    } finally {
      if (!isStreaming) {
        setIsLoading(false);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = async () => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
    }
    try {
      if (storageKey) localStorage.removeItem(storageKey);
      setSessionId(null);
      setMessages([INITIAL_MESSAGE]);
      setDisplayMessages([INITIAL_MESSAGE]);
      setError(null);
      setStreamStatus('');
      setIsStreaming(false);
      setIsLoading(false);
      sessionInitialized.current = false;
      const response = await chatApi.createSession('general');
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
      if (storageKey) localStorage.setItem(storageKey, newSessionId);
    } catch (err) {
      console.error('Failed to create new session:', err);
      setError('Failed to start new chat. Please try again.');
    }
  };

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header
        className="sticky top-0 z-50 px-4 py-3 flex items-center justify-between"
        style={{
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-color)'
        }}
      >
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
              }}
            >
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                  AI Health Coach
                </h1>
                {litReady && (
                  <ShieldCheck
                    className="w-4 h-4 text-emerald-500"
                    title="End-to-end encrypted"
                  />
                )}
              </div>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Always here to help</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleNewChat}
            className="p-2 rounded-lg transition-colors hover:bg-opacity-80"
            style={{ color: 'var(--text-secondary)' }}
            title="New Chat"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
          <ThemeToggle />
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4">
        {displayMessages.map((message, idx) => (
          <div
            key={idx}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
          >
            <div className={`flex items-start gap-3 max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {/* Avatar */}
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{
                  background: message.role === 'user'
                    ? 'var(--color-primary)'
                    : 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                }}
              >
                {message.role === 'user'
                  ? <span className="text-white text-sm font-bold">{user?.displayName?.charAt(0) || 'U'}</span>
                  : <Sparkles className="w-4 h-4 text-white" />
                }
              </div>
              {/* Message Bubble */}
              <div
                className="px-4 py-3 rounded-2xl"
                style={{
                  background: message.role === 'user'
                    ? 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                    : 'var(--bg-surface)',
                  color: message.role === 'user' ? 'white' : 'var(--text-primary)',
                  border: message.role === 'user' ? 'none' : '1px solid var(--border-color)',
                  borderRadius: message.role === 'user'
                    ? '1.25rem 1.25rem 0.25rem 1.25rem'
                    : '1.25rem 1.25rem 1.25rem 0.25rem'
                }}
              >
                {message.role === 'assistant' ? (
                  <div className="text-sm leading-relaxed assistant-markdown">
                    <ReactMarkdown
                      rehypePlugins={[[rehypeSanitize, MARKDOWN_SANITIZE_SCHEMA]]}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm leading-relaxed">{message.content}</p>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Streaming progress indicator */}
        {isStreaming && streamStatus && (
          <div className="flex justify-start animate-fadeIn">
            <div className="flex items-start gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                }}
              >
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div
                className="px-4 py-3 rounded-2xl"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '1.25rem 1.25rem 1.25rem 0.25rem'
                }}
              >
                <div className="flex items-center gap-2">
                  <Loader2
                    className="w-4 h-4 animate-spin"
                    style={{ color: 'var(--color-primary)' }}
                  />
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {streamStatus}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading indicator (fallback) */}
        {isLoading && !streamStatus && (
          <div className="flex justify-start animate-fadeIn">
            <div className="flex items-start gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                }}
              >
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div
                className="px-4 py-3 rounded-2xl"
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '1.25rem 1.25rem 1.25rem 0.25rem'
                }}
              >
                <div className="flex gap-1">
                  <div
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ background: 'var(--color-primary)', animationDelay: '0ms' }}
                  />
                  <div
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ background: 'var(--color-primary)', animationDelay: '150ms' }}
                  />
                  <div
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ background: 'var(--color-primary)', animationDelay: '300ms' }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="flex justify-center animate-fadeIn">
            <div
              className="px-4 py-2 rounded-lg text-sm"
              style={{
                background: 'var(--color-error, #ef4444)',
                color: 'white',
                opacity: 0.9
              }}
            >
              {error}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input */}
      <footer
        className="p-4"
        style={{ background: 'var(--bg-surface)', borderTop: '1px solid var(--border-color)' }}
      >
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="input w-full pr-12"
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)'
              }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || isStreaming}
            className="p-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105"
            style={{
              background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)',
              boxShadow: '0 4px 14px rgba(var(--color-primary-rgb), 0.3)'
            }}
          >
            <Send className="w-5 h-5 text-white" />
          </button>
        </div>
      </footer>
    </div>
  );
}