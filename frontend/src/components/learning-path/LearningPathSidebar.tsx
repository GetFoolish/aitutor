import { useState, useEffect } from 'react';
import { FaLock, FaCalculator, FaChevronDown, FaChevronRight, FaCheckCircle, FaExclamationCircle, FaTimesCircle } from 'react-icons/fa';
import { useAuth } from '../../contexts/AuthContext';

interface SkillState {
  skill_id: string;
  name: string;
  grade_level: string;
  memory_strength: number;
  practice_count: number;
  correct_count: number;
  prerequisites: string[];
  is_locked: boolean;
}

interface LearningPathSidebarProps {
  onSkillSelect?: (skillId: string) => void;
}

export function LearningPathSidebar({ onSkillSelect }: LearningPathSidebarProps) {
  const { user } = useAuth();
  const [skills, setSkills] = useState<SkillState[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Kindergarten']));

  useEffect(() => {
    if (user) {
      fetchSkillStates();
    }
  }, [user]);

  const fetchSkillStates = async () => {
    if (!user) return;

    try {
      const response = await fetch(`http://localhost:8000/skill-states/${user.user_id}`);
      const data = await response.json();
      setSkills(data.skills || []);
    } catch (error) {
      console.error('Failed to fetch skill states:', error);
    } finally {
      setLoading(false);
    }
  };

  // Group skills by category
  const groupedSkills = skills.reduce((acc, skill) => {
    const category = skill.grade_level === 'K' ? 'Kindergarten' :
                     skill.grade_level.startsWith('GRADE') ? 'Arithmetic' : 'Advanced';

    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(skill);
    return acc;
  }, {} as Record<string, SkillState[]>);

  const totalSkills = skills.length;
  const masteredSkills = skills.filter(s => s.memory_strength >= 0.8).length;

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Overall Progress Card */}
      <div className="card" style={{
        padding: '24px',
        background: '#FFFFFF',
        border: '1px solid #E5E7EB',
        borderRadius: '16px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)'
      }}>
        <h2 style={{
          marginBottom: '8px',
          fontSize: '20px',
          fontWeight: 700,
          fontFamily: "'Nunito', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
          color: '#1E1E1E',
          letterSpacing: '-0.02em'
        }}>
          Your Learning Path
        </h2>
        <p style={{
          fontSize: '14px',
          color: '#6B7280',
          marginBottom: '16px',
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
        }}>
          {masteredSkills} of {totalSkills} skills mastered
        </p>
        <div style={{
          height: '10px',
          background: '#E5E7EB',
          borderRadius: '999px',
          overflow: 'hidden',
          boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.06)'
        }}>
          <div style={{
            height: '100%',
            width: `${totalSkills > 0 ? (masteredSkills / totalSkills) * 100 : 0}%`,
            background: 'linear-gradient(90deg, #6366F1 0%, #8B5CF6 100%)',
            borderRadius: '999px',
            transition: 'width 300ms cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 2px 4px rgba(99, 102, 241, 0.3)'
          }}></div>
        </div>
      </div>

      {/* Category Cards */}
      {Object.entries(groupedSkills).map(([category, categorySkills]) => {
        const categoryMastered = categorySkills.filter(s => s.memory_strength >= 0.8).length;
        const categoryTotal = categorySkills.length;
        const categoryProgress = categoryTotal > 0 ? (categoryMastered / categoryTotal) * 100 : 0;
        const isExpanded = expandedCategories.has(category);

        return (
          <div key={category} className="card">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(category)}
              className="btn btn--ghost"
              style={{
                width: '100%',
                justifyContent: 'space-between',
                padding: '16px',
                textAlign: 'left'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {isExpanded ? (
                  <FaChevronDown size={18} color="#6366F1" style={{ transition: 'transform 200ms' }} />
                ) : (
                  <FaChevronRight size={18} color="#6366F1" style={{ transition: 'transform 200ms' }} />
                )}
                <FaCalculator color="#fbbf24" size={18} />
                <div>
                  <h3 style={{
                    margin: 0,
                    fontSize: '16px',
                    fontWeight: 700,
                    color: '#1E1E1E',
                    fontFamily: "'Nunito', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
                  }}>
                    {category}
                  </h3>
                  <p className="subtle" style={{
                    margin: 0,
                    fontSize: '13px',
                    color: '#6B7280'
                  }}>
                    {categoryMastered} of {categoryTotal} skills
                  </p>
                </div>
              </div>
              <span
                style={{
                  fontSize: '12px',
                  padding: '6px 12px',
                  borderRadius: '12px',
                  background: '#EEF2FF',
                  color: '#6366F1',
                  fontWeight: 600,
                  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"
                }}
              >
                {Math.round(categoryProgress)}%
              </span>
            </button>

            {/* Category Skills */}
            {isExpanded && (
              <div style={{ marginTop: '12px', paddingLeft: '8px' }}>
                {/* Category Progress Bar */}
                <div className="meter mb-12">
                  <i style={{ width: `${categoryProgress}%` }}></i>
                </div>

                {/* Skill Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {categorySkills.map((skill) => (
                    <div
                      key={skill.skill_id}
                      className="skill"
                      onClick={() => !skill.is_locked && onSkillSelect?.(skill.skill_id)}
                      style={{
                        cursor: skill.is_locked ? 'not-allowed' : 'pointer',
                        opacity: skill.is_locked ? 0.6 : 1,
                        borderColor:
                          skill.memory_strength >= 0.8 ? '#2ed573' :
                          skill.memory_strength >= 0.5 ? '#fbbf24' :
                          skill.is_locked ? '#2a3647' : '#1e2a3a',
                        borderWidth: '2px'
                      }}
                    >
                      <div className="skill-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {skill.is_locked && <FaLock size={10} color="#7b8a9a" />}
                          <span className="skill-name">{skill.name}</span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-end' }}>
                          <span
                            style={{
                              fontSize: '10px',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: skill.grade_level === 'K' ? '#581c87' : '#0e7490',
                              color: '#e8edf2'
                            }}
                          >
                            {skill.grade_level === 'K' ? 'K' : skill.grade_level.replace('GRADE_', 'G')}
                          </span>
                          <span className="skill-score">
                            Level {Math.floor(skill.memory_strength * 5)}
                          </span>
                        </div>
                      </div>

                      {/* Progress */}
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '4px', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            {skill.memory_strength >= 0.8 ? (
                              <FaCheckCircle size={10} color="#2ed573" title="Mastered" />
                            ) : skill.memory_strength >= 0.5 ? (
                              <FaExclamationCircle size={10} color="#fbbf24" title="In Progress" />
                            ) : (
                              <FaTimesCircle size={10} color="#ff6868" title="Needs Practice" />
                            )}
                            <span className="subtle">Memory strength</span>
                          </div>
                          <span className="subtle">
                            {Math.round(skill.memory_strength * 100)}%
                          </span>
                        </div>
                        <div className="meter">
                          <i
                            style={{
                              width: `${skill.memory_strength * 100}%`,
                              background:
                                skill.memory_strength >= 0.8 ? '#2ed573' :
                                skill.memory_strength >= 0.5 ? '#fbbf24' : '#ff6868',
                              backgroundImage: skill.memory_strength >= 0.8
                                ? 'repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(255,255,255,0.1) 5px, rgba(255,255,255,0.1) 10px)'
                                : skill.memory_strength >= 0.5
                                ? 'repeating-linear-gradient(45deg, transparent, transparent 3px, rgba(255,255,255,0.1) 3px, rgba(255,255,255,0.1) 6px)'
                                : 'repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(255,255,255,0.1) 2px, rgba(255,255,255,0.1) 4px)'
                            }}
                          ></i>
                        </div>
                      </div>

                      {/* Prerequisites */}
                      {skill.is_locked && skill.prerequisites.length > 0 && (
                        <p className="subtle" style={{ fontSize: '11px', marginTop: '8px', marginBottom: 0 }}>
                          Requires: {skill.prerequisites.join(', ')}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
