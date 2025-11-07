import { motion } from 'framer-motion';
import { FaTrophy } from 'react-icons/fa';
import { useGame } from '../../contexts/GameContext';

interface LevelBadgeProps {
  size?: 'small' | 'medium' | 'large';
  showIcon?: boolean;
}

export function LevelBadge({ size = 'medium', showIcon = true }: LevelBadgeProps) {
  const { level } = useGame();

  const sizeStyles = {
    small: {
      badge: '28px',
      text: '13px',
      icon: 12,
    },
    medium: {
      badge: '36px',
      text: '16px',
      icon: 14,
    },
    large: {
      badge: '48px',
      text: '20px',
      icon: 18,
    },
  };

  const styles = sizeStyles[size];

  // Badge color based on level milestones
  const getBadgeColor = () => {
    if (level < 5) return { bg: '#854d0e', border: '#fbbf24', text: '#fbbf24' }; // Bronze
    if (level < 10) return { bg: '#71717a', border: '#d4d4d8', text: '#d4d4d8' }; // Silver
    if (level < 20) return { bg: '#854d0e', border: '#fbbf24', text: '#fde047' }; // Gold
    return { bg: '#581c87', border: '#a78bfa', text: '#c4b5fd' }; // Purple (Master)
  };

  const colors = getBadgeColor();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
      {showIcon && <FaTrophy color={colors.border} size={styles.icon} />}

      <motion.div
        key={level}
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 15 }}
        style={{
          width: styles.badge,
          height: styles.badge,
          borderRadius: '50%',
          background: colors.bg,
          border: `2px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: styles.text,
          color: colors.text,
          boxShadow: `0 0 12px ${colors.border}40`,
        }}
      >
        {level}
      </motion.div>
    </div>
  );
}
