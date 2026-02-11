import React, { createContext, useContext, useState, ReactNode } from 'react';

interface HintContextType {
  showHints: boolean;
  toggleHints: () => void;
  setShowHints: (show: boolean) => void;
  currentHintIndex: number;
  setCurrentHintIndex: (index: number) => void;
  totalHints: number;
  setTotalHints: (count: number) => void;
  responsiveHint: string | null;
  setResponsiveHint: (hint: string | null) => void;
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
  const [responsiveHint, setResponsiveHint] = useState<string | null>(null);

  const toggleHints = () => {
    setShowHints(prev => !prev);
    if (!showHints) {
      setCurrentHintIndex(0);
    }
  };

  return (
    <HintContext.Provider
      value={{
        showHints,
        toggleHints,
        setShowHints,
        currentHintIndex,
        setCurrentHintIndex,
        totalHints,
        setTotalHints,
        responsiveHint,
        setResponsiveHint,
      }}
    >
      {children}
    </HintContext.Provider>
  );
};
