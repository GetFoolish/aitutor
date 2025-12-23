/**
 * Coming Soon Page
 * Blocks access to the entire application
 */
import React from 'react';
import TeachrLogo from '../landing/TeachrLogo';
import './ComingSoon.scss';

const ComingSoon: React.FC = () => {
  return (
    <div className="coming-soon-page">
      <div className="coming-soon-container">
        {/* Header */}
        <header className="coming-soon-header">
          <TeachrLogo size="medium" />
        </header>

        {/* Main Content */}
        <section className="coming-soon-hero">
          <div className="coming-soon-content">
            <div className="coming-soon-badge">
              We're Building Something Amazing
            </div>
            <h1 className="coming-soon-title">
              Coming Soon
            </h1>
            <p className="coming-soon-subtitle">
              We're working hard to bring you an incredible learning experience.
              Stay tuned for updates!
            </p>

            {/* Decorative Elements */}
            <div className="coming-soon-decoration">
              <div className="decoration-box decoration-box-1"></div>
              <div className="decoration-box decoration-box-2"></div>
              <div className="decoration-box decoration-box-3"></div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="coming-soon-footer">
          <p className="text-sm font-bold text-black uppercase tracking-wider">
            Thank you for your patience
          </p>
        </footer>
      </div>
    </div>
  );
};

export default ComingSoon;
