import { useEffect, useState } from 'react';
import { FaStar } from 'react-icons/fa';
import { useGame } from '../../contexts/GameContext';
import { motion, AnimatePresence } from 'framer-motion';

interface XPDisplayProps {
  showProgress?: boolean;
  size?: 'small' | 'medium' | 'large';
}

export function XPDisplay({ showProgress = true, size = 'medium' }: XPDisplayProps) {
  const { xp, xpInCurrentLevel, xpToNextLevel } = useGame();
  const [displayXP, setDisplayXP] = useState(xp);

  // Animate XP counter when it changes
  useEffect(() => {
    const duration = 500; // ms
    const steps = 30;
    const increment = (xp - displayXP) / steps;
    const stepDuration = duration / steps;

    let currentStep = 0;
    const timer = setInterval(() => {
      currentStep++;
      if (currentStep >= steps) {
        setDisplayXP(xp);
        clearInterval(timer);
      } else {
        setDisplayXP((prev) => Math.round(prev + increment));
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [xp]);

  const progress = xpToNextLevel > 0 ? (xpInCurrentLevel / xpToNextLevel) * 100 : 0;

  const sizeStyles = {
    small: {
      container: 'gap-1',
      icon: 14,
      text: 'text-sm',
      bar: 'h-1',
    },
    medium: {
      container: 'gap-2',
      icon: 16,
      text: 'text-base',
      bar: 'h-2',
    },
    large: {
      container: 'gap-2',
      icon: 20,
      text: 'text-lg',
      bar: 'h-3',
    },
  };

  const styles = sizeStyles[size];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      {/* XP Display */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: styles.container === 'gap-1' ? 'var(--space-1)' : 'var(--space-2)',
        }}
      >
        <FaStar color="#fbbf24" size={styles.icon} />
        <motion.span
          key={displayXP}
          initial={{ scale: 1.2, color: '#fbbf24' }}
          animate={{ scale: 1, color: 'var(--text-primary)' }}
          style={{
            fontSize: styles.text === 'text-sm' ? '14px' : styles.text === 'text-base' ? '16px' : '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
          }}
        >
          {displayXP.toLocaleString()} XP
        </motion.span>
      </div>

      {/* Progress Bar */}
      {showProgress && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div
            style={{
              width: '100%',
              backgroundColor: 'var(--border)',
              borderRadius: '999px',
              overflow: 'hidden',
              height: styles.bar === 'h-1' ? '4px' : styles.bar === 'h-2' ? '8px' : '12px',
            }}
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              style={{
                height: '100%',
                background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
                borderRadius: '999px',
              }}
            />
          </div>

          <div
            style={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              textAlign: 'right',
            }}
          >
            {xpInCurrentLevel} / {xpToNextLevel} to next level
          </div>
        </div>
      )}
    </div>
  );
}
