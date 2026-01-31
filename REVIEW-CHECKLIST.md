# UI/UX Review Checklist for AITutor

This checklist contains SPECIFIC, MEASURABLE criteria. Do not approve unless ALL items pass.

---

## 0. CRITICAL PRE-CHECKS (MUST PASS BEFORE ANYTHING ELSE)

### Visual Verification (REQUIRED - NO EXCEPTIONS)

**You MUST take a screenshot of http://localhost:3000/app/assessment/dynamic**

If you cannot take a screenshot:
- REJECT immediately with: "Cannot access browser. Visual verification impossible."
- DO NOT fall back to API-only testing
- DO NOT approve without seeing the page

### Screenshot Analysis Checklist

Look at the screenshot and answer YES/NO:

1. [ ] Is there a question displayed?
2. [ ] Are there answer choices visible (radio buttons, text input)?
3. [ ] Do you see "No answer choices available"? (If YES → CRITICAL FAIL)
4. [ ] Do you see "question data is incomplete"? (If YES → CRITICAL FAIL)
5. [ ] Do you see any error messages?
6. [ ] Is there a submit button?

**IF #3 or #4 is YES:**
- REJECT with: "CRITICAL: Answer input missing. Question data malformed."
- Point to: `content/question_generator.py` validation or API response

### Test User Flow (In Browser)

1. [ ] Click a subject button (math/science/reading)
2. [ ] Click "let's go!" button
3. [ ] Verify question loads with answer options
4. [ ] Click an answer choice
5. [ ] Click submit button
6. [ ] Verify feedback appears

If any step fails → REJECT with which step failed

### Critical Rules

1. You may ONLY approve if ALL pre-checks pass
2. "API returns 200" is NOT sufficient
3. "Code looks correct" is NOT sufficient
4. You MUST verify the RENDERED OUTPUT
5. If browser fails, you CANNOT approve

---

## 1. Spacing (8pt Grid) - MANDATORY

**Rule**: All spacing must be multiples of 8px (8, 16, 24, 32, 40, 48, 56, 64).

### Check in Code
Search for these patterns and FLAG any violations:
```
padding: [0-9]+px  -> Must be 8, 16, 24, 32, 40, 48, 56, 64
margin: [0-9]+px   -> Must be 8, 16, 24, 32, 40, 48, 56, 64
gap: [0-9]+px      -> Must be 8, 16, 24, 32, 40, 48
```

### FAIL if you find:
- `padding: 10px` or `padding: 20px` or `padding: 15px`
- `margin: 12px` or `margin: 18px` or `margin: 30px`
- Any non-8-multiple spacing values

### Exception
4px and 12px allowed ONLY for:
- Icon padding inside buttons
- Small inline element gaps
- Badge internal padding

---

## 2. Typography - MANDATORY

### Allowed Font Sizes
```
12px - captions only
14px - labels, small text
16px - body text (MINIMUM)
18px - large body
20px, 24px, 32px, 40px, 48px - headings
```

### Check in Code
- [ ] No `font-size` below 12px
- [ ] Body text is 16px minimum
- [ ] Headings follow scale (20, 24, 32, 40, 48)
- [ ] Line-height is 1.5 for body, 1.2 for headings
- [ ] Maximum 2 font families

### FAIL if you find:
- `font-size: 13px` or `font-size: 15px` or `font-size: 11px`
- Body text smaller than 16px
- Random heading sizes like 22px, 28px, 35px

---

## 3. Neo-Brutalist Consistency - MANDATORY

### Border Rules
```css
Cards/Buttons: border: 3px solid #000
Secondary:     border: 2px solid #000
```

### Shadow Rules
```css
Large cards:   box-shadow: 6px 6px 0 #000
Standard:      box-shadow: 4px 4px 0 #000
Small:         box-shadow: 2px 2px 0 #000
```

### Border Radius
```css
Cards:   border-radius: 12px or 16px
Buttons: border-radius: 12px
Pills:   border-radius: 999px
```

### Check in Code
- [ ] All cards have 3px black borders
- [ ] All interactive cards have offset shadows
- [ ] No blur shadows (box-shadow with blur value)
- [ ] No gray borders
- [ ] Consistent border-radius (no 5px, 10px, 15px)

### FAIL if you find:
- `border: 1px solid #ccc`
- `box-shadow: 0 2px 4px rgba(0,0,0,0.1)` (blur shadow)
- `border-radius: 5px` or `border-radius: 10px`

---

## 4. Color Consistency - MANDATORY

### Primary Palette
```
Primary:    #6C63FF (buttons, links, CTAs)
Background: #FFFDF5 (main background)
Surface:    #FFFFFF (cards)
Surface 2:  #F5F5F5 (secondary areas)
Border:     #000000 (all borders)
Text:       #000000, #666666, #888888
Success:    #4CAF50
Warning:    #FF9800
Error:      #F44336
```

### Check in Code
- [ ] Primary buttons use #6C63FF
- [ ] All borders are #000 (black)
- [ ] Text uses only #000, #666, or #888
- [ ] Success/error states use semantic colors
- [ ] No more than 6 total colors used

