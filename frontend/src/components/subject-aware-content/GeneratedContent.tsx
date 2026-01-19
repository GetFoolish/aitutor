/**
 * GeneratedContent - AI-generated educational content for non-Math subjects
 */
import React, { useState, useEffect } from 'react';

interface GeneratedContentProps {
  subject: string;
  grade: string;
  userName: string;
}

interface ContentItem {
  type: 'lesson' | 'question' | 'exercise';
  title: string;
  content: string;
  options?: string[];
  correctAnswer?: number;
}

const GeneratedContent: React.FC<GeneratedContentProps> = ({ subject, grade, userName }) => {
  const [content, setContent] = useState<ContentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);

  // Sample content for demonstration - in production this would come from AI
  const generateSampleContent = (subject: string, grade: string): ContentItem => {
    const gradeNum = grade.replace('GRADE_', '').replace('K', '0');

    const contentBySubject: Record<string, ContentItem[]> = {
      'English': [
        {
          type: 'lesson',
          title: 'Parts of Speech: Nouns',
          content: `A **noun** is a word that represents a person, place, thing, or idea.\n\n**Examples:**\n- Person: teacher, doctor, Sarah\n- Place: school, park, New York\n- Thing: book, computer, apple\n- Idea: freedom, happiness, love\n\n**Practice:** Can you identify the nouns in this sentence?\n"The cat sat on the warm blanket."`,
          options: ['cat, blanket', 'sat, warm', 'the, on', 'cat, sat, blanket'],
          correctAnswer: 0
        },
        {
          type: 'question',
          title: 'Reading Comprehension',
          content: `Read the passage and answer the question:\n\n*"The sun was setting over the mountains, painting the sky in shades of orange and pink. Maya watched from her window, thinking about the adventure that awaited her tomorrow."*\n\n**Question:** What time of day is it in the passage?`,
          options: ['Morning', 'Afternoon', 'Evening/Sunset', 'Night'],
          correctAnswer: 2
        }
      ],
      'Science': [
        {
          type: 'lesson',
          title: 'The Water Cycle',
          content: `The **water cycle** is how water moves around Earth.\n\n**Steps:**\n1. **Evaporation** - Sun heats water, turning it into vapor\n2. **Condensation** - Water vapor cools and forms clouds\n3. **Precipitation** - Water falls as rain or snow\n4. **Collection** - Water gathers in oceans, lakes, and rivers\n\n**Question:** What causes water to evaporate?`,
          options: ['The moon', 'Heat from the sun', 'Wind', 'Clouds'],
          correctAnswer: 1
        }
      ],
      'History': [
        {
          type: 'lesson',
          title: 'Ancient Civilizations',
          content: `**Ancient Egypt** was one of the world's first great civilizations.\n\n**Key Facts:**\n- Located along the Nile River in Africa\n- Famous for building pyramids and the Sphinx\n- Used hieroglyphics for writing\n- Ruled by pharaohs\n\n**Question:** What river was essential to Ancient Egyptian civilization?`,
          options: ['Amazon River', 'Nile River', 'Mississippi River', 'Ganges River'],
          correctAnswer: 1
        }
      ],
      'Coding': [
        {
          type: 'lesson',
          title: 'Introduction to Variables',
          content: `A **variable** is like a container that stores information.\n\n**Example in Python:**\n\`\`\`python\nname = "Alex"\nage = 10\nprint("Hello, " + name)\n\`\`\`\n\n**Question:** In the code above, what value is stored in the variable 'age'?`,
          options: ['Alex', '10', 'name', 'Hello'],
          correctAnswer: 1
        }
      ],
      'Arts': [
        {
          type: 'lesson',
          title: 'Primary Colors',
          content: `**Primary colors** are colors that cannot be made by mixing other colors.\n\nThe three primary colors are:\n- **Red**\n- **Blue**\n- **Yellow**\n\nMixing primary colors creates **secondary colors**:\n- Red + Blue = Purple\n- Blue + Yellow = Green\n- Red + Yellow = Orange\n\n**Question:** What color do you get when you mix blue and yellow?`,
          options: ['Purple', 'Orange', 'Green', 'Brown'],
          correctAnswer: 2
        }
      ]
    };

    const subjectContent = contentBySubject[subject] || contentBySubject['English'];
    return subjectContent[Math.floor(Math.random() * subjectContent.length)];
  };

  useEffect(() => {
    setLoading(true);
    setSelectedAnswer(null);
    setShowResult(false);

    // Simulate API call delay
    const timer = setTimeout(() => {
      setContent(generateSampleContent(subject, grade));
      setLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, [subject, grade]);

  const handleAnswerSelect = (index: number) => {
    if (showResult) return;
    setSelectedAnswer(index);
  };

  const handleSubmit = () => {
    if (selectedAnswer === null) return;
    setShowResult(true);
  };

  const handleNext = () => {
    setContent(generateSampleContent(subject, grade));
    setSelectedAnswer(null);
    setShowResult(false);
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '300px',
        background: '#FFFDF5',
        border: '4px solid #000',
        boxShadow: '8px 8px 0 #000'
      }}>
        <div style={{
          padding: '24px 32px',
          border: '4px solid #000',
          background: '#FFD93D',
          boxShadow: '4px 4px 0 #000',
          fontWeight: 700,
          fontSize: '18px'
        }}>
          Loading {subject} content...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '24px',
        background: '#FFE5E5',
        border: '4px solid #000',
        boxShadow: '8px 8px 0 #000'
      }}>
        <h3 style={{ color: '#D00', margin: 0 }}>Error loading content</h3>
        <p>{error}</p>
      </div>
    );
  }

  if (!content) return null;

  const isCorrect = selectedAnswer === content.correctAnswer;

  return (
    <div style={{
      background: '#FFFDF5',
      border: '4px solid #000',
      boxShadow: '8px 8px 0 #000',
      padding: '24px',
      minHeight: '400px'
    }}>
      {/* Subject badge */}
      <div style={{
        display: 'inline-block',
        padding: '6px 16px',
        background: '#FFD93D',
        border: '3px solid #000',
        fontWeight: 700,
        fontSize: '14px',
        textTransform: 'uppercase',
        marginBottom: '16px'
      }}>
        {subject}
      </div>

      {/* Title */}
      <h2 style={{
        fontSize: '24px',
        fontWeight: 900,
        marginBottom: '20px',
        color: '#000'
      }}>
        {content.title}
      </h2>

      {/* Content */}
      <div style={{
        fontSize: '16px',
        lineHeight: 1.7,
        marginBottom: '24px',
        whiteSpace: 'pre-wrap'
      }}>
        {content.content.split('**').map((part, i) =>
          i % 2 === 1 ? <strong key={i}>{part}</strong> : part
        )}
      </div>

      {/* Answer options */}
      {content.options && (
        <div style={{ marginBottom: '24px' }}>
          {content.options.map((option, index) => {
            let bgColor = '#fff';
            let borderColor = '#000';

            if (showResult) {
              if (index === content.correctAnswer) {
                bgColor = '#90EE90';
              } else if (index === selectedAnswer && !isCorrect) {
                bgColor = '#FFB6C1';
              }
            } else if (index === selectedAnswer) {
              bgColor = '#FFD93D';
            }

            return (
              <button
                key={index}
                onClick={() => handleAnswerSelect(index)}
                disabled={showResult}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '14px 20px',
                  marginBottom: '10px',
                  background: bgColor,
                  border: `3px solid ${borderColor}`,
                  textAlign: 'left',
                  fontSize: '16px',
                  fontWeight: 600,
                  cursor: showResult ? 'default' : 'pointer',
                  boxShadow: index === selectedAnswer ? '3px 3px 0 #000' : 'none',
                  transform: index === selectedAnswer ? 'translate(-2px, -2px)' : 'none'
                }}
              >
                {String.fromCharCode(65 + index)}. {option}
              </button>
            );
          })}
        </div>
      )}

      {/* Submit/Next button */}
      <div style={{ display: 'flex', gap: '12px' }}>
        {!showResult ? (
          <button
            onClick={handleSubmit}
            disabled={selectedAnswer === null}
            style={{
              padding: '14px 32px',
              background: selectedAnswer !== null ? '#FFD93D' : '#ccc',
              border: '4px solid #000',
              fontWeight: 700,
              fontSize: '16px',
              textTransform: 'uppercase',
              cursor: selectedAnswer !== null ? 'pointer' : 'not-allowed',
              boxShadow: selectedAnswer !== null ? '4px 4px 0 #000' : 'none'
            }}
          >
            Check Answer
          </button>
        ) : (
          <>
            <div style={{
              padding: '14px 24px',
              background: isCorrect ? '#90EE90' : '#FFB6C1',
              border: '4px solid #000',
              fontWeight: 700,
              fontSize: '16px'
            }}>
              {isCorrect ? 'Correct!' : 'Not quite - try again!'}
            </div>
            <button
              onClick={handleNext}
              style={{
                padding: '14px 32px',
                background: '#FFD93D',
                border: '4px solid #000',
                fontWeight: 700,
                fontSize: '16px',
                textTransform: 'uppercase',
                cursor: 'pointer',
                boxShadow: '4px 4px 0 #000'
              }}
            >
              Next Question
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default GeneratedContent;
