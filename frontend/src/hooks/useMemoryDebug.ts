/**
 * Memory Debug Hook - Console logging for Cognitive Memory Pipeline testing
 *
 * This hook provides functions to test and debug the v5 Cognitive Memory Pipeline:
 * - Biography retrieval and display
 * - Memory search and retrieval
 * - Memory extraction from conversations
 * - System configuration status
 *
 * All operations log detailed information to the browser console for debugging.
 *
 * Usage:
 *   const {
 *     getBiography,
 *     searchMemories,
 *     getMemoryStats,
 *     getConfig,
 *     testMemoryPipeline
 *   } = useMemoryDebug();
 *
 * Then call in browser console:
 *   window.memoryDebug.getBiography()
 *   window.memoryDebug.searchMemories("basketball")
 *   window.memoryDebug.testMemoryPipeline()
 */

import { useCallback, useEffect, useRef } from 'react';
import { jwtUtils } from '../lib/jwt-utils';

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

// Console styling for better readability
const styles = {
  header: 'background: #4a90d9; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;',
  success: 'background: #2ecc71; color: white; padding: 2px 6px; border-radius: 2px;',
  error: 'background: #e74c3c; color: white; padding: 2px 6px; border-radius: 2px;',
  info: 'background: #3498db; color: white; padding: 2px 6px; border-radius: 2px;',
  warning: 'background: #f39c12; color: white; padding: 2px 6px; border-radius: 2px;',
  biography: 'background: #9b59b6; color: white; padding: 2px 6px; border-radius: 2px;',
  memory: 'background: #1abc9c; color: white; padding: 2px 6px; border-radius: 2px;',
};

interface MemorySearchResult {
  text: string;
  type: string;
  importance: number;
  score: number;
  timestamp: string;
}

interface BiographyResponse {
  user_id: string;
  biography: string;
  has_biography: boolean;
}

interface MemoryStatsResponse {
  enabled: boolean;
  total_memories?: number;
  by_type?: Record<string, number>;
  error?: string;
}

interface ConfigResponse {
  config: {
    llm_provider: string;
    has_gemini: boolean;
    has_openai: boolean;
    has_pinecone: boolean;
    has_mongodb: boolean;
    enable_biographer: boolean;
    enable_memory_extraction: boolean;
    enable_semantic_search: boolean;
    enable_skills: boolean;
  };
  validation: string[];
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = jwtUtils.getToken();
  if (!token) {
    throw new Error('No auth token found. Please log in first.');
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export function useMemoryDebug() {
  const debugRef = useRef<{
    getBiography: () => Promise<BiographyResponse | null>;
    searchMemories: (query: string, topK?: number) => Promise<MemorySearchResult[]>;
    getMemoryStats: () => Promise<MemoryStatsResponse | null>;
    getConfig: () => Promise<ConfigResponse | null>;
    testMemoryPipeline: () => Promise<void>;
    extractMemories: (exchanges: Array<{student: string, tutor: string}>) => Promise<any>;
  }>();

  const getBiography = useCallback(async (): Promise<BiographyResponse | null> => {
    console.log('%c[MEMORY DEBUG] Fetching Biography...', styles.header);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/student/biography`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: BiographyResponse = await response.json();

      console.log('%c[BIOGRAPHY]', styles.biography, 'Retrieved successfully');
      console.log('User ID:', data.user_id);
      console.log('Has Biography:', data.has_biography);

      if (data.biography) {
        console.log('%c--- BIOGRAPHY TEXT ---', styles.biography);
        console.log(data.biography);
        console.log('%c--- END BIOGRAPHY ---', styles.biography);
      } else {
        console.log('%c[INFO]', styles.warning, 'No biography exists yet. Complete some sessions to generate one.');
      }

      return data;
    } catch (error) {
      console.log('%c[ERROR]', styles.error, 'Failed to fetch biography:', error);
      return null;
    }
  }, []);

  const searchMemories = useCallback(async (
    query: string,
    topK: number = 10
  ): Promise<MemorySearchResult[]> => {
    console.log('%c[MEMORY DEBUG] Searching Memories...', styles.header);
    console.log('Query:', query);
    console.log('Top K:', topK);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/search`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ query, top_k: topK }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      console.log('%c[MEMORY SEARCH]', styles.memory, `Found ${data.results?.length || 0} memories`);

      if (data.results && data.results.length > 0) {
        console.table(data.results.map((r: MemorySearchResult, i: number) => ({
          '#': i + 1,
          type: r.type,
          importance: r.importance?.toFixed(2),
          score: r.score?.toFixed(3),
          text: r.text?.substring(0, 60) + (r.text?.length > 60 ? '...' : ''),
        })));

        console.log('%c--- FULL MEMORY TEXTS ---', styles.memory);
        data.results.forEach((r: MemorySearchResult, i: number) => {
          console.log(`[${i + 1}] (${r.type}, importance: ${r.importance}) ${r.text}`);
        });
      } else {
        console.log('%c[INFO]', styles.warning, 'No memories found matching query');
      }

      return data.results || [];
    } catch (error) {
      console.log('%c[ERROR]', styles.error, 'Failed to search memories:', error);
      return [];
    }
  }, []);

