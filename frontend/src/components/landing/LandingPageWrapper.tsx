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
    const stored = localStorage.getItem('landingPageIndex');
    if (stored) {
      const storedNum = parseInt(stored, 10);
      if (storedNum >= 0 && storedNum < landingPagePaths.length) {
        return storedNum;
      }
    }

    const randomIndex = Math.floor(Math.random() * landingPagePaths.length);
    localStorage.setItem('landingPageIndex', randomIndex.toString());
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
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: '#FFFDF5'
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  // Render landing page
  const handleGetStarted = () => {
    history.push('/app/login');
  };

  return <LandingPageComponent onGetStarted={handleGetStarted} />;
};

export default LandingPageWrapper;
