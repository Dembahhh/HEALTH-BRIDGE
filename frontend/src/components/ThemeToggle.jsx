import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ className = "" }) {
    const { theme, toggleTheme } = useTheme();

    return (
        <button
            onClick={toggleTheme}
            className={`p-2 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 focus:outline-none transition-colors duration-200 ${className}`}
            aria-label="Toggle Theme"
        >
            {theme === 'dark' ? (
                <div className="flex items-center gap-2">
                    <Sun className="h-5 w-5" />
                </div>
            ) : (
                <div className="flex items-center gap-2">
                    <Moon className="h-5 w-5" />
                </div>
            )}
        </button>
    );
}
