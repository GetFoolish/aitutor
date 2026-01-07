# Athena Standalone Tool & Perseus Removal Plan

**Date:** January 2026
**Branch:** `gagan-perseus-fixed` → `v1` → `main`
**Author:** Developer Prompt

---

## Goal

1. Create a standalone "Athena Testing Tool" that runs **completely independently** (with its own backend, includes Perseus for comparison)
2. Remove Perseus from the main app's QuestionPane - use **Athena only**
3. Remove all Perseus code from the main repo (except what's in the standalone tool)
4. Clean up QuestionPane.tsx to be Athena-only (keep debug features behind `?debug=true` flag)
5. Merge changes: `gagan-perseus-fixed` → `v1` → eventually to `main`

---

## Phase 1: Create Standalone Athena Testing Tool

### Create new directory structure:
```
tools/athena-testing-tool/
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Simple app with just the testing page
│   │   ├── index.tsx                  # Entry point
│   │   ├── components/
│   │   │   └── AthenaTestPane.tsx     # Copy of QuestionPane.tsx (KEEP Perseus comparison)
│   │   ├── renderer/
│   │   │   └── athena/                # COPY entire folder from frontend/src/renderer/athena/
│   │   ├── services/
│   │   │   └── athenaAPI/             # COPY from frontend/src/services/athenaAPI/
│   │   └── package/
│   │       └── perseus/               # COPY entire Perseus package for comparison mode
│   ├── public/
│   ├── package.json                   # Standalone dependencies
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── index.html
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app (COPY from services/athenaAPI/app/)
│   │   ├── routes.py                  # API routes
│   │   └── question_loader.py         # Question fetching & conversion
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── mongodb_manager.py         # COPY from managers/
│   │   ├── cors_config.py             # COPY from shared/
│   │   └── logging_config.py          # COPY from shared/
│   ├── run_backend.py                 # Entry point (runs on port 8010)
│   └── requirements.txt               # FastAPI, PyMongo, uvicorn, etc.
├── .env.example                       # MONGODB_URI, API ports, etc.
├── README.md                          # How to run the standalone tool
└── run.sh                             # Script to start both frontend (port 3001) & backend (port 8010)
```

### Files to COPY:

| Source | Destination |
|--------|-------------|
| `frontend/src/renderer/athena/` | `tools/athena-testing-tool/frontend/src/renderer/athena/` |
| `frontend/src/services/athenaAPI/` | `tools/athena-testing-tool/frontend/src/services/athenaAPI/` |
| `frontend/src/package/perseus/` | `tools/athena-testing-tool/frontend/src/package/perseus/` |
| `frontend/src/components/question-pane/QuestionPane.tsx` | `tools/athena-testing-tool/frontend/src/components/AthenaTestPane.tsx` |
| `services/athenaAPI/app/` | `tools/athena-testing-tool/backend/app/` |
| `services/athenaAPI/run_backend.py` | `tools/athena-testing-tool/backend/run_backend.py` |
| `managers/mongodb_manager.py` | `tools/athena-testing-tool/backend/shared/mongodb_manager.py` |
| `shared/cors_config.py` | `tools/athena-testing-tool/backend/shared/cors_config.py` |
| `shared/logging_config.py` | `tools/athena-testing-tool/backend/shared/logging_config.py` |

### Standalone package.json dependencies:
```json
{
  "name": "athena-testing-tool",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite --port 3001",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@khanacademy/perseus": "68.0.2",
    "@khanacademy/perseus-core": "19.0.2",
    "@khanacademy/math-input": "26.2.4",
    "@khanacademy/wonder-blocks-core": "^10.1.0",
    "@khanacademy/kas": "2.1.1",
    "@khanacademy/kmath": "2.2.4",
    "@khanacademy/simple-markdown": "2.1.0",
    "katex": "^0.16.9",
    "mathquill": "^0.10.1",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-router-dom": "^6.22.0",
    "lucide-react": "^0.447.0",
    "tailwindcss": "^4.1.17"
  }
}
```

### Standalone requirements.txt:
```
fastapi==0.116.2
uvicorn==0.35.0
pymongo==4.15.4
python-dotenv==1.1.1
pydantic==2.11.9
```

### run.sh script:
```bash
#!/bin/bash
# Start Athena Testing Tool

echo "Starting Athena Testing Tool..."

# Start backend
echo "Starting backend on port 8010..."
cd backend && python run_backend.py &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on port 3001..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Athena Testing Tool running at: http://localhost:3001"
echo "Backend API at: http://localhost:8010"
echo ""
echo "Press Ctrl+C to stop..."

wait
```

---

## Phase 2: Clean Up Main App QuestionPane

### File: `frontend/src/components/question-pane/QuestionPane.tsx`

#### 2.1 REMOVE Perseus imports (lines ~51-58):
```typescript
// DELETE these lines:
import { ServerItemRenderer } from '../../package/perseus/src/server-item-renderer';
import { storybookDependenciesV2 } from '../../package/perseus/testing/test-dependencies';
import { RenderStateRoot } from '@khanacademy/wonder-blocks-core';
import { PerseusI18nContextProvider } from '../../package/perseus/src/components/i18n-context';
import { mockStrings } from '../../package/perseus/src/strings';
```

#### 2.2 REMOVE ViewMode type and state:
```typescript
// DELETE this type:
type ViewMode = 'athena' | 'perseus' | 'comparison';

// DELETE this state:
const [viewMode, setViewMode] = useState<ViewMode>('athena');
```

#### 2.3 REMOVE from UI (keep debug behind flag):
- **DELETE:** View mode toggle buttons (Athena/Perseus/Compare) - lines ~1749-1782
- **DELETE:** Perseus renderer JSX blocks (`viewMode === 'perseus'` and `viewMode === 'comparison'`)
- **DELETE:** Input Window button (Perseus storybook link)
- **KEEP (behind `showDebugUI` flag):** JSON viewer, Question ID display, Widget filter dropdown

#### 2.4 SIMPLIFY rendering to Athena-only:
```tsx
{/* Main Content - Athena Only */}
<div className="px-6 py-6 md:px-8 md:py-8">
  <RendererErrorBoundary
    key={`athena-${currentQuestion._id}-${rendererKey}`}
    name="Athena"
    onRetry={() => setRendererKey(k => k + 1)}
  >
    <AthenaRenderer
      item={{
        question: currentQuestion.question as any,
        hints: currentQuestion.hints as any,
        answerArea: currentQuestion.answerArea,
      }}
      onAnswerChange={handleAnswerChange}
      readOnly={isSubmitted}
      reviewMode={isSubmitted}
      theme={darkMode ? 'dark' : 'light'}
    />
  </RendererErrorBoundary>
</div>
```

#### 2.5 Keep debug UI behind flag (already exists):
```typescript
// This already exists - keep it:
const showDebugUI = import.meta.env.DEV || window.location.search.includes('debug=true');

// Wrap debug features with:
{showDebugUI && (
  // ObjectID search, widget filter, JSON viewer, etc.
)}
```

**Estimated reduction:** ~500-700 lines removed

---

## Phase 3: Remove Perseus from Main Repo

### 3.1 DELETE entire Perseus package:
```bash
rm -rf frontend/src/package/perseus/
```

### 3.2 Update `frontend/package.json` - REMOVE these dependencies:
```json
// REMOVE these:
"@khanacademy/perseus": "68.0.2",
"@khanacademy/perseus-core": "19.0.2",
"@khanacademy/perseus-utils": "2.1.0",
"@khanacademy/wonder-blocks-core": "...",
"@khanacademy/wonder-blocks-i18n": "...",
// And any other @khanacademy packages NOT used by Athena renderer
```

**Note:** Check which @khanacademy packages Athena actually needs before removing. The Athena renderer might use some math-related packages.

### 3.3 Search for remaining Perseus references:
```bash
# Run these to find any remaining imports:
grep -r "from.*perseus" frontend/src/ --include="*.ts" --include="*.tsx"
grep -r "ServerItemRenderer" frontend/src/
grep -r "PerseusI18n" frontend/src/
grep -r "@khanacademy/wonder-blocks" frontend/src/
```

### 3.4 Clean up any other files with Perseus imports:
- `frontend/src/index.tsx` - Remove Perseus route if any
- `frontend/src/App.tsx` - Remove Perseus renderer option handling
- Any test files referencing Perseus

---

## Phase 4: Update Routes & App Config

### File: `frontend/src/index.tsx`

**Current (likely):**
```tsx
<Route exact path="/test/athena" component={QuestionPane} />
<Route exact path="/test/simple" component={SimpleTest} />  // Maybe uses Perseus?
```

**After cleanup:**
- Keep `/test/athena` route pointing to cleaned-up QuestionPane
- Remove `/test/simple` if it uses Perseus
- Remove any `?renderer=perseus` query param handling in App.tsx

---

## Phase 5: Git Workflow

### Step 1: Create standalone tool first (on `gagan-perseus-fixed`)
```bash
git checkout gagan-perseus-fixed

# Create standalone tool directory and copy files
mkdir -p tools/athena-testing-tool/{frontend,backend}
# ... copy all files as listed in Phase 1

git add tools/athena-testing-tool/
git commit -m "feat: create standalone athena testing tool with independent backend"
```

### Step 2: Clean up main app (on `gagan-perseus-fixed`)
```bash
# Remove Perseus from QuestionPane
# Remove Perseus package folder
# Update package.json

git add -A
git commit -m "feat: remove perseus from main app, athena-only rendering"
```

### Step 3: Merge to v1
```bash
git checkout v1
git pull origin v1

# Merge with strategy to favor our changes
git merge gagan-perseus-fixed

# Resolve conflicts - v1 has older code
# Key conflict areas: QuestionPane.tsx, package.json, App.tsx
# Generally prefer gagan-perseus-fixed changes

git push origin v1
```

### Step 4: Test on v1
- Run main app, verify Athena rendering works
- Run standalone tool, verify Perseus comparison works
- Run `npm run build` to ensure no broken imports

### Step 5: Eventually merge v1 to main
```bash
git checkout main
git merge v1
git push origin main
```

---

## Critical Files to Modify

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/components/question-pane/QuestionPane.tsx` | **MODIFY** | Remove Perseus, keep Athena only |
| `frontend/src/package/perseus/` | **DELETE** | Entire folder (~100+ files) |
| `frontend/package.json` | **MODIFY** | Remove Perseus dependencies |
| `frontend/src/index.tsx` | **MODIFY** | Update routes |
| `frontend/src/App.tsx` | **MODIFY** | Remove Perseus renderer option |
| `tools/athena-testing-tool/` | **CREATE** | New standalone tool (copy files) |

---

## Testing Checklist

### Main App (after cleanup):
- [ ] QuestionPane renders questions with Athena only
- [ ] Debug UI shows only when `?debug=true` is in URL
- [ ] `npm run build` succeeds with no Perseus references
- [ ] `grep -r "perseus" frontend/src/` returns no results (except comments)
- [ ] All widget types render correctly in Athena
- [ ] Scoring/validation works correctly
- [ ] Dark mode works

### Standalone Tool:
- [ ] `tools/athena-testing-tool/` runs independently
- [ ] Backend starts on port 8010
- [ ] Frontend starts on port 3001
- [ ] Athena/Perseus/Compare toggle works
- [ ] JSON viewer works
- [ ] Input Window (Perseus Storybook) button works
- [ ] Can fetch questions from MongoDB

### Git Workflow:
- [ ] `gagan-perseus-fixed` has all changes committed
- [ ] Successfully merged to `v1`
- [ ] `v1` passes all tests
- [ ] Ready for eventual merge to `main`

---

## Rollback Plan

If issues arise after merge:
```bash
# Revert to before the merge
git checkout v1
git reset --hard HEAD~1  # Or specific commit hash
git push origin v1 --force  # CAUTION: force push

# Or create a revert commit
git revert <merge-commit-hash>
```

---

## Estimated Effort

| Phase | Estimated Time |
|-------|---------------|
| Phase 1: Create standalone tool | 2-3 hours |
| Phase 2: Clean up QuestionPane | 1-2 hours |
| Phase 3: Remove Perseus | 30 mins |
| Phase 4: Update routes | 30 mins |
| Phase 5: Git workflow & testing | 1-2 hours |
| **Total** | **5-8 hours** |
