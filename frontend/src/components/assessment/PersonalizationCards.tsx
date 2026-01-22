/**
 * Personalization Cards Animation Component
 * 
 * Displays 16-18 skill cards that enter from different directions, then shuffle/circle/wobble, and align into a grid.
 * Cards show skill names and grade levels (no mastery).
 * Uses neo-brutalist design with different colors for each card.
 */
import React, { useMemo, useState, useEffect, useRef } from 'react';
import BackgroundShapes from '../background-shapes/BackgroundShapes';

interface SkillCard {
  id: string;
  name: string;
  grade_level: string;
}

interface PersonalizationCardsProps {
  skills: SkillCard[];
  onComplete: () => void;
}

// Color palette for cards (neo-brutalist colors)
const CARD_COLORS = [
  '#FFD93D', // Yellow
  '#FF6B6B', // Red
  '#4ADE80', // Green
  '#6B9FFF', // Blue
  '#FF9F66', // Orange
  '#C084FC', // Purple
  '#60E5D4', // Cyan
  '#FBBF24', // Amber
  '#A78BFA', // Violet
  '#34D399', // Emerald
];

type AnimationPhase = 'entrance' | 'shuffle' | 'transition' | 'align';

const PersonalizationCards: React.FC<PersonalizationCardsProps> = ({ skills, onComplete }) => {
  const [cardPositions, setCardPositions] = useState<Array<{ x: number; y: number; rotation: number; scale: number }>>([]);
  const [animationPhase, setAnimationPhase] = useState<AnimationPhase>('entrance');
  const containerRef = useRef<HTMLDivElement>(null);
  const animationStartTime = useRef<number>(0);
  const finalPositions = useRef<Array<{ x: number; y: number; rotation: number; scale: number }>>([]);
  const entranceStartPositions = useRef<Array<{ x: number; y: number; rotation: number; scale: number }>>([]);
  const shuffleStartPositions = useRef<Array<{ x: number; y: number; rotation: number; scale: number }>>([]);
  const currentPositionsRef = useRef<Array<{ x: number; y: number; rotation: number; scale: number }>>([]);
  const isCompleteRef = useRef(false);
  const animationStartedRef = useRef(false);
  const phaseRef = useRef<AnimationPhase>('entrance');
  const centerXRef = useRef<number>(0);
  const centerYRef = useRef<number>(0);
  const containerWidthRef = useRef<number>(0);
  const containerHeightRef = useRef<number>(0);

  // Select up to 18 skills (or all if fewer) for a fuller grid
  const displaySkills = useMemo(
    () => skills.slice(0, Math.min(18, skills.length)),
    [skills]
  );
  const cardCount = displaySkills.length;

  // Initialize positions: entrance start positions, shuffle start positions, and final grid positions
  useEffect(() => {
    if (!containerRef.current || cardCount === 0) return;

    // Reset animation state when the skills set changes
    isCompleteRef.current = false;
    animationStartedRef.current = false;
    phaseRef.current = 'entrance';
    setAnimationPhase('entrance');

    const container = containerRef.current;
    // Get the actual container dimensions (including padding)
    const containerWidth = container.offsetWidth || window.innerWidth;
    const containerHeight = container.offsetHeight || window.innerHeight;
    
    // Store dimensions and center in refs for use in animation loop
    containerWidthRef.current = containerWidth;
    containerHeightRef.current = containerHeight;
    
    // Calculate true center of the container (accounting for padding box)
    const centerX = containerWidth / 2;
    const centerY = containerHeight / 2;
    centerXRef.current = centerX;
    centerYRef.current = centerY;

    // Card layout constants - larger cards for better presence
    const cardWidth = 220;
    const cardHeight = 170;
    const gap = 24;
    const topOffset = 100; // Space for title + breathing room

    // Calculate grid layout (3-4 columns for larger cards)
    const cols = cardCount <= 9 ? 3 : 4;
    const rows = Math.ceil(cardCount / cols);
    const totalWidth = cols * cardWidth + (cols - 1) * gap;
    const totalHeight = rows * cardHeight + (rows - 1) * gap;

    // Center the grid on screen (horizontally and vertically)
    // Account for title at top (40px) + some spacing (60px) = 100px offset
    const gridStartX = (containerWidth - totalWidth) / 2;
    const gridStartY = (containerHeight - totalHeight) / 2 + 60; // Offset down slightly to account for title

    // ENTRANCE: Cards start off-screen from different directions
    // Assign each card a direction: 0=left, 1=right, 2=top, 3=bottom
    const entrancePositions = displaySkills.map((_, index) => {
      const direction = index % 4;
      const offset = 600; // How far off-screen
      let x = 0, y = 0, rotation = 0;

      switch (direction) {
        case 0: // Left
          x = -offset;
          y = centerY + (Math.random() - 0.5) * 400 - cardHeight / 2;
          rotation = (Math.random() - 0.5) * 30;
          break;
        case 1: // Right
          x = containerWidth + offset;
          y = centerY + (Math.random() - 0.5) * 400 - cardHeight / 2;
          rotation = (Math.random() - 0.5) * 30;
          break;
        case 2: // Top
          x = centerX + (Math.random() - 0.5) * 400 - cardWidth / 2;
          y = -offset;
          rotation = (Math.random() - 0.5) * 30;
          break;
        case 3: // Bottom
          x = centerX + (Math.random() - 0.5) * 400 - cardWidth / 2;
          y = containerHeight + offset;
          rotation = (Math.random() - 0.5) * 30;
          break;
      }

      return { x, y, rotation, scale: 0.8 }; // Start slightly smaller
    });
    entranceStartPositions.current = entrancePositions;

    // SHUFFLE START: Cards converge to center in a circle for the shuffle/circle phase
    const shuffleRadius = Math.min(containerWidth, containerHeight) * 0.35;

    const shuffleStart = displaySkills.map((_, index) => {
      const angle = (index / Math.max(1, cardCount)) * Math.PI * 2;
      const rJitter = (Math.random() - 0.5) * 30;
      return {
        x: centerX + (shuffleRadius + rJitter) * Math.cos(angle) - cardWidth / 2,
        y: centerY + (shuffleRadius + rJitter) * Math.sin(angle) - cardHeight / 2,
        rotation: (Math.random() - 0.5) * 20,
        scale: 1.0,
      };
    });
    shuffleStartPositions.current = shuffleStart;

    // FINAL GRID: Calculate final grid positions, centering each row
    const final: Array<{ x: number; y: number; rotation: number; scale: number }> = [];
    for (let row = 0; row < rows; row++) {
      const rowStartIndex = row * cols;
      const remaining = cardCount - rowStartIndex;
      const rowCols = Math.min(cols, remaining);
      const rowWidth = rowCols * cardWidth + (rowCols - 1) * gap;
      const rowStartX = (containerWidth - rowWidth) / 2;
      const y = gridStartY + row * (cardHeight + gap);

      for (let col = 0; col < rowCols; col++) {
        final.push({
          x: rowStartX + col * (cardWidth + gap),
          y,
          rotation: 0,
          scale: 1.0,
        });
      }
    }
    finalPositions.current = final;

    // Start with entrance positions
    setCardPositions(entrancePositions);
    currentPositionsRef.current = entrancePositions;
    animationStartTime.current = Date.now();
  }, [cardCount, displaySkills]);

  // Update ref when positions change
  useEffect(() => {
    currentPositionsRef.current = cardPositions;
  }, [cardPositions]);

  // Animation loop: entrance → shuffle/circle/wobble → transition → align
  useEffect(() => {
    if (cardPositions.length === 0 || finalPositions.current.length === 0) return;
    if (animationStartTime.current === 0) return;
    if (animationStartedRef.current) return; // Prevent multiple starts

    let animationId: number;
    isCompleteRef.current = false;
    animationStartedRef.current = true;

    const animate = () => {
      if (isCompleteRef.current) return;

      const elapsed = Date.now() - animationStartTime.current;
      const totalDuration = 5000; // 5 seconds total (reduced from 6)
      const entranceDuration = 700; // 0-14%: cards fly in from edges
      const shuffleDuration = 2800; // 14-70%: shuffle/circle/wobble
      const transitionDuration = 700; // 70-84%: transition to grid
      const alignDuration = 800; // 84-100%: final alignment with bounce

      const cardWidth = 220;
      const cardHeight = 170;

      if (elapsed < entranceDuration) {
        // Phase 1: ENTRANCE - Cards fly in from different directions with stagger
        if (phaseRef.current !== 'entrance') {
          phaseRef.current = 'entrance';
          setAnimationPhase('entrance');
        }
        const progress = elapsed / entranceDuration;

        const newPositions = entranceStartPositions.current.map((start, index) => {
          const shuffleStart = shuffleStartPositions.current[index];
          // Staggered entrance: each card starts slightly after the previous
          const staggerDelay = (index / Math.max(1, cardCount)) * 0.3; // 30% of duration spread
          const adjustedProgress = Math.max(0, Math.min(1, (progress - staggerDelay) / (1 - staggerDelay)));
          // Ease-out for smooth deceleration with extra bounce
          const eased = 1 - Math.pow(1 - adjustedProgress, 3);

          return {
            x: start.x + (shuffleStart.x - start.x) * eased,
            y: start.y + (shuffleStart.y - start.y) * eased,
            rotation: start.rotation + (shuffleStart.rotation - start.rotation) * eased,
            scale: start.scale + (shuffleStart.scale - start.scale) * eased,
          };
        });
        setCardPositions(newPositions);
        animationId = requestAnimationFrame(animate);
      } else if (elapsed < entranceDuration + shuffleDuration) {
        // Phase 2: SHUFFLE/CIRCLE/WOBBLE - Mix of orbiting, shuffling, wobbling, and scaling
        if (phaseRef.current !== 'shuffle') {
          phaseRef.current = 'shuffle';
          setAnimationPhase('shuffle');
        }
        const t = (elapsed - entranceDuration) / 1000; // seconds since shuffle started
        // Use stored center coordinates for consistency
        const centerX = centerXRef.current;
        const centerY = centerYRef.current;
        const baseRadius = Math.min(containerWidthRef.current, containerHeightRef.current) * 0.35;
        const orbitSpeed = 0.7; // radians / second (faster for more dynamic feel)

        const newPositions = shuffleStartPositions.current.map((shuffleStart, index) => {
          // Base angle for orbiting
          const baseAngle = (index / Math.max(1, cardCount)) * Math.PI * 2;
          const angle = baseAngle + t * orbitSpeed;

          // Wobble/jitter for shuffling effect - increased amplitude
          const wobbleX = Math.sin(t * 2.5 + index * 0.8) * 25;
          const wobbleY = Math.cos(t * 2.1 + index * 0.9) * 25;
          const wobbleRot = Math.sin(t * 2.8 + index * 0.7) * 15;

          // Radius pulse for circling effect - increased amplitude
          const rPulse = Math.sin(t * 1.4 + index * 0.6) * 40;

          // Shuffle effect: occasional larger random movements - increased amplitude
          const shuffleX = Math.sin(t * 0.3 + index * 1.2) * 45;
          const shuffleY = Math.cos(t * 0.35 + index * 1.1) * 45;

          // Scale wobble: cards grow and shrink slightly
          const scaleWobble = 1.0 + Math.sin(t * 3 + index * 0.5) * 0.08; // ±8% scale variation

          return {
            x: centerX + (baseRadius + rPulse) * Math.cos(angle) - cardWidth / 2 + wobbleX + shuffleX,
            y: centerY + (baseRadius + rPulse) * Math.sin(angle) - cardHeight / 2 + wobbleY + shuffleY,
            rotation: shuffleStart.rotation + wobbleRot,
            scale: scaleWobble,
          };
        });
        setCardPositions(newPositions);
        animationId = requestAnimationFrame(animate);
      } else if (elapsed < entranceDuration + shuffleDuration + transitionDuration) {
        // Phase 3: TRANSITION - Move toward grid positions
        if (phaseRef.current !== 'transition') {
          phaseRef.current = 'transition';
          setAnimationPhase('transition');
        }
        const transitionProgress = (elapsed - entranceDuration - shuffleDuration) / transitionDuration;
        // Ease-in-out for smooth transition
        const eased = transitionProgress < 0.5
          ? 2 * transitionProgress * transitionProgress
          : 1 - Math.pow(-2 * transitionProgress + 2, 2) / 2;

        const currentPos = currentPositionsRef.current;
        const newPositions = currentPos.map((pos, index) => {
          const final = finalPositions.current[index];
          return {
            x: pos.x + (final.x - pos.x) * eased * 0.65, // Partial movement
            y: pos.y + (final.y - pos.y) * eased * 0.65,
            rotation: pos.rotation + (final.rotation - pos.rotation) * eased * 0.65,
            scale: pos.scale + (final.scale - pos.scale) * eased * 0.65,
          };
        });
        setCardPositions(newPositions);
        animationId = requestAnimationFrame(animate);
      } else if (elapsed < totalDuration) {
        // Phase 4: ALIGN - Final snap to grid with bounce effect
        if (phaseRef.current !== 'align') {
          phaseRef.current = 'align';
          setAnimationPhase('align');
        }
        const alignProgress = (elapsed - entranceDuration - shuffleDuration - transitionDuration) / alignDuration;
        // Bounce easing: overshoot then settle
        const eased = alignProgress < 0.5
          ? 4 * alignProgress * alignProgress * alignProgress
          : 1 - Math.pow(-2 * alignProgress + 2, 3) / 2;

        // Add subtle bounce overshoot
        const bounce = alignProgress < 0.7 ? Math.sin(alignProgress * Math.PI * 2.5) * 0.03 * (1 - alignProgress) : 0;

        const currentPos = currentPositionsRef.current;
        const newPositions = currentPos.map((pos, index) => {
          const final = finalPositions.current[index];
          return {
            x: pos.x + (final.x - pos.x) * eased,
            y: pos.y + (final.y - pos.y) * eased,
            rotation: pos.rotation + (final.rotation - pos.rotation) * eased,
            scale: (pos.scale + (final.scale - pos.scale) * eased) * (1 + bounce),
          };
        });
        setCardPositions(newPositions);
        animationId = requestAnimationFrame(animate);
      } else {
        // Animation complete
        setCardPositions(finalPositions.current);
        if (phaseRef.current !== 'align') {
          phaseRef.current = 'align';
          setAnimationPhase('align');
        }
        isCompleteRef.current = true;
        setTimeout(() => {
          onComplete();
        }, 400);
        return;
      }
    };

    animationId = requestAnimationFrame(animate);
    return () => {
      isCompleteRef.current = true;
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [cardPositions.length, cardCount, onComplete]);

  // Format grade level for display
  const formatGradeLevel = (grade: string): string => {
    if (grade === 'K') return 'K';
    return grade.replace('GRADE_', 'Grade ');
  };

  return (
    <div
      ref={containerRef}
      className="question-panel"
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        minHeight: '600px',
        overflow: 'hidden',
        backgroundColor: 'var(--neo-bg)',
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='1.5' fill='%23000000' opacity='0.50'/%3E%3C/svg%3E\")",
        backgroundSize: '20px 20px',
        backgroundRepeat: 'repeat',
        padding: '40px 20px',
      }}
    >
      <BackgroundShapes count={18} />
      {/* Title */}
      <div style={{
        position: 'absolute',
        top: '40px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 10,
        textAlign: 'center',
      }}>
        <h2 style={{
          fontSize: '28px',
          fontWeight: 900,
          color: '#000000',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          margin: 0,
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}>
          Personalizing Your Learning Plan...
        </h2>
      </div>

      {/* Cards */}
      {displaySkills.map((skill, index) => {
        const pos = cardPositions[index] || { x: 0, y: 0, rotation: 0, scale: 1 };
        const color = CARD_COLORS[index % CARD_COLORS.length];

        return (
          <div
            key={skill.id}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: '220px',
              height: '170px',
              border: '4px solid #000000',
              backgroundColor: color,
              boxShadow: '4px 4px 0px 0px #000000',
              padding: '16px',
              transform: `translate(${pos.x}px, ${pos.y}px) rotate(${pos.rotation}deg) scale(${pos.scale})`,
              transition: animationPhase === 'align' ? 'transform 0.2s ease-out' : 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              willChange: 'transform',
              overflow: 'hidden',
            }}
          >
            {/* Grade Level Badge */}
            <div style={{
              alignSelf: 'flex-start',
              padding: '4px 8px',
              border: '2px solid #000000',
              backgroundColor: '#FFFFFF',
              fontSize: '11px',
              fontWeight: 900,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: '#000000',
            }}>
              {formatGradeLevel(skill.grade_level)}
            </div>

            {/* Skill Name */}
            <div style={{
              fontSize: '15px',
              fontWeight: 700,
              color: '#000000',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              lineHeight: '1.3',
              wordBreak: 'break-word',
              textAlign: 'center',
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '8px 4px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {skill.name}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default PersonalizationCards;
