/**
 * Signup form for new users - collects user type and age
 */
import React, { useState } from 'react';
import { authAPI } from '../../lib/auth-api';
import './auth.scss';

interface SignupFormProps {
  setupToken: string;
  googleUser: any;
  onComplete: (token: string, user: any) => void;
  onCancel: () => void;
}

const SignupForm: React.FC<SignupFormProps> = ({ setupToken, googleUser, onComplete, onCancel }) => {
  const [userType, setUserType] = useState<'student' | 'parent'>('student');
  const [age, setAge] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const ageNum = parseInt(age);
    if (!age || isNaN(ageNum) || ageNum < 5 || ageNum > 18) {
      setError('Please enter a valid age between 5 and 18');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await authAPI.completeSetup(setupToken, userType, ageNum);
      onComplete(response.token, response.user);
    } catch (err: any) {
      setError(err.message || 'Failed to complete setup. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>Complete Your Profile</h1>
        <p>Welcome! Please tell us a bit about yourself to get started.</p>

        <form onSubmit={handleSubmit} className="signup-form">
          <div className="form-group">
            <label>I am a:</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="userType"
                  value="student"
                  checked={userType === 'student'}
                  onChange={(e) => setUserType(e.target.value as 'student' | 'parent')}
                />
                <span>Student</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="userType"
                  value="parent"
                  checked={userType === 'parent'}
                  onChange={(e) => setUserType(e.target.value as 'student' | 'parent')}
                />
                <span>Parent</span>
              </label>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="age">How old are you? (or your child's age)</label>
            <input
              id="age"
              type="number"
              min="5"
              max="18"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="Enter age (5-18)"
              required
              disabled={isSubmitting}
            />
            <small>This helps us personalize your learning experience</small>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="form-actions">
            <button type="button" onClick={onCancel} disabled={isSubmitting} className="cancel-button">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting} className="submit-button">
              {isSubmitting ? 'Setting up...' : 'Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SignupForm;

