/**
 * Athena Usage Example
 *
 * This file demonstrates how to use Athena in your existing codebase.
 */

import React from 'react';
import { AthenaQuestionRenderer } from './AthenaIntegration';

import type { PerseusItem } from '../core/types';

/**
 * Example 1: Replace an existing Perseus renderer
 *
 * Before (with Perseus):
 * ```tsx
 * import { ServerItemRenderer } from '@khanacademy/perseus';
 *
 * <ServerItemRenderer
 *   item={questionData}
 *   problemNum={1}
 *   reviewMode={false}
 *   apiOptions={{}}
 * />
 * ```
 *
 * After (with Athena):
 * ```tsx
 * import { AthenaQuestionRenderer } from '@/renderer/athena/integration';
 *
 * <AthenaQuestionRenderer
 *   question={questionData}
 *   reviewMode={false}
 *   onSubmit={(result) => console.log('Score:', result)}
 * />
 * ```
 */

// Sample Perseus question data
const SAMPLE_QUESTION: PerseusItem = {
  question: {
    content: 'Solve for $x$:\n\n$$2x + 5 = 15$$\n\n[[☃ numeric-input 1]]',
    widgets: {
      'numeric-input 1': {
        type: 'numeric-input',
        alignment: 'default',
        static: false,
        graded: true,
        options: {
          answers: [{ value: 5, status: 'correct', maxError: 0 }],
          size: 'normal',
        },
        version: { major: 0, minor: 0 },
      },
    },
    images: {},
  },
  hints: [
    {
      content: 'Subtract 5 from both sides: $2x = 10$',
      widgets: {},
      images: {},
    },
    {
      content: 'Divide both sides by 2: $x = 5$',
      widgets: {},
      images: {},
    },
  ],
  answerArea: { type: 'single' },
};

/**
 * Example component showing basic usage
 */
export function BasicUsageExample() {
  const handleSubmit = (result: { correct: boolean; earned: number; total: number }) => {
    console.log('Answer submitted:', result);

    if (result.correct) {
      alert('Correct! Great job!');
    } else {
      alert('Not quite right. Try again!');
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 20 }}>
      <h1>Athena Integration Example</h1>

      <AthenaQuestionRenderer
        question={SAMPLE_QUESTION}
        showHints={true}
        onSubmit={handleSubmit}
        onAnswerChange={(answers) => console.log('Answers changed:', answers)}
      />
    </div>
  );
}

/**
 * Example 2: Using Athena in review mode
 */
export function ReviewModeExample() {
  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 20 }}>
      <h1>Review Mode Example</h1>

      <AthenaQuestionRenderer
        question={SAMPLE_QUESTION}
        reviewMode={true}
        showHints={true}
        initialHints={2} // Show all hints in review mode
      />
    </div>
  );
}



/**
 * Example 4: Migrating multiple questions
 *
 * ```tsx
 * import { migratePerseusQuestions } from '@/renderer/athena/integration';
 *
 * // Fetch your Perseus questions from API
 * const perseusQuestions = await fetchQuestionsFromAPI();
 *
 * // Migrate them to Athena format
 * const { successful, failed, stats } = await migratePerseusQuestions(perseusQuestions);
 *
 * console.log(`Migrated ${stats.success}/${stats.total} questions`);
 * if (failed.length > 0) {
 *   console.warn('Failed questions:', failed);
 * }
 *
 * // Use the migrated questions with AthenaRenderer
 * successful.forEach((athenaItem, index) => {
 *   // Store or render each item
 * });
 * ```
 */

/**
 * Example 5: Using the useAthenaQuestion hook
 *
 * ```tsx
 * import { useAthenaQuestion } from '@/renderer/athena/integration';
 *
 * function MyQuestionComponent({ perseusData }) {
 *   const { athenaItem, answers, setAnswers, score, isReady, error } = useAthenaQuestion(perseusData);
 *
 *   if (error) return <div>Error: {error}</div>;
 *   if (!isReady) return <div>Loading...</div>;
 *
 *   const handleCheck = () => {
 *     const result = score();
 *     if (result?.correct) {
 *       alert('Correct!');
 *     }
 *   };
 *
 *   return (
 *     <div>
 *       <AthenaRenderer
 *         item={athenaItem}
 *         onChange={setAnswers}
 *       />
 *       <button onClick={handleCheck}>Check Answer</button>
 *     </div>
 *   );
 * }
 * ```
 */

export default BasicUsageExample;
