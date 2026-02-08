import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const ACCENT_SWATCHES = [
    { key: 'orange', color: '#F18F2E' },
    { key: 'purple', color: '#c548de' },
];

export default function ThemeToggle({ className = "" }) {
    const { theme, toggleTheme, accent, setAccent } = useTheme();

    return (
        <div className={`flex items-center gap-1.5 ${className}`}>
            {/* Accent colour swatches */}
            {ACCENT_SWATCHES.map((s) => (
                <button
                    key={s.key}
                    onClick={() => setAccent(s.key)}
                    className="w-6 h-6 rounded-full transition-all duration-200 hover:scale-110 flex-shrink-0"
                    style={{
                        background: s.color,
                        boxShadow: accent === s.key
                            ? `0 0 0 2px var(--bg-elevated), 0 0 0 4px ${s.color}`
                            : 'none',
                        opacity: accent === s.key ? 1 : 0.5,
                    }}
                    aria-label={`${s.key} accent`}
                    title={`${s.key.charAt(0).toUpperCase() + s.key.slice(1)} theme`}
                />
            ))}

            {/* Light / Dark toggle */}
            <button
                onClick={toggleTheme}
                className="p-2.5 rounded-xl transition-all duration-200 hover:scale-105"
                style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--color-primary)'
                }}
                aria-label="Toggle Theme"
            >
                {theme === 'dark' ? (
                    <Sun className="h-5 w-5" />
                ) : (
                    <Moon className="h-5 w-5" />
                )}
            </button>
        </div>
    );
}
