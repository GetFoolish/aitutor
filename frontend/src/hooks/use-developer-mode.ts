/**
 * Developer mode hook - Controls Gemini Console visibility via localStorage
 * Activated by Ctrl+Shift+D keyboard shortcut
 */
import { useState, useEffect } from 'react';

const DEVELOPER_MODE_KEY = 'ai-tutor-dev-mode';

export const useDeveloperMode = () => {
  const [isDeveloperMode, setIsDeveloperMode] = useState(() => {
    return localStorage.getItem(DEVELOPER_MODE_KEY) === 'true';
  });

  const toggleDeveloperMode = () => {
    const newValue = !isDeveloperMode;
    setIsDeveloperMode(newValue);
    localStorage.setItem(DEVELOPER_MODE_KEY, String(newValue));

    // Log to console for user feedback
    if (newValue) {
      console.log('🔧 Developer mode enabled - Gemini Console is now visible');
    } else {
      console.log('🔧 Developer mode disabled - Gemini Console is now hidden');
    }
  };

  // Sync with localStorage changes from other tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === DEVELOPER_MODE_KEY) {
        setIsDeveloperMode(e.newValue === 'true');
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return { isDeveloperMode, toggleDeveloperMode };
};
