import React, { createContext, useContext, useState, ReactNode, useCallback, useMemo } from 'react';

interface HintContextType {
  showHints: boolean;
  toggleHints: () => void;
  setShowHints: (show: boolean) => void;
  currentHintIndex: number;
  setCurrentHintIndex: (index: number) => void;
  totalHints: number;
  setTotalHints: (count: number) => void;
  resetHints: () => void;
}

const HintContext = createContext<HintContextType | undefined>(undefined);

export const useHint = () => {
  const context = useContext(HintContext);
  if (!context) {
    throw new Error('useHint must be used within a HintProvider');
  }
  return context;
};

interface HintProviderProps {
  children: ReactNode;
}

export const HintProvider: React.FC<HintProviderProps> = ({ children }) => {
  const [showHints, setShowHints] = useState(false);
  const [currentHintIndex, setCurrentHintIndex] = useState(0);
  const [totalHints, setTotalHints] = useState(0);

  const toggleHints = useCallback(() => {
    setShowHints(prev => {
      if (!prev) {
        setCurrentHintIndex(0);
      }
      return !prev;
    });
  }, []);

  const resetHints = useCallback(() => {
    setShowHints(false);
    setCurrentHintIndex(0);
  }, []);

  const contextValue = useMemo(() => ({
    showHints,
    toggleHints,
    setShowHints,
    currentHintIndex,
    setCurrentHintIndex,
    totalHints,
    setTotalHints,
    resetHints,
  }), [showHints, currentHintIndex, totalHints, toggleHints, resetHints]);

  return (
    <HintContext.Provider value={contextValue}>
      {children}
    </HintContext.Provider>
  );
};
