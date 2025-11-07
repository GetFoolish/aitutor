import { motion } from 'framer-motion';
import { FaCheck } from 'react-icons/fa';
import { useGame } from '../../contexts/GameContext';

interface DailyGoalRingProps {
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
}

export function DailyGoalRing({ size = 48, strokeWidth = 4, showLabel = true }: DailyGoalRingProps) {
  const { sessionXp, dailyGoalXp, dailyProgress } = useGame();

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - dailyProgress * circumference;

  const isComplete = dailyProgress >= 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-1)' }}>
      {/* SVG Ring */}
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth={strokeWidth}
          />

          {/* Progress circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={isComplete ? '#6EDC82' : '#fbbf24'}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </svg>

        {/* Center content */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {isComplete ? (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 15 }}
            >
              <FaCheck color="#6EDC82" size={size / 3} />
            </motion.div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: size / 4,
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  lineHeight: 1,
                }}
              >
                {Math.round(dailyProgress * 100)}%
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Label */}
      {showLabel && (
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Daily Goal
          </div>
          <div
            style={{
              fontSize: '12px',
              color: isComplete ? '#6EDC82' : 'var(--text-primary)',
              fontWeight: 600,
            }}
          >
            {sessionXp} / {dailyGoalXp} XP
          </div>
        </div>
      )}
    </div>
  );
}
