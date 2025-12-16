/**
 * Dynamic Landing Page Component
 * Handles /landing/:id routes with validation
 * Shows specific landing pages or 404 for invalid IDs
 */
import React from 'react';
import { useParams, useHistory } from 'react-router-dom';
import LandingPage1 from './LandingPage1';
import LandingPageNeo from './LandingPageNeo';

const DynamicLandingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const history = useHistory();
  const pageId = parseInt(id, 10);

  const handleGetStarted = () => {
    history.push('/app/login');
  };

  // Validate page ID (only pages 1-2 exist)
  if (isNaN(pageId) || pageId < 1 || pageId > 2) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: '#FFFDF5',
        textAlign: 'center',
        padding: '20px'
      }}>
        <h1 style={{
          fontSize: '64px',
          fontWeight: 900,
          marginBottom: '24px',
          border: '5px solid #000000',
          padding: '20px 60px',
          background: '#FF006E',
          color: '#FFFFFF',
          boxShadow: '4px 4px 0 #000000'
        }}>404</h1>
        <p style={{ 
          fontSize: '20px', 
          fontWeight: 700, 
          marginBottom: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          Landing Page Not Found
        </p>
        <p style={{ 
          fontSize: '14px', 
          fontWeight: 600, 
          marginBottom: '32px',
          color: '#666'
        }}>
          Landing page {id} does not exist. Please use page 1 or 2.
        </p>
        <button
          onClick={() => history.push('/')}
          style={{
            padding: '14px 40px',
            border: '4px solid #000000',
            background: '#FFD93D',
            cursor: 'pointer',
            fontWeight: 900,
            textTransform: 'uppercase',
            fontSize: '14px',
            boxShadow: '3px 3px 0 #000000',
            transition: 'all 0.1s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translate(1px, 1px)';
            e.currentTarget.style.boxShadow = '2px 2px 0 #000000';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translate(0, 0)';
            e.currentTarget.style.boxShadow = '3px 3px 0 #000000';
          }}
        >
          Go to Home
        </button>
      </div>
    );
  }

  // Render appropriate landing page
  switch (pageId) {
    case 1:
      return <LandingPage1 onGetStarted={handleGetStarted} />;
    case 2:
      return <LandingPageNeo onGetStarted={handleGetStarted} />;
    default:
      return <LandingPageNeo onGetStarted={handleGetStarted} />;
  }
};

export default DynamicLandingPage;
