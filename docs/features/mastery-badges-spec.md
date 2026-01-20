# Feature: Mastery Badges & Gamification System

## Overview
Add a gamification system with visual badges and achievements to motivate K-12 students. Display earned badges prominently and track progress toward new achievements.

## Requirements

### Backend (FastAPI)
1. Create `services/DashSystem/badges.py` with badge definitions:
   - Skill mastery badges (Bronze/Silver/Gold for 50%/75%/90% mastery)
   - Streak badges (3-day, 7-day, 30-day streaks)
   - Question count badges (10, 50, 100, 500 questions answered)
   - Perfect score badges (5, 10, 25 perfect answers in a row)

2. Add badge tracking to user profile in `managers/user_manager.py`:
   - `earned_badges: List[str]` - list of earned badge IDs
   - `badge_progress: Dict[str, int]` - progress toward each badge

3. Create API endpoints in `services/DashSystem/dash_api.py`:
   - `GET /api/badges` - Get all available badges with user progress
   - `GET /api/badges/earned` - Get user's earned badges
   - `POST /api/badges/check` - Check and award new badges after question answer

### Frontend (React/TypeScript)
1. Create `frontend/src/components/badges/BadgeDisplay.tsx`:
   - Grid display of badge icons with earned/locked states
   - Progress bars for partially-earned badges
   - Celebration animation when new badge earned

2. Create `frontend/src/components/badges/BadgeNotification.tsx`:
   - Toast notification when badge is earned
   - Confetti animation effect

3. Create `frontend/src/hooks/query-hooks/useBadges.ts`:
   - React Query hooks for badge data fetching

4. Add badge summary to Header component showing recent achievements

## Technical Notes
- Use existing user_manager.py UserProfile model
- Badges should be checked after each question submission
- Store badge definitions in a JSON/Python dict for easy updates
- Use shadcn/ui components for consistent styling

## Files to Create/Modify
- NEW: `services/DashSystem/badges.py`
- NEW: `frontend/src/components/badges/BadgeDisplay.tsx`
- NEW: `frontend/src/components/badges/BadgeNotification.tsx`
- NEW: `frontend/src/hooks/query-hooks/useBadges.ts`
- MODIFY: `services/DashSystem/dash_api.py` - add badge endpoints
- MODIFY: `managers/user_manager.py` - add badge fields to UserProfile
- MODIFY: `frontend/src/components/header/Header.tsx` - add badge summary
