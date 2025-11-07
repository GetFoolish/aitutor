import { motion } from 'framer-motion';
import { FaFire } from 'react-icons/fa';
import { useGame } from '../../contexts/GameContext';

interface StreakCounterProps {
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
}

export function StreakCounter({ size = 'medium', showLabel = true }: StreakCounterProps) {
  const { streakCount } = useGame();

  const sizeStyles = {
    small: {
      icon: 14,
      text: '14px',
      gap: 'var(--space-1)',
    },
    medium: {
      icon: 18,
      text: '16px',
      gap: 'var(--space-1)',
    },
    large: {
      icon: 24,
      text: '20px',
      gap: 'var(--space-2)',
    },
  };

  const styles = sizeStyles[size];

  // Determine flame color based on streak
  const getFlameColor = () => {
    if (streakCount === 0) return '#6b7280'; // gray
    if (streakCount < 3) return '#f59e0b'; // orange
    if (streakCount < 7) return '#ef4444'; // red
    return '#dc2626'; // deep red (hot streak!)
  };

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: styles.gap,
        padding: 'var(--space-1) var(--space-2)',
        background: streakCount > 0 ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
        borderRadius: 'var(--radius)',
        border: streakCount > 0 ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid var(--border)',
      }}
    >
      {/* Animated Flame */}
      <motion.div
        animate={
          streakCount > 0
            ? {
                scale: [1, 1.1, 1],
                rotate: [0, 5, -5, 0],
              }
            : {}
        }
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      >
        <FaFire color={getFlameColor()} size={styles.icon} />
      </motion.div>

      {/* Streak Count */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        <motion.span
          key={streakCount}
          initial={{ scale: 1.3, color: '#f59e0b' }}
          animate={{ scale: 1, color: 'var(--text-primary)' }}
          style={{
            fontSize: styles.text,
            fontWeight: 700,
            lineHeight: 1,
            color: 'var(--text-primary)',
          }}
        >
          {streakCount}
        </motion.span>
        {showLabel && (
          <span
            style={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              lineHeight: 1,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            {streakCount === 1 ? 'day' : 'days'}
          </span>
        )}
      </div>
    </motion.div>
  );
}
