import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import ThemeToggle from '../components/ThemeToggle';
import { ArrowLeft, Send, Sparkles, User } from 'lucide-react';

export default function ChatPage() {
    const { user } = useSelector((state) => state.auth);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: "Hello! I'm your AI health coach. I'm here to help you understand your health better and provide personalized recommendations. How can I assist you today?"
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        // Simulate AI response (replace with actual API call)
        setTimeout(() => {
            const aiResponse = {
                role: 'assistant',
                content: "Thank you for sharing that with me. Based on your profile and what you've told me, I'd recommend focusing on regular physical activity and maintaining a balanced diet. Would you like more specific recommendations?"
            };
            setMessages(prev => [...prev, aiResponse]);
            setIsLoading(false);
        }, 1500);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
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
                <ThemeToggle />
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
