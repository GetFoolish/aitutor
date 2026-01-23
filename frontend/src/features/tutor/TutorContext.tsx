/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { createContext, FC, ReactNode, useContext } from "react";
import { useTutor, UseTutorResults } from "./use-tutor";

const TutorContext = createContext<UseTutorResults | undefined>(undefined);

export type TutorProviderProps = {
  children: ReactNode;
  assessmentMode?: boolean;
};

export const TutorProvider: FC<TutorProviderProps> = ({ children, assessmentMode }) => {
  const tutor = useTutor(assessmentMode);

  // Debug helper: expose tutor client to window for console testing
  if (typeof window !== 'undefined' && !(window as any)._tutorDebugInitialized) {
    (window as any)._tutorDebugInitialized = true;
    console.log('[TutorDebug] Available! Use window.tutorDebug.send("your message") to send text');
  }
  if (typeof window !== 'undefined') {
    (window as any).tutorDebug = {
      client: tutor.client,
      connected: tutor.connected,
      send: (text: string) => {
        if (tutor.client && tutor.connected) {
          tutor.client.send({ text });
          console.log('[TutorDebug] Sent:', text);
        } else {
          console.error('[TutorDebug] Not connected. Start a session first.');
        }
      },
      status: () => tutor.client?.status || 'no client',
    };
  }

  return (
    <TutorContext.Provider value={tutor}>
      {children}
    </TutorContext.Provider>
  );
};

export const useTutorContext = () => {
  const context = useContext(TutorContext);
  if (!context) {
    throw new Error("useTutorContext must be used within a TutorProvider");
  }
  return context;
};

/**
 * Optional tutor context hook.
 * Returns undefined when not wrapped in TutorProvider (useful for pages where tutor is not mounted).
 */
export const useOptionalTutorContext = () => {
  return useContext(TutorContext);
};

// Export aliases for backward compatibility during migration
export { TutorProvider as LiveAPIProvider };
export { useTutorContext as useLiveAPIContext };
