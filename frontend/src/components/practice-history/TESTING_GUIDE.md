# Practice History Dashboard - Testing Guide

## Overview

The Practice History Dashboard allows students to view their past practice sessions, including:
- Session dates and durations
- Number of questions attempted
- Accuracy percentage
- Skills practiced

## How to Test

### 1. Start the Services

```bash
# Terminal 1: Start DASH API
cd services/DashSystem
python dash_api.py

# Terminal 2: Start Frontend
cd frontend
npm run dev
```

### 2. Access the Feature

1. Open http://localhost:3000
2. Log in with a test account
3. The Practice History panel appears on the right side
4. Click the toggle button (History icon) to open/close the panel

### 3. What You Should See

**With Mock Data (default):**
- 5 demo practice sessions
- Sessions from "1 hour ago" to "5 days ago"
- Accuracy ranging from 64% to 100%
- Various skills like "Addition Within 20", "Fractions Basics", etc.

**With Real Data:**
- Your actual practice sessions grouped by 30-minute gaps
- Real accuracy based on correct/incorrect answers
- Skills you actually practiced

### 4. UI Components

| Component | Location | Description |
|-----------|----------|-------------|
| `PracticeHistoryPanel` | Right sidebar | Main panel with session list |
| `SessionDetailView` | Panel expansion | Detailed view of a session |
| `PerformanceChart` | Detail view | Visual chart of performance |

### 5. API Endpoints

```bash
# Get paginated practice history
GET /api/practice-history?page=1&limit=10

# Get session details
GET /api/practice-history/{session_id}
```

### 6. Toggle Mock Data

In `usePracticeHistory.ts`, change `useMockData` default:

```typescript
// Show mock data (for demo)
useMockData = true

// Show real data (for production)
useMockData = false
```

### 7. Files Modified

**Frontend:**
- `src/components/practice-history/PracticeHistoryPanel.tsx` - Main panel
- `src/components/practice-history/SessionDetailView.tsx` - Session details
- `src/components/practice-history/PerformanceChart.tsx` - Charts
- `src/hooks/query-hooks/usePracticeHistory.ts` - Data fetching hook
- `src/App.tsx` - Integration

**Backend:**
- `services/DashSystem/dash_api.py` - API endpoints (to be added for production)

## Known Issues

- Backend endpoints not yet added (using mock data)
- Panel positioning may need adjustment on smaller screens

## Next Steps

1. Add backend `/api/practice-history` endpoints to `dash_api.py`
2. Connect to real MongoDB question_history data
3. Add loading states and error handling
4. Add pagination controls
