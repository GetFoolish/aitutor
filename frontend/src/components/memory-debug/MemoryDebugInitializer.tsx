/**
 * MemoryDebugInitializer - Initializes memory debug functions for console testing
 *
 * This component should be placed inside AuthGuard to have access to the auth token.
 * It exposes window.memoryDebug for testing the Cognitive Memory Pipeline from
 * the browser console.
 *
 * Usage (in browser console):
 *   window.memoryDebug.testMemoryPipeline()  - Run all tests
 *   window.memoryDebug.getBiography()        - Get student biography
 *   window.memoryDebug.searchMemories("...")  - Search memories
 *   window.memoryDebug.getConfig()           - Get system config
 */

import { useMemoryDebug } from '../../hooks/useMemoryDebug';

export function MemoryDebugInitializer() {
  // This hook sets up window.memoryDebug when mounted
  useMemoryDebug();

  // This component renders nothing - it just initializes the debug functions
  return null;
}

export default MemoryDebugInitializer;
