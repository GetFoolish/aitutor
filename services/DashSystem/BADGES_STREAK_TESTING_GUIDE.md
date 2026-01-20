# Badges & Streak System Testing Guide

This guide covers testing the gamification features: badges, streaks, and progress tracking.

## Overview

The gamification system consists of:
1. **Streak Tracking** - Daily practice streaks (Duolingo-style)
2. **Badges System** - Achievements for various milestones
3. **Progress Tracking** - Real-time progress towards badges

## Prerequisites

1. **MongoDB** running with question_attempts collection
2. **DashSystem service** running on port 8000
3. **Frontend** running on port 5173
4. A test user with JWT authentication

## Quick Start

### 1. Start the DashSystem Service

```bash
cd services/DashSystem
python dash_api.py
```

The service runs on `http://localhost:8000`

### 2. Start the Frontend

```bash
cd frontend
npm run dev
```

### 3. Verify Endpoints

```bash
# Check streak endpoint
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:8000/api/streak

# Check badges endpoint
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:8000/api/badges

# Check earned badges
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:8000/api/badges/earned

# Check/award new badges
curl -X POST -H "Authorization: Bearer <your-jwt-token>" http://localhost:8000/api/badges/check

# Get calendar heatmap data
curl -H "Authorization: Bearer <your-jwt-token>" http://localhost:8000/api/streak/calendar
```

## API Endpoints

### Streak Endpoints

#### GET /api/streak
Returns current streak data.

**Response:**
```json
{
  "current_streak": 5,
  "longest_streak": 12,
  "last_practice_date": "2024-01-20",
  "streak_history": ["2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19", "2024-01-20"]
}
```

#### GET /api/streak/calendar
Returns practice dates for calendar heatmap.

**Response:**
```json
{
  "practice_dates": ["2024-01-10", "2024-01-12", "2024-01-15", "2024-01-16", "2024-01-17"]
}
```

### Badge Endpoints

#### GET /api/badges
Returns all available badges with user progress.

**Response:**
```json
{
  "available_badges": [
    {
      "badge_id": "first_steps",
      "name": "First Steps",
      "description": "Answer your first question",
      "badge_type": "question_count",
      "icon": "🚀",
      "requirement": 1,
      "tier": "bronze"
    }
  ],
  "user_progress": {
    "first_steps": {
      "current": 15,
      "required": 1,
      "percentage": 100,
      "earned": true
    }
  },
  "earned_badges": ["first_steps", "practice_10"]
}
```

#### GET /api/badges/earned
Returns only the badges user has earned.

**Response:**
```json
{
  "earned_badges": [
    {
      "badge_id": "first_steps",
      "name": "First Steps",
      "description": "Answer your first question",
      "badge_type": "question_count",
      "icon": "🚀",
      "requirement": 1,
      "tier": "bronze"
    }
  ],
  "total_count": 2
}
```

#### POST /api/badges/check
Check and award any new badges based on current progress.

**Response:**
```json
{
  "newly_earned": ["practice_50"],
  "badge_progress": {
    "first_steps": { "current": 52, "required": 1, "percentage": 100, "earned": true },
    "practice_50": { "current": 52, "required": 50, "percentage": 100, "earned": true }
  }
}
```

## Available Badges

| Badge ID | Name | Type | Requirement | Tier |
|----------|------|------|-------------|------|
| first_steps | First Steps | question_count | 1 | bronze |
| practice_10 | Getting Started | question_count | 10 | bronze |
| practice_50 | Dedicated Learner | question_count | 50 | silver |
| practice_100 | Century Club | question_count | 100 | gold |
| streak_3 | On Fire | streak | 3 days | bronze |
| streak_7 | Week Warrior | streak | 7 days | silver |
| streak_30 | Monthly Master | streak | 30 days | gold |
| perfect_5 | Sharp Mind | perfect_score | 5 in a row | bronze |
| perfect_10 | Perfectionist | perfect_score | 10 in a row | silver |

## Frontend Components

### StreakDisplay
Located in `frontend/src/components/streak/StreakDisplay.tsx`

Duolingo-inspired flame icon showing:
- Current streak count
- Orange flame when practiced today
- Gray flame when streak at risk (didn't practice today)

### BadgeDisplay
Located in `frontend/src/components/badges/BadgeDisplay.tsx`

Circular badges with:
- Progress ring for partially complete badges
- Full color and glow for earned badges
- Grayscale for locked badges
- Green checkmark for earned

### BadgesDialog
Located in `frontend/src/components/badges/BadgesDialog.tsx`

Modal showing all badges with:
- Grid layout of all available badges
- Progress indicators
- Badge details on hover

## Testing Scenarios

### 1. Test Streak Display
1. Answer at least one question today
2. Check header - flame should be orange
3. Wait until tomorrow without practicing
4. Flame should turn gray (streak at risk)

### 2. Test Badge Earning
1. Answer your first question
2. Call `/api/badges/check`
3. Verify "first_steps" badge is awarded
4. UI should show notification

### 3. Test Streak Calculation
1. Practice on consecutive days
2. Verify `current_streak` increases
3. Miss a day
4. Verify streak resets to 0

### 4. Test Perfect Streak
1. Answer 5 questions correctly in a row
2. Call `/api/badges/check`
3. Verify "perfect_5" badge is awarded

## Mock Data Mode

Frontend hooks default to `useMockData = true` for demo purposes.

To test with real backend:
```typescript
// In your component
const { data } = useStreak({ userId: "test", useMockData: false });
```

## Troubleshooting

### Streak showing 0 when it shouldn't
1. Check `question_attempts` collection has data
2. Verify timestamps are stored correctly
3. Check timezone handling

### Badges not being awarded
1. Verify `users` collection exists
2. Check `/api/badges/check` is being called after answering questions
3. Look at backend logs for errors

### UI not updating
1. React Query might be caching - try hard refresh
2. Check if `useMockData` is set to `true`
3. Verify backend is actually running

## Files Modified

### Backend (DashSystem)
- `dash_api.py` - Added streak and badge endpoints

### Frontend
- `src/hooks/query-hooks/useStreak.ts` - Streak data fetching
- `src/hooks/query-hooks/useBadges.ts` - Badge data fetching
- `src/components/streak/StreakDisplay.tsx` - Streak UI (Duolingo-style)
- `src/components/badges/BadgeDisplay.tsx` - Badge grid
- `src/components/badges/BadgesDialog.tsx` - Badge modal
- `src/components/header/Header.tsx` - Integration point

## Contact

For issues with this implementation, check the git history on `v1-mastery-badges` branch.
