/**
 * SherlockED API New - Frontend Client
 *
 * Client for the Athena-based question service.
 * NO CODE FROM SHERLOCKEDAPI OR PERSEUS.
 */

export interface AthenaWidget {
  type: string;
  options: Record<string, unknown>;
  alignment?: string;
  graded?: boolean;
  static?: boolean;
  version?: { major: number; minor: number };
}

export interface AthenaQuestion {
  content: string;
  widgets: Record<string, AthenaWidget>;
  images?: Record<string, {
    url: string;
    width: number;
    height: number;
    alt?: string;
  }>;
}

export interface AthenaHint {
  content: string;
  widgets?: Record<string, AthenaWidget>;
  images?: Record<string, unknown>;
  replace?: boolean;
}

export interface AthenaAnswerArea {
  calculator: boolean;
  periodicTable: boolean;
  chi2Table: boolean;
  tTable: boolean;
  zTable: boolean;
  financialCalculator: boolean;
}

export interface AthenaItem {
  _id: string;
  slug: string;
  skill_prefix: string;
  question: AthenaQuestion;
  hints: AthenaHint[];
  answerArea: AthenaAnswerArea;
  widgetTypes: string[];
}

// API base URL - new Athena service
const SHERLOCKED_API_NEW_URL = import.meta.env.VITE_SHERLOCKED_API_NEW_URL || 'http://localhost:8010';

/**
 * Fetch a single question by ObjectId
 */
export async function fetchQuestionById(questionId: string): Promise<AthenaItem | null> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/api/question/${questionId}`);

    if (!response.ok) {
      console.error(`Failed to fetch question: ${response.status}`);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching question:', error);
    return null;
  }
}

/**
 * Fetch multiple random questions
 */
export async function fetchQuestions(
  count: number = 10,
  widgetTypes?: string[],
  skillPrefix?: string
): Promise<AthenaItem[]> {
  try {
    let url = `${SHERLOCKED_API_NEW_URL}/api/questions/${count}`;
    const params = new URLSearchParams();

    if (widgetTypes && widgetTypes.length > 0) {
      params.append('widget_types', widgetTypes.join(','));
    }

    if (skillPrefix) {
      params.append('skill_prefix', skillPrefix);
    }

    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`Failed to fetch questions: ${response.status}`);
      return [];
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching questions:', error);
    return [];
  }
}

/**
 * Fetch questions by multiple ObjectIds
 */
export async function fetchQuestionsByIds(ids: string[]): Promise<AthenaItem[]> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/api/questions/by-ids`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ids }),
    });

    if (!response.ok) {
      console.error(`Failed to fetch questions: ${response.status}`);
      return [];
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching questions:', error);
    return [];
  }
}

/**
 * Get widget types summary
 */
export async function getWidgetTypes(): Promise<Record<string, number>> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/api/widget-types`);

    if (!response.ok) {
      return {};
    }

    const data = await response.json();
    return data.widget_types || {};
  } catch (error) {
    console.error('Error fetching widget types:', error);
    return {};
  }
}

/**
 * Search questions by text
 */
export async function searchQuestions(
  query: string,
  limit: number = 20
): Promise<AthenaItem[]> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/api/questions/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, limit }),
    });

    if (!response.ok) {
      return [];
    }

    const data = await response.json();
    return data.results || [];
  } catch (error) {
    console.error('Error searching questions:', error);
    return [];
  }
}

/**
 * Get database stats
 */
export async function getDatabaseStats(): Promise<{
  total_questions: number;
  widget_types: Record<string, number>;
}> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/api/stats`);

    if (!response.ok) {
      return { total_questions: 0, widget_types: {} };
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching stats:', error);
    return { total_questions: 0, widget_types: {} };
  }
}

/**
 * Check service health
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${SHERLOCKED_API_NEW_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
