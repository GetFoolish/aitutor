/**
 * Landing Page Wrapper
 * Dynamically loads all landing pages from ./landingpages folder
 * Randomly selects one for root path, or shows specific page for /landing/:id
 */
import React, { useEffect, useState } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

// Dynamically import all landing pages
const landingPages = import.meta.glob('./landingpages/LandingPage*.tsx');
const landingPagePaths = Object.keys(landingPages).sort();

const LandingPageWrapper: React.FC = () => {
  const history = useHistory();
  const { id } = useParams<{ id?: string }>();
  const { isAuthenticated, isLoading } = useAuth();
  const [selectedPageIndex, setSelectedPageIndex] = useState<number | null>(null);
  const [LandingPageComponent, setLandingPageComponent] = useState<React.ComponentType<any> | null>(null);

  // Get random landing page index (persist across sessions with localStorage)
  const getRandomLandingPage = (): number => {
    try {
      const stored = localStorage.getItem('landingPageIndex');
      if (stored) {
        const storedNum = parseInt(stored, 10);
        if (storedNum >= 0 && storedNum < landingPagePaths.length) {
          return storedNum;
        }
      }
    } catch { /* private browsing — localStorage unavailable */ }

    const randomIndex = Math.floor(Math.random() * landingPagePaths.length);
    try { localStorage.setItem('landingPageIndex', randomIndex.toString()); } catch { /* private browsing */ }
    return randomIndex;
  };

  useEffect(() => {
    // Determine which page to load
    let pageIndex: number;

    if (id) {
      // If /landing/:id route, use that specific page (1-indexed)
      pageIndex = parseInt(id, 10) - 1;
      if (pageIndex < 0 || pageIndex >= landingPagePaths.length) {
        pageIndex = 0; // Default to first page if invalid
      }
    } else {
      // For root route, use random selection
      pageIndex = getRandomLandingPage();
    }

    setSelectedPageIndex(pageIndex);

    // Dynamically load the component
    const loadComponent = async () => {
      try {
        const modulePath = landingPagePaths[pageIndex];
        const module = await landingPages[modulePath]() as any;
        setLandingPageComponent(() => module.default);
      } catch (error) {
        console.error('Error loading landing page:', error);
      }
    };

    loadComponent();
  }, [id]);

  useEffect(() => {
    // If authenticated, redirect to app
    if (!isLoading && isAuthenticated) {
      history.replace('/app');
      return;
    }
  }, [isAuthenticated, isLoading, history]);

  // Show loading while checking authentication or loading component
  if (isLoading || selectedPageIndex === null || !LandingPageComponent) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '16px',
        background: '#FFFDF5',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}>
        <div style={{
          width: '200px',
          height: '8px',
          border: '3px solid #000',
          backgroundColor: '#fff',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: '40%',
            backgroundColor: '#FFD93D',
            animation: 'landing-loading-bar 1.5s ease-in-out infinite',
          }} />
        </div>
        <div style={{
          fontWeight: 900,
          fontSize: '16px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#000',
        }}>
          Loading...
        </div>
        <style>{`
          @keyframes landing-loading-bar {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
          }
        `}</style>
      </div>
    );
  }

  // Render landing page
  const handleGetStarted = () => {
    history.push('/app/dev-login');
  };

  return <LandingPageComponent onGetStarted={handleGetStarted} />;
};

export default LandingPageWrapper;
