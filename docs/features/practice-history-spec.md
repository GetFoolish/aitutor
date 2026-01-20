# Practice History Dashboard

## Overview
Add a Practice History Dashboard that shows students their past learning sessions, questions answered, and performance trends over time. This helps students track their progress and identify areas for improvement.

## User Story
As a student using AI Tutor, I want to see my practice history so that I can:
- Review questions I've answered
- See my performance trends over time
- Identify skills that need more practice
- Feel motivated by seeing my progress

## Requirements

### Frontend Components

#### 1. Practice History Panel
- New component in `frontend/src/components/practice-history/`
- Accessible from the main navigation or side panel
- Shows list of recent practice sessions with:
  - Date and duration
  - Number of questions attempted
  - Accuracy percentage
  - Skills practiced

#### 2. Session Detail View
- Expandable view showing questions from a specific session
- Display question text, student's answer, correct answer
- Visual indicator for correct/incorrect

#### 3. Performance Chart
- Line chart showing accuracy trend over time
- Bar chart showing questions per skill
- Use existing charting library or add lightweight one (recharts)

### Backend Endpoints

#### 1. GET /api/practice-history
- Returns paginated list of practice sessions for a user
- Include session metadata: date, duration, question_count, accuracy

#### 2. GET /api/practice-history/{session_id}
- Returns detailed session data including all questions and answers

### Data Model
Leverage existing MongoDB collections:
- `users` collection already tracks `question_history`
- `dash_questions` / `scraped_questions` for question details

## Technical Approach

1. **Frontend**: Create new React component using existing patterns
   - Use Zustand for state management (already in project)
   - Use React Query for data fetching (already in project)
   - Follow existing Tailwind CSS styling patterns
   - Use Radix UI components for consistency

2. **Backend**: Add endpoints to DashSystem service
   - Aggregate data from existing question_history in users collection
   - Add new endpoints in `services/DashSystem/dash_api.py`

3. **Integration**: Wire up to existing auth system
   - Use existing JWT auth middleware
   - Ensure user can only see their own history

## Acceptance Criteria
- [ ] Practice History panel is accessible from the main UI
- [ ] Shows list of past sessions with key metrics
- [ ] Can drill down into individual sessions
- [ ] Performance chart displays accuracy trends
- [ ] Responsive design matches existing UI
- [ ] Works with existing authentication
- [ ] No breaking changes to existing functionality

## Out of Scope
- Exporting history to PDF/CSV
- Sharing progress with others
- Comparing with other students
