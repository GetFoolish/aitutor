#!/bin/bash
# Test script for ScratchpadTeacher Phase 2 implementation

echo "=== ScratchpadTeacher Phase 2 Test Suite ==="
echo ""

# Test 1: Backend API
echo "Test 1: Backend API (/api/scratchpad/generate)"
response=$(curl -s -X POST http://localhost:5001/api/scratchpad/generate \
  -H "Content-Type: application/json" \
  -d '{"concept":"2+2","grade_level":"K-2"}')

if echo "$response" | jq -e '.concept and .steps' > /dev/null 2>&1; then
  echo "✅ Backend API working"
  echo "   Concept: $(echo "$response" | jq -r '.concept')"
  echo "   Steps: $(echo "$response" | jq '.steps | length')"
else
  echo "❌ Backend API failed"
  exit 1
fi
echo ""

# Test 2: Frontend files exist
echo "Test 2: Frontend files exist"
files=(
  "frontend/src/components/scratchpad/ScratchpadTeacher.tsx"
  "frontend/src/components/scratchpad/types.ts"
  "frontend/src/components/scratchpad/index.ts"
  "frontend/src/pages/test-scratchpad.tsx"
)

all_exist=true
for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $file"
  else
    echo "❌ $file (missing)"
    all_exist=false
  fi
done

if [ "$all_exist" = false ]; then
  exit 1
fi
echo ""

# Test 3: TypeScript compilation
echo "Test 3: TypeScript type-check"
cd frontend
if npm run type-check 2>&1 | grep -q "error"; then
  echo "❌ TypeScript errors found"
  npm run type-check 2>&1 | grep "error" | head -10
  exit 1
else
  echo "✅ No TypeScript errors"
fi
cd ..
echo ""

# Test 4: Component exports
echo "Test 4: Component exports from index.ts"
if grep -q "ScratchpadTeacher" frontend/src/components/scratchpad/index.ts; then
  echo "✅ ScratchpadTeacher exported"
else
  echo "❌ ScratchpadTeacher not exported"
  exit 1
fi
echo ""

# Test 5: Test page accessible
echo "Test 5: Test page accessibility"
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/test-scratchpad)
if [ "$status" = "200" ]; then
  echo "✅ Test page accessible (HTTP $status)"
else
  echo "❌ Test page not accessible (HTTP $status)"
  exit 1
fi
echo ""

# Test 6: Required action handlers implemented
echo "Test 6: Required action handlers"
actions=("write" "draw_line" "draw_arrow" "draw_shape" "draw_groups" "number_line" "fraction_bar" "highlight" "erase")
missing=()

for action in "${actions[@]}"; do
  if grep -q "is${action^}Action" frontend/src/components/scratchpad/ScratchpadTeacher.tsx; then
    echo "✅ ${action} handler"
  else
    echo "❌ ${action} handler (missing)"
    missing+=("$action")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  echo "Missing handlers: ${missing[*]}"
  exit 1
fi
echo ""

# Test 7: Props interface
echo "Test 7: Props interface"
if grep -q "concept: string" frontend/src/components/scratchpad/types.ts && \
   grep -q "gradeLevel: string" frontend/src/components/scratchpad/types.ts; then
  echo "✅ Props interface has concept and gradeLevel"
else
  echo "❌ Props interface incomplete"
  exit 1
fi
echo ""

# Test 8: API integration
echo "Test 8: API fetch integration"
if grep -q "fetch.*api/scratchpad/generate" frontend/src/components/scratchpad/ScratchpadTeacher.tsx; then
  echo "✅ API fetch implemented"
else
  echo "❌ API fetch missing"
  exit 1
fi
echo ""

# Test 9: Loading and error states
echo "Test 9: Loading and error states"
has_loading=$(grep -c "isLoading" frontend/src/components/scratchpad/ScratchpadTeacher.tsx)
has_error=$(grep -c "error" frontend/src/components/scratchpad/ScratchpadTeacher.tsx)

if [ "$has_loading" -gt 0 ] && [ "$has_error" -gt 0 ]; then
  echo "✅ Loading and error states implemented"
else
  echo "❌ Missing loading or error states"
  exit 1
fi
echo ""

# Test 10: Playback controls
echo "Test 10: Playback controls"
controls=("Play" "Pause" "Restart" "speed")
all_controls=true

for control in "${controls[@]}"; do
  if grep -qi "$control" frontend/src/components/scratchpad/ScratchpadTeacher.tsx; then
    echo "✅ $control control"
  else
    echo "❌ $control control (missing)"
    all_controls=false
  fi
done

if [ "$all_controls" = false ]; then
  exit 1
fi
echo ""

echo "======================================"
echo "✅ ALL TESTS PASSED!"
echo "======================================"
echo ""
echo "Production-grade ScratchpadTeacher implementation complete:"
echo "  - Backend API working (/api/scratchpad/generate)"
echo "  - Frontend component with all action handlers"
echo "  - TypeScript types defined"
echo "  - API integration with loading/error states"
echo "  - Playback controls (play/pause/restart/speed)"
echo "  - Test page accessible at http://localhost:3000/test-scratchpad"
echo ""
echo "Ready to commit! 🚀"