### FAIL if you find:
- Random colors like #5a5a5a, #333, #444
- Different blues for different buttons
- Gray borders instead of black

---

## 5. Component Consistency - MANDATORY

### All Primary Buttons Must Have:
```css
padding: 16px 24px;
font-size: 16px or 18px;
font-weight: 700;
background: #6C63FF;
color: white;
border: 3px solid #000;
border-radius: 12px;
box-shadow: 4px 4px 0 #000;
```

### All Cards Must Have:
```css
background: #fff;
border: 3px solid #000;
border-radius: 12px or 16px;
padding: 24px or 32px or 48px;
box-shadow: 4px 4px 0 #000 or 6px 6px 0 #000;
```

### Check in Browser
- [ ] Open each screen
- [ ] Compare buttons - do they ALL look identical?
- [ ] Compare cards - same border, shadow, padding?
- [ ] Check hover states - all work the same way?

### FAIL if:
- One button has different padding than another
- Cards have different shadow offsets
- Some cards have borders, others don't

---

## 6. Hover States - MANDATORY

### Standard Hover Effect
```css
/* On hover, element shifts and shadow reduces */
transform: translate(2px, 2px);
box-shadow: 2px 2px 0 #000; /* was 4px 4px */
```

### Check in Browser
- [ ] Hover over EVERY button - does it respond?
- [ ] Hover over EVERY card - consistent effect?
- [ ] No elements without hover feedback

### FAIL if:
- Some buttons have hover, others don't
- Inconsistent hover effects
- No visual feedback on interactive elements

---

## 7. Educational App Requirements

### Tone of Voice
- [ ] All text is friendly (not formal)
- [ ] Encouraging language (not condescending)
- [ ] Simple vocabulary for children
- [ ] Lowercase preferred for casual feel

### PASS Examples:
```
"nice job!"
"let's try another one"
"you got this!"
"almost there!"
```

### FAIL Examples:
```
"Correct Answer"
"Assessment Complete"
"Submit Response"
"Error: Invalid Input"
```

### Feedback for Wrong Answers
- [ ] Message is encouraging, not shaming
- [ ] Provides helpful hint or guidance
- [ ] Uses gentle language

### FAIL if:
- "Wrong" or "Incorrect" without encouragement
- No hint provided
- Harsh or formal language

---

## 8. Loading States - MANDATORY

### Every Async Action Must Have:
- Loading indicator visible
- Button disabled during loading
- Meaningful loading text

### Check:
- [ ] Assessment loading shows spinner
- [ ] Submit button shows loading state
- [ ] API calls show feedback

### FAIL if:
- Button can be clicked multiple times
- No visual feedback during loading
- User doesn't know something is happening

---

## 9. Specific File Checks

### DynamicAssessment.tsx
Run these specific checks:

1. **Search for bad padding values:**
   ```
   padding: '20px'  -> Should be 24px
   padding: '40px'  -> Should be 48px
   padding: '60px'  -> Should be 64px
   ```

2. **Check card consistency:**
   - Intro card padding: should be 48px
   - Question card padding: should be 24px
   - Results card padding: should be 48px

3. **Check button consistency:**
   - All "let's go" type buttons: same style
   - All "back" buttons: same outline style

### Other Components
- LearnerOnboarding.tsx: same spacing rules
- AssessmentResults.tsx: same card styles
- Header.tsx: consistent with design system

---

## 10. Browser Testing Checklist

### For Each Screen, Verify:

1. **Visual Alignment**
   - [ ] Elements align to invisible grid
   - [ ] Consistent spacing between sections
   - [ ] No elements awkwardly close to edges

2. **Color Consistency**
   - [ ] All buttons same color
   - [ ] All borders black
   - [ ] Text colors consistent

3. **Interactive States**
   - [ ] All buttons have hover effect
   - [ ] All cards respond to interaction
   - [ ] Focus states visible

4. **Typography**
   - [ ] Headings clearly larger than body
   - [ ] Text is readable (not too small)
   - [ ] Consistent font weights

5. **No Console Errors**
   - [ ] Open DevTools Console
   - [ ] Navigate through flow
   - [ ] Zero JavaScript errors

---

## Approval Criteria

### APPROVE only if ALL of the following are true:
1. Zero spacing violations (8pt grid)
2. Zero typography violations
3. 100% border/shadow consistency
4. All buttons look identical
5. All cards look identical
6. All hover states work
7. Tone is friendly/encouraging
8. No console errors

### REJECT and provide specific feedback:
```
REJECT: Found these issues:
- Line 401 in DynamicAssessment.tsx: padding: '40px' should be '48px'
- Line 509: padding: '20px 24px' should be '24px'
- Intro card shadow is 6px, question card shadow is 4px - inconsistent
- "Submit Answer" button text should be lowercase: "submit answer" or "check answer"
```

---

## Reference

See DESIGN-SYSTEM.md for full color palette, spacing scale, and component specs.
