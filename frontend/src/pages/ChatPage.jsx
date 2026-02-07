import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import ThemeToggle from '../components/ThemeToggle';
import { ArrowLeft, Send, Sparkles, RotateCcw } from 'lucide-react';
import { chatApi } from '../services/api';

const INITIAL_MESSAGE = {
    role: 'assistant',
    content: "Hello! I'm your AI health coach. I'm here to help you understand your health better and provide personalized recommendations. How can I assist you today?"
};

export default function ChatPage() {
    const { user } = useSelector((state) => state.auth);
    const [messages, setMessages] = useState([INITIAL_MESSAGE]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState(() => localStorage.getItem('chatSessionId'));
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const sessionInitialized = useRef(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Initialize or restore chat session
    const initializeSession = useCallback(async () => {
        if (sessionInitialized.current) return;
        sessionInitialized.current = true;

        console.log('[ChatPage] Initializing session, existing sessionId:', sessionId);

        try {
            // If we have a stored session, try to load its messages
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
            // Create a new session if none exists
            console.log('[ChatPage] Creating new session...');
            const response = await chatApi.createSession('general');
            const newSessionId = response.data.session_id;
            console.log('[ChatPage] Created session:', newSessionId);
            setSessionId(newSessionId);
            localStorage.setItem('chatSessionId', newSessionId);
        } catch (err) {
            console.error('[ChatPage] Failed to initialize session:', err);
            setError('Failed to initialize chat session. Please refresh.');
            // If session restoration fails (e.g., invalid session), create a new one
            if (sessionId) {
                localStorage.removeItem('chatSessionId');
                setSessionId(null);
                sessionInitialized.current = false;
            }
        }
    }, [sessionId]);

    useEffect(() => {
        initializeSession();
    }, [initializeSession]);

    const handleSend = async () => {
        console.log('[ChatPage] handleSend called, input:', input, 'isLoading:', isLoading);
        if (!input.trim() || isLoading) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        const currentInput = input;
        setInput('');
        setIsLoading(true);
        setError(null);

        try {
            // Ensure we have a session
            let currentSessionId = sessionId;
            console.log('[ChatPage] Current sessionId:', currentSessionId);

            if (!currentSessionId) {
                console.log('[ChatPage] No session, creating one...');
                const sessionResponse = await chatApi.createSession('general');
                currentSessionId = sessionResponse.data.session_id;
                console.log('[ChatPage] Created session:', currentSessionId);
                setSessionId(currentSessionId);
                localStorage.setItem('chatSessionId', currentSessionId);
            }

            // Send message to backend (using quick mode for fast responses)
            console.log('[ChatPage] Sending message to session:', currentSessionId);
            const response = await chatApi.sendQuickMessage(currentSessionId, currentInput);
            console.log('[ChatPage] Got response:', response.data);

            const aiResponse = {
                role: 'assistant',
                content: response.data.content
            };
            setMessages(prev => [...prev, aiResponse]);
        } catch (err) {
            console.error('[ChatPage] Failed to send message:', err);
            const errorMessage = err.response?.data?.detail || 'Failed to get response. Please try again.';
            setError(errorMessage);

            // If session is invalid, clear it and retry
            if (err.response?.status === 404 || err.response?.status === 403) {
                localStorage.removeItem('chatSessionId');
                setSessionId(null);
                sessionInitialized.current = false;
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleNewChat = async () => {
        try {
            localStorage.removeItem('chatSessionId');
            setSessionId(null);
            setMessages([INITIAL_MESSAGE]);
            setError(null);
            sessionInitialized.current = false;

            const response = await chatApi.createSession('general');
            const newSessionId = response.data.session_id;
            setSessionId(newSessionId);
            localStorage.setItem('chatSessionId', newSessionId);
        } catch (err) {
            console.error('Failed to create new session:', err);
            setError('Failed to start new chat. Please try again.');
        }
    };

    return (
        <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
            {/* Header */}
            <header className="sticky top-0 z-50 px-4 py-3 flex items-center justify-between"
                style={{
                    background: 'var(--bg-surface)',
                    borderBottom: '1px solid var(--border-color)'
                }}>
                <div className="flex items-center gap-4">
                    <Link to="/dashboard"
                        className="p-2 rounded-lg transition-colors"
                        style={{ color: 'var(--text-secondary)' }}>
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}>
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="font-semibold" style={{ color: 'var(--text-primary)' }}>AI Health Coach</h1>
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
                {messages.map((message, idx) => (
                    <div key={idx}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}>
                        <div className={`flex items-start gap-3 max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            {/* Avatar */}
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                                style={{
                                    background: message.role === 'user'
                                        ? 'var(--color-primary)'
                                        : 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                                }}>
                                {message.role === 'user'
                                    ? <span className="text-white text-sm font-bold">{user?.displayName?.charAt(0) || 'U'}</span>
                                    : <Sparkles className="w-4 h-4 text-white" />
                                }
                            </div>
                            {/* Message Bubble */}
                            <div className="px-4 py-3 rounded-2xl"
                                style={{
                                    background: message.role === 'user'
                                        ? 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)'
                                        : 'var(--bg-surface)',
                                    color: message.role === 'user' ? 'white' : 'var(--text-primary)',
                                    border: message.role === 'user' ? 'none' : '1px solid var(--border-color)',
                                    borderRadius: message.role === 'user'
                                        ? '1.25rem 1.25rem 0.25rem 1.25rem'
                                        : '1.25rem 1.25rem 1.25rem 0.25rem'
                                }}>
                                <p className="text-sm leading-relaxed">{message.content}</p>
                            </div>
                        </div>
                    </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                    <div className="flex justify-start animate-fadeIn">
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                                style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}>
                                <Sparkles className="w-4 h-4 text-white" />
                            </div>
                            <div className="px-4 py-3 rounded-2xl"
                                style={{
                                    background: 'var(--bg-surface)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '1.25rem 1.25rem 1.25rem 0.25rem'
                                }}>
                                <div className="flex gap-1">
                                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--color-primary)', animationDelay: '0ms' }} />
                                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--color-primary)', animationDelay: '150ms' }} />
                                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--color-primary)', animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Error display */}
                {error && (
                    <div className="flex justify-center animate-fadeIn">
                        <div className="px-4 py-2 rounded-lg text-sm"
                            style={{
                                background: 'var(--color-error, #ef4444)',
                                color: 'white',
                                opacity: 0.9
                            }}>
                            {error}
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </main>

            {/* Input */}
            <footer className="p-4" style={{ background: 'var(--bg-surface)', borderTop: '1px solid var(--border-color)' }}>
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
                        disabled={!input.trim() || isLoading}
                        className="p-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105"
                        style={{
                            background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)',
                            boxShadow: '0 4px 14px rgba(241, 143, 46, 0.3)'
                        }}>
                        <Send className="w-5 h-5 text-white" />
                    </button>
                </div>
            </footer>
        </div>
    );
}
