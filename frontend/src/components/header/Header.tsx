import { useState } from 'react';
import { FaCoins, FaSignOutAlt, FaUser, FaCog, FaPlus, FaSun, FaMoon } from 'react-icons/fa';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useGame } from '../../contexts/GameContext';
import { CreditsPurchaseModal } from '../credits/CreditsPurchaseModal';
import { XPDisplay } from '../gamification/XPDisplay';
import { StreakCounter } from '../gamification/StreakCounter';
import { LevelBadge } from '../gamification/LevelBadge';
import { useHistory } from 'react-router-dom';

export function Header() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const history = useHistory();

  return (
    <>
      <header className="header">
        <h1 style={{
          margin: 0,
          fontSize: '14px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
          color: '#1E1E1E'
        }}>
          AI TUTOR
        </h1>

        {user && (
          <>
            {/* Gamification Stats */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '24px',
              marginLeft: 'auto',
              marginRight: '24px',
            }}>
              <LevelBadge size="small" />
              <StreakCounter size="small" showLabel={false} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <XPDisplay showProgress={false} size="small" />
              </div>
            </div>

            <div className="header-right">
            {/* Credits Display */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              background: '#FFFBEB',
              borderRadius: '8px',
              border: '1px solid #FEF3C7'
            }}>
              <FaCoins size={14} style={{ color: '#F59E0B' }} />
              <span style={{
                fontSize: '14px',
                fontWeight: 600,
                color: '#92400E',
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
              }}>
                {user.credits}
              </span>
            </div>

            {/* Theme Toggle Button */}
            <button
              className="btn"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              style={{ padding: 'var(--space-1) var(--space-2)', fontSize: '13px' }}
            >
              {theme === 'dark' ? <FaSun size={14} /> : <FaMoon size={14} />}
            </button>

            {/* Buy Credits Button */}
            <button
              className="btn btn--primary"
              onClick={() => setIsModalOpen(true)}
              style={{
                background: '#6366F1',
                color: '#FFFFFF',
                fontSize: '14px',
                padding: '8px 16px',
                fontWeight: 600,
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(99, 102, 241, 0.2)',
                transition: 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)',
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#4F46E5';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(99, 102, 241, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#6366F1';
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(99, 102, 241, 0.2)';
              }}
            >
              <FaPlus size={12} />
              <span>Buy Credits</span>
            </button>

            {/* User Profile Menu */}
            <div style={{ position: 'relative' }}>
              {/* Avatar Button */}
              <button
                className="avatar"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                aria-label="User menu"
              >
                {user.name ? user.name[0].toUpperCase() : 'U'}
              </button>

              {/* Dropdown Menu */}
              {isMenuOpen && (
                <div
                  style={{
                    position: 'absolute',
                    top: 'var(--space-6)',
                    right: 0,
                    background: 'var(--panel)',
                    border: '1px solid #1e2a3a',
                    borderRadius: 'var(--radius)',
                    minWidth: '200px',
                    boxShadow: 'var(--shadow)',
                    zIndex: 1000
                  }}
                >
                  {/* User Info */}
                  <div style={{ padding: 'var(--space-2)', borderBottom: '1px solid #1e2a3a' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: '14px' }}>
                      {user.name}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: 'var(--space-1)' }}>
                      {user.email}
                    </div>
                    {user.account_type && (
                      <div
                        style={{
                          marginTop: 'var(--space-1)',
                          display: 'inline-block',
                          padding: '2px var(--space-1)',
                          background: '#854d0e',
                          color: '#fbbf24',
                          borderRadius: '999px',
                          fontSize: '11px',
                          fontWeight: 500
                        }}
                      >
                        {user.account_type}
                      </div>
                    )}
                  </div>

                  {/* Menu Items */}
                  <div style={{ padding: 'var(--space-1) 0' }}>
                    {/* Profile Button */}
                    <button
                      className="btn btn--ghost"
                      onClick={() => {
                        setIsMenuOpen(false);
                        history.push('/profile');
                      }}
                      style={{
                        width: '100%',
                        justifyContent: 'flex-start',
                        borderRadius: 0,
                        border: 'none',
                        fontSize: '13px',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(245, 158, 11, 0.1)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <FaUser size={12} />
                      <span>Profile</span>
                    </button>

                    {/* Settings Button */}
                    <button
                      className="btn btn--ghost"
                      onClick={() => {
                        setIsMenuOpen(false);
                        history.push('/settings');
                      }}
                      style={{
                        width: '100%',
                        justifyContent: 'flex-start',
                        borderRadius: 0,
                        border: 'none',
                        fontSize: '13px',
                        transition: 'background 0.15s ease'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(245, 158, 11, 0.1)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <FaCog size={12} />
                      <span>Settings</span>
                    </button>

                    {/* Separator */}
                    <div style={{ height: '1px', background: '#1e2a3a', margin: 'var(--space-1) 0' }}></div>

                    {/* Logout Button */}
                    <button
                      className="btn btn--ghost"
                      onClick={() => {
                        setIsMenuOpen(false);
                        logout();
                      }}
                      style={{
                        width: '100%',
                        justifyContent: 'flex-start',
                        borderRadius: 0,
                        border: 'none',
                        color: '#ff6868',
                        fontSize: '13px'
                      }}
                    >
                      <FaSignOutAlt size={12} />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
          </>
        )}
      </header>

      <CreditsPurchaseModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </>
  );
}