  const getMemoryStats = useCallback(async (): Promise<MemoryStatsResponse | null> => {
    console.log('%c[MEMORY DEBUG] Fetching Memory Stats...', styles.header);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/stats`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: MemoryStatsResponse = await response.json();

      console.log('%c[MEMORY STATS]', styles.memory, 'Retrieved successfully');
      console.log('Memory System Enabled:', data.enabled);

      if (data.total_memories !== undefined) {
        console.log('Total Memories:', data.total_memories);
      }
      if (data.by_type) {
        console.log('Memories by Type:', data.by_type);
      }
      if (data.error) {
        console.log('%c[WARNING]', styles.warning, data.error);
      }

      return data;
    } catch (error) {
      console.log('%c[ERROR]', styles.error, 'Failed to fetch memory stats:', error);
      return null;
    }
  }, []);

  const getConfig = useCallback(async (): Promise<ConfigResponse | null> => {
    console.log('%c[MEMORY DEBUG] Fetching System Config...', styles.header);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/config/info`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: ConfigResponse = await response.json();

      console.log('%c[CONFIG]', styles.info, 'System Configuration:');
      console.log('LLM Provider:', data.config.llm_provider);
      console.log('Has Gemini:', data.config.has_gemini);
      console.log('Has OpenAI:', data.config.has_openai);
      console.log('Has Pinecone:', data.config.has_pinecone);
      console.log('Has MongoDB:', data.config.has_mongodb);
      console.log('---');
      console.log('Biographer Enabled:', data.config.enable_biographer);
      console.log('Memory Extraction Enabled:', data.config.enable_memory_extraction);
      console.log('Semantic Search Enabled:', data.config.enable_semantic_search);
      console.log('Skills Enabled:', data.config.enable_skills);

      if (data.validation && data.validation.length > 0) {
        console.log('%c[VALIDATION ISSUES]', styles.warning);
        data.validation.forEach(issue => console.log(' -', issue));
      } else {
        console.log('%c[VALIDATION]', styles.success, 'All checks passed!');
      }

      return data;
    } catch (error) {
      console.log('%c[ERROR]', styles.error, 'Failed to fetch config:', error);
      return null;
    }
  }, []);

  const extractMemories = useCallback(async (
    exchanges: Array<{student: string, tutor: string}>
  ): Promise<any> => {
    console.log('%c[MEMORY DEBUG] Extracting Memories from Exchanges...', styles.header);
    console.log('Number of exchanges:', exchanges.length);

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/memory/extract`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ exchanges }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      console.log('%c[EXTRACTION RESULTS]', styles.memory);
      console.log('Memories Extracted:', data.memories_extracted);
      console.log('Emotions Detected:', data.emotions_detected);
      console.log('Breakthroughs:', data.breakthroughs);
      console.log('Unfinished Topics:', data.unfinished_topics);

      if (data.memories && data.memories.length > 0) {
        console.log('%c--- EXTRACTED MEMORIES ---', styles.memory);
        console.table(data.memories.map((m: any, i: number) => ({
          '#': i + 1,
          type: m.type,
          importance: m.importance?.toFixed(2),
          emotion: m.emotion || 'none',
          text: m.text?.substring(0, 50) + (m.text?.length > 50 ? '...' : ''),
        })));
      }

      return data;
    } catch (error) {
      console.log('%c[ERROR]', styles.error, 'Failed to extract memories:', error);
      return null;
    }
  }, []);

  const testMemoryPipeline = useCallback(async (): Promise<void> => {
    console.log('%c[MEMORY DEBUG] Running Full Pipeline Test...', styles.header);
    console.log('='.repeat(60));

    // Test 1: Config
    console.log('\n%c[TEST 1/4] System Configuration', styles.info);
    await getConfig();

    // Test 2: Biography
    console.log('\n%c[TEST 2/4] Biography Retrieval', styles.info);
    await getBiography();

    // Test 3: Memory Stats
    console.log('\n%c[TEST 3/4] Memory Statistics', styles.info);
    await getMemoryStats();

    // Test 4: Memory Search
    console.log('\n%c[TEST 4/4] Memory Search (query: "learning")', styles.info);
    await searchMemories('learning', 5);

    console.log('\n' + '='.repeat(60));
    console.log('%c[MEMORY DEBUG] Pipeline Test Complete!', styles.success);
    console.log('Use window.memoryDebug for individual tests');
  }, [getConfig, getBiography, getMemoryStats, searchMemories]);

  // Store ref for window access
  debugRef.current = {
    getBiography,
    searchMemories,
    getMemoryStats,
    getConfig,
    testMemoryPipeline,
    extractMemories,
  };

  // Expose to window for console access
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).memoryDebug = debugRef.current;

      console.log('%c[MEMORY DEBUG] Available!', styles.header);
      console.log('Use these commands in the console:');
      console.log('  window.memoryDebug.testMemoryPipeline() - Run full test');
      console.log('  window.memoryDebug.getBiography() - Get student biography');
      console.log('  window.memoryDebug.searchMemories("query") - Search memories');
      console.log('  window.memoryDebug.getMemoryStats() - Get memory statistics');
      console.log('  window.memoryDebug.getConfig() - Get system configuration');
      console.log('  window.memoryDebug.extractMemories([{student:"...", tutor:"..."}]) - Extract from exchanges');
    }

    return () => {
      if (typeof window !== 'undefined') {
        delete (window as any).memoryDebug;
      }
    };
  }, []);

  return {
    getBiography,
    searchMemories,
    getMemoryStats,
    getConfig,
    testMemoryPipeline,
    extractMemories,
  };
}

// Type declaration for window.memoryDebug
declare global {
  interface Window {
    memoryDebug?: {
      getBiography: () => Promise<BiographyResponse | null>;
      searchMemories: (query: string, topK?: number) => Promise<MemorySearchResult[]>;
      getMemoryStats: () => Promise<MemoryStatsResponse | null>;
      getConfig: () => Promise<ConfigResponse | null>;
      testMemoryPipeline: () => Promise<void>;
      extractMemories: (exchanges: Array<{student: string, tutor: string}>) => Promise<any>;
    };
  }
}
