/**
 * Landing Page Wrapper
 * Randomly selects and displays one of the available landing pages
 * Selection is persisted in localStorage for consistent user experience
 */
import React, { useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import LandingPage1 from './LandingPage1';
import LandingPageNeo from './LandingPage2';

const LandingPageWrapper: React.FC = () => {
  const history = useHistory();
  const { isAuthenticated, isLoading } = useAuth();
  const [selectedPage, setSelectedPage] = useState<number | null>(null);

  // Get random landing page (persist across sessions with localStorage)
  const getRandomLandingPage = (): number => {
    // Check localStorage first (persist across sessions)
    const stored = localStorage.getItem('landingPageIndex');
    if (stored) {
      const storedNum = parseInt(stored, 10);
      // Validate stored value is within range (1-2 available pages)
      if (storedNum >= 1 && storedNum <= 2) {
        return storedNum;
      }
    }
    
    // Generate random number 1-2 (only 2 pages available)
    const randomIndex = Math.floor(Math.random() * 2) + 1;
    localStorage.setItem('landingPageIndex', randomIndex.toString());
    return randomIndex;
  };

  useEffect(() => {
    // Set random page on mount
    setSelectedPage(getRandomLandingPage());
  }, []);

  useEffect(() => {
    // If authenticated, redirect to app
    if (!isLoading && isAuthenticated) {
      history.replace('/app');
      return;
    }
  }, [isAuthenticated, isLoading, history]);

  // Show loading while checking authentication or selecting page
  if (isLoading || selectedPage === null) {
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

  // Render appropriate landing page based on random selection
  switch (selectedPage) {
    case 1:
      return <LandingPage1 onGetStarted={handleGetStarted} />;
    case 2:
      return <LandingPageNeo onGetStarted={handleGetStarted} />;
    default:
      return <LandingPageNeo onGetStarted={handleGetStarted} />;
  }
};

export default LandingPageWrapper;

