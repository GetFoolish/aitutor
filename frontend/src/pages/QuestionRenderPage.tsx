import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ServerItemRenderer } from '../package/perseus/src/server-item-renderer';
import { storybookDependenciesV2 } from '../package/perseus/testing/test-dependencies';
import { RenderStateRoot } from '@khanacademy/wonder-blocks-core';
import { PerseusI18nContextProvider } from '../package/perseus/src/components/i18n-context';
import { mockStrings } from '../package/perseus/src/strings';

/**
 * Minimal Perseus question renderer for screenshot capture
 * Used by Selenium to capture visual representation of questions
 */
export function QuestionRenderPage() {
  const { questionId } = useParams<{ questionId: string }>();
  const [question, setQuestion] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (questionId) {
      fetchQuestion(questionId);
    }
  }, [questionId]);

  const fetchQuestion = async (id: string) => {
    try {
      setLoading(true);
      // Fetch from Dash API - assumes question_id format
      const response = await fetch(`http://localhost:8000/get-question/${id}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch question: ${response.status}`);
      }

      const data = await response.json();
      setQuestion(data);
      setLoading(false);
    } catch (err: any) {
      console.error('Error loading question:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        padding: '40px',
        fontFamily: 'sans-serif',
        fontSize: '18px',
        color: '#333'
      }}>
        Loading question...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '40px',
        fontFamily: 'sans-serif',
        fontSize: '18px',
        color: '#d32f2f'
      }}>
        Error: {error}
      </div>
    );
  }

  if (!question || !question.question) {
    return (
      <div style={{
        padding: '40px',
        fontFamily: 'sans-serif',
        fontSize: '18px',
        color: '#666'
      }}>
        No question found
      </div>
    );
  }

  return (
    <div style={{
      padding: '40px',
      maxWidth: '900px',
      margin: '0 auto',
      backgroundColor: '#ffffff',
      minHeight: '100vh'
    }}>
      <div className="framework-perseus" style={{
        fontSize: '18px',
        lineHeight: '1.6'
      }}>
        <RenderStateRoot>
          <PerseusI18nContextProvider
            strings={mockStrings}
            locale="en"
          >
            <ServerItemRenderer
              problemNum={1}
              item={question}
              dependencies={storybookDependenciesV2}
            />
          </PerseusI18nContextProvider>
        </RenderStateRoot>
      </div>
    </div>
  );
}
