import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext();

const ACCENTS = ['orange', 'purple'];

export const ThemeProvider = ({ children }) => {
    const [theme, setTheme] = useState(() => {
        // Default to dark if no preference found
        const savedTheme = localStorage.getItem('theme');
        return savedTheme || 'dark';
    });

    const [accent, setAccent] = useState(() => {
        return localStorage.getItem('accent') || 'orange';
    });

    useEffect(() => {
        const root = window.document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
    }, [theme]);

    useEffect(() => {
        const root = window.document.documentElement;
        // Remove all accent classes, then add the active one
        ACCENTS.forEach((a) => root.classList.remove(`accent-${a}`));
        if (accent !== 'orange') {
            root.classList.add(`accent-${accent}`);
        }
        localStorage.setItem('accent', accent);
    }, [accent]);

    const toggleTheme = () => {
        setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, accent, setAccent }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => useContext(ThemeContext);
