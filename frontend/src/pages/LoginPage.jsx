import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { loginWithGoogle, loginWithEmail } from '../features/auth/authSlice';
import { useNavigate, Navigate, Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';

export default function LoginPage() {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { loading, error, isAuthenticated } = useSelector((state) => state.auth);

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />;
    }

    const handleGoogleLogin = () => {
        dispatch(loginWithGoogle());
    };

    const handleEmailLogin = (e) => {
        e.preventDefault();
        dispatch(loginWithEmail({ email, password }));
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 relative overflow-hidden"
            style={{ background: 'var(--bg-primary)' }}>

            {/* Background Gradient Orbs */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full opacity-20"
                    style={{ background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)' }} />
                <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full opacity-15"
                    style={{ background: 'radial-gradient(circle, var(--color-accent) 0%, transparent 70%)' }} />
            </div>

            {/* Theme Toggle */}
            <div className="absolute top-6 right-6">
                <ThemeToggle />
            </div>

            {/* Logo */}
            <div className="absolute top-6 left-6">
                <Link to="/" className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}>
                        <span className="text-white font-bold text-lg">H</span>
                    </div>
                    <span className="font-bold text-xl" style={{ color: 'var(--text-primary)' }}>HealthBridge</span>
                </Link>
            </div>

            <div className="max-w-md w-full animate-fadeIn relative z-10">
                {/* Card */}
                <div className="rounded-2xl p-8 sm:p-10 shadow-2xl"
                    style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-color)'
                    }}>

                    <div className="text-center mb-8">
                        <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                            Welcome Back
                        </h2>
                        <p style={{ color: 'var(--text-secondary)' }}>
                            Sign in to continue your health journey
                        </p>
                    </div>

                    {error && (
                        <div className="mb-6 px-4 py-3 rounded-xl text-sm"
                            style={{
                                background: 'rgba(231, 70, 39, 0.1)',
                                border: '1px solid rgba(231, 70, 39, 0.3)',
                                color: 'var(--color-accent)'
                            }}>
                            {error}
                        </div>
                    )}

                    <form className="space-y-5" onSubmit={handleEmailLogin}>
                        <div>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                required
                                placeholder="Email address"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="input w-full"
                                style={{
                                    background: 'var(--bg-elevated)',
                                    border: '1px solid var(--border-color)',
                                    color: 'var(--text-primary)'
                                }}
                            />
                        </div>

                        <div>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                required
                                placeholder="Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="input w-full"
                                style={{
                                    background: 'var(--bg-elevated)',
                                    border: '1px solid var(--border-color)',
                                    color: 'var(--text-primary)'
                                }}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary w-full text-center"
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Signing in...
                                </span>
                            ) : 'Sign In'}
                        </button>
                    </form>

                    <div className="my-8 flex items-center">
                        <div className="flex-1 h-px" style={{ background: 'var(--border-color)' }} />
                        <span className="px-4 text-sm" style={{ color: 'var(--text-muted)' }}>or continue with</span>
                        <div className="flex-1 h-px" style={{ background: 'var(--border-color)' }} />
                    </div>

                    <button
                        onClick={handleGoogleLogin}
                        disabled={loading}
                        className="btn-secondary w-full flex items-center justify-center gap-3"
                    >
                        <img className="h-5 w-5" src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" />
                        Google
                    </button>

                    <p className="mt-8 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                        Don't have an account?{' '}
                        <Link to="/signup" className="font-semibold hover:underline" style={{ color: 'var(--color-primary)' }}>
                            Sign Up
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
