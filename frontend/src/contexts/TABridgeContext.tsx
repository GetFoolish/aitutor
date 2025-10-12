/**
 * Teaching Assistant Bridge Context
 *
 * Provides access to the TA Bridge throughout the app
 */

import { createContext, FC, ReactNode, useContext, useRef, useEffect, useState } from "react";
import { TeachingAssistantBridge } from "../lib/teaching-assistant-bridge";
import { useLiveAPIContext } from "./LiveAPIContext";

interface TABridgeContextType {
  taBridge: TeachingAssistantBridge | null;
  isConnected: boolean;
}

const TABridgeContext = createContext<TABridgeContextType | undefined>(undefined);

export interface TABridgeProviderProps {
  children: ReactNode;
}

export const TABridgeProvider: FC<TABridgeProviderProps> = ({ children }) => {
  const { client } = useLiveAPIContext();
  const taBridgeRef = useRef<TeachingAssistantBridge | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    console.log("[TABridgeContext] Initializing Teaching Assistant Bridge...");
    const taBridge = new TeachingAssistantBridge("ws://localhost:9000", "Student");
    taBridgeRef.current = taBridge;

    // Connect to TA
    taBridge.connect().then((success) => {
      if (success) {
        console.log("[TABridgeContext] TA Bridge connected successfully");
        setIsConnected(true);
        // Attach to Gemini client
        taBridge.attachToGeminiClient(client);
      } else {
        console.error("[TABridgeContext] Failed to connect TA Bridge");
        setIsConnected(false);
      }
    });

    // Cleanup on unmount
    return () => {
      console.log("[TABridgeContext] Disconnecting TA Bridge");
      taBridge.disconnect();
    };
  }, [client]);

  return (
    <TABridgeContext.Provider value={{ taBridge: taBridgeRef.current, isConnected }}>
      {children}
    </TABridgeContext.Provider>
  );
};

export const useTABridge = () => {
  const context = useContext(TABridgeContext);
  if (!context) {
    throw new Error("useTABridge must be used within a TABridgeProvider");
  }
  return context;
};
