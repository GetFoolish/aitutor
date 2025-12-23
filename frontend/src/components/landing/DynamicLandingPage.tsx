/**
 * Dynamic Landing Page Component
 * Handles /landing/:id routes with validation
 * Shows specific landing pages or 404 for invalid IDs
 */
import React from 'react';
import { useParams, useHistory } from 'react-router-dom';
import LandingPage1 from './LandingPage1';
import LandingPageNeo from './LandingPage2';

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
      <div className="flex flex-col justify-center items-center h-screen bg-[#FFFDF5] text-center p-5">
        <h1 className="text-6xl font-black mb-6 border-[5px] border-black py-5 px-16 bg-[#FF006E] text-white shadow-[4px_4px_0_0_#000]">
          404
        </h1>
        <p className="text-xl font-bold mb-3 uppercase tracking-widest text-black">
          Landing Page Not Found
        </p>
        <p className="text-sm font-semibold mb-8 text-[#666]">
          Landing page {id} does not exist. Please use page 1 or 2.
        </p>
        <button
          onClick={() => history.push('/')}
          className="px-10 py-3.5 border-4 border-black bg-[#FFD93D] cursor-pointer font-black uppercase text-sm shadow-[3px_3px_0_0_#000] transition-all duration-100 hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0_0_#000]"
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
