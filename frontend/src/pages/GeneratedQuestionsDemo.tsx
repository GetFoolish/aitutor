import React, { useState } from 'react';
import { useGeneratedQuestions, useGeneratedQuestionsList } from '../hooks/query-hooks/useGeneratedQuestions';

/**
 * Demo page for Generated Questions.
 * 
 * Shows questions generated with Innocent Drinks tone + personalization.
 */
export function GeneratedQuestionsDemo() {
  const [grade, setGrade] = useState<string>('K-2');
  const [currentIndex, setCurrentIndex] = useState(0);
  
  // Fetch questions list
  const { data: questionsList } = useGeneratedQuestionsList();
  
  // Fetch questions for selected grade
  const { data: questions, isLoading, error } = useGeneratedQuestions({
    count: 10,
    grade,
    subject: 'math',
  });
  
  const currentQuestion = questions?.[currentIndex];
  
  const handleNext = () => {
    if (questions && currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };
  
  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  // Extract widget info from question
  const getWidgetInfo = (q: any) => {
    const widgets = q?.question?.widgets || {};
    const entries = Object.entries(widgets);
    if (entries.length === 0) return null;
    const [name, config] = entries[0] as [string, any];
    return { name, type: config?.type, options: config?.options };
  };

  // Clean content (remove widget placeholder)
  const cleanContent = (content: string) => {
    return content?.replace(/\[\[☃[^\]]+\]\]/g, '').trim() || '';
  };

  // Render widget preview
  const renderWidget = (widget: any) => {
    if (!widget) return null;
    
    const { type, options } = widget;
    
    if (type === 'radio') {
      const choices = options?.choices || [];
      return (
        <div className="space-y-2 mt-4">
          {choices.map((c: any, i: number) => (
            <div 
              key={i}
              className={`p-3 rounded-lg border-2 ${
                c.correct 
                  ? 'border-green-400 bg-green-50' 
                  : 'border-gray-200 bg-white'
              }`}
            >
              <span className="mr-2">○</span> {c.content}
              {c.correct && <span className="ml-2 text-green-600 text-sm">✓ correct</span>}
            </div>
          ))}
        </div>
      );
    }
    
    if (type === 'numeric-input' || type === 'input-number') {
      const answer = options?.answers?.[0]?.value || options?.value || '?';
      return (
        <div className="mt-4">
          <input 
            type="text" 
            placeholder="?" 
            disabled
            className="p-3 border-2 border-gray-200 rounded-lg w-32 text-lg"
          />
          <div className="text-sm text-gray-500 mt-2">
            Correct answer: <span className="font-medium text-green-600">{answer}</span>
          </div>
        </div>
      );
    }
    
    if (type === 'dropdown') {
      const choices = options?.choices || [];
      const correct = choices.find((c: any) => c.correct)?.content || '?';
      return (
        <div className="mt-4">
          <select disabled className="p-3 border-2 border-gray-200 rounded-lg min-w-48">
            {choices.map((c: any, i: number) => (
              <option key={i}>{c.content}</option>
            ))}
          </select>
          <div className="text-sm text-gray-500 mt-2">
            Correct: <span className="font-medium text-green-600">{correct}</span>
          </div>
        </div>
      );
    }
    
    if (type === 'orderer') {
      const items = options?.options || options?.correctOptions || [];
      return (
        <div className="flex flex-wrap gap-2 mt-4">
          {items.map((item: string, i: number) => (
            <div key={i} className="px-4 py-2 bg-white border-2 border-gray-200 rounded-lg cursor-grab">
              ↕️ {item}
            </div>
          ))}
        </div>
      );
    }
    
    return <div className="text-gray-500 mt-4">{type} widget</div>;
  };
  
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">
            🎯 Generated Questions Demo
          </h1>
          <p className="text-gray-600 mt-2">
            Personalized questions with Innocent Drinks tone
          </p>
        </div>
        
        {/* Grade Selector */}
        <div className="flex justify-center gap-4 mb-8">
          {['K-2', '3-5', '6-8', '9-12'].map((g) => (
            <button
              key={g}
              onClick={() => {
                setGrade(g);
                setCurrentIndex(0);
              }}
              className={`px-6 py-2 rounded-full font-medium transition-all ${
                grade === g
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 border border-gray-300 hover:border-blue-400'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
        
        {/* Questions List Info */}
        {questionsList && (
          <div className="bg-white rounded-lg p-4 mb-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Available Questions</h3>
            <div className="flex gap-4 text-sm flex-wrap">
              {Object.entries(questionsList.grades || {}).map(([g, subjects]: [string, any]) => (
                <div key={g} className="bg-gray-100 px-3 py-1 rounded">
                  {g}: {subjects?.math?.count || 0} math
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Question Display */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          {isLoading && (
            <div className="p-8 text-center text-gray-500">
              Loading questions...
            </div>
          )}
          
          {error && (
            <div className="p-8 text-center text-red-500">
              Error: {(error as Error).message}
            </div>
          )}
          
          {currentQuestion && (
            <>
              {/* Question Header */}
              <div className="bg-gray-50 px-6 py-4 border-b flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm font-medium">
                    {(currentQuestion as any).dash_metadata?.grade}
                  </span>
                  <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full text-sm font-medium">
                    {(currentQuestion as any).dash_metadata?.topic}
                  </span>
                  <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm font-medium">
                    {getWidgetInfo(currentQuestion)?.type}
                  </span>
                </div>
                <div className="text-gray-500 text-sm">
                  {currentIndex + 1} / {questions?.length || 0}
                </div>
              </div>
              
              {/* Question Content */}
              <div className="p-6">
                <div className="text-xl leading-relaxed mb-4">
                  {cleanContent(currentQuestion.question?.content || '')}
                </div>
                
                {/* Widget */}
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                    {getWidgetInfo(currentQuestion)?.type} widget
                  </div>
                  {renderWidget(getWidgetInfo(currentQuestion))}
                </div>
                
                {/* Hints */}
                {currentQuestion.hints && currentQuestion.hints.length > 0 && (
                  <div className="mt-6 border-t pt-4">
                    <h4 className="text-sm font-medium text-gray-500 mb-3">💡 Hints</h4>
                    <div className="space-y-2">
                      {currentQuestion.hints.slice(0, 3).map((hint: any, i: number) => (
                        <div key={i} className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded-r text-sm">
                          {hint.content || hint}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Navigation */}
              <div className="bg-gray-50 px-6 py-4 border-t flex justify-between">
                <button
                  onClick={handlePrev}
                  disabled={currentIndex === 0}
                  className="px-6 py-2 rounded-lg bg-gray-200 text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 transition-colors"
                >
                  ← Previous
                </button>
                <button
                  onClick={handleNext}
                  disabled={!questions || currentIndex >= questions.length - 1}
                  className="px-6 py-2 rounded-lg bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
                >
                  Next →
                </button>
              </div>
            </>
          )}
          
          {!isLoading && !error && !currentQuestion && (
            <div className="p-8 text-center text-gray-500">
              No questions found for {grade} math. Generate some first!
            </div>
          )}
        </div>
        
        {/* Integration Info */}
        <div className="mt-6 bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium text-gray-700 mb-2">🔌 Integration</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <p><strong>API:</strong> <code className="bg-gray-100 px-2 py-0.5 rounded">http://localhost:8001/api/generated/questions/{'{count}'}</code></p>
            <p><strong>Hook:</strong> <code className="bg-gray-100 px-2 py-0.5 rounded">useGeneratedQuestions({'{count, grade, subject}'})</code></p>
            <p><strong>Format:</strong> Same as DASH API (Perseus-compatible)</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default GeneratedQuestionsDemo;
