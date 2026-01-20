# Mastery Badges & Gamification - Testing Guide

## Overview

Duolingo-inspired gamification features:
- **Streak Display**: Shows practice streak in header (flame icon + day count)
- **Badges System**: Achievement badges with progress tracking

## How to Test

### 1. Start the Frontend

```bash
cd frontend
npm run dev
```

### 2. What You Should See

**In the Header (top right):**
- **Streak Counter**: Orange pill with flame icon + "5" (mock 5-day streak)
- **Badges Button**: Golden yellow pill with trophy icon + "5" - click to open achievements

**In the Badges Dialog (click trophy button):**
- **12 achievement badges** in a clean grid
- **5 earned badges** (colorful with green checkmark)
- **In-progress badges** (gray with colored progress ring)
- **Locked badges** (gray, no progress)
- **Progress bar** at top showing 5/12 earned

### 3. Badge States

| State | Appearance |
|-------|------------|
| Earned | Colored background, white icon, green checkmark |
| In Progress | Gray background, colored progress ring around edge |
| Locked | Gray background, gray border, no progress |

### 4. Mock Data

The feature uses mock data by default:
- Streak: 5 days current, practiced today (orange/hot state)
- 5 earned badges: First Steps, 3 Day Streak, Week Warrior, 10 Questions, On Fire
- Several in-progress badges with varying completion percentages

### 5. Files Added/Modified

**New Components:**
- `src/components/badges/BadgeDisplay.tsx` - Badge grid with Duolingo-style circles
- `src/components/badges/BadgesDialog.tsx` - Dialog with trophy trigger button
- `src/components/badges/BadgeNotification.tsx` - Toast for new badges
- `src/components/streak/StreakDisplay.tsx` - Streak counter (Duolingo orange style)
- `src/components/streak/StreakCalendar.tsx` - Calendar view

**Hooks:**
- `src/hooks/query-hooks/useBadges.ts` - Badge data fetching
- `src/hooks/query-hooks/useStreak.ts` - Streak data with mock fallback

**Modified:**
- `src/components/header/Header.tsx` - Added StreakDisplay + BadgesDialog
- `src/components/floating-control-panel/FloatingControlPanel.tsx` - Added homeworkPanelOpen state

### 6. Design Principles (Duolingo-inspired)

- **Simple circles** - not complex cards
- **Colorful when earned** - satisfying visual reward
- **Gray when locked** - clear distinction
- **Progress rings** - show how close you are
- **Minimal text** - icons speak for themselves
- **Satisfying interactions** - hover effects, press states

### 7. API Endpoints (for production)

```bash
GET /api/streak          # Current streak data
GET /api/streak/calendar # Practice history calendar
GET /api/badges          # All badges with progress
GET /api/badges/earned   # User's earned badges
POST /api/badges/check   # Check and award new badges
```

### 8. Toggle Mock Data

In `useStreak.ts`:
```typescript
useMockData = true   // Show demo data (default)
useMockData = false  // Use real API
```

## Next Steps

1. Implement backend API endpoints
2. Connect badge checking to question submissions
3. Add celebration animations when badges are earned
4. Add streak freeze/repair features
