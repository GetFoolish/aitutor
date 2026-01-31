# Memory Pipeline Verification Checklist

## How to Run the Test

1. **Start the TeachingAssistant API:**
   ```bash
   cd /Users/gaganarora/Desktop/Autocode/aitutor
   python3 -m uvicorn services.TeachingAssistant.api:app --host 0.0.0.0 --port 8002 --reload
   ```

2. **Run the Simulator (in another terminal):**
   ```bash
   cd /Users/gaganarora/Desktop/Autocode/aitutor
   python3 services/TeachingAssistant/Simulator.py --mode automatic --user-id maya_test_001 --clean
   ```

3. **Check the Biography (after simulator completes):**
   - Use the frontend console: `window.memoryDebug.getBiography()`
   - Or call the API: `curl http://localhost:8002/student/biography -H "Authorization: Bearer <token>"`

---

## Session 1 Facts to Verify
After running session 1, the biography/memories should contain:

### Personal Information
- [ ] **Name:** Maya
- [ ] **Grade:** 10th grade / Sophomore
- [ ] **School:** Lincoln High School
- [ ] **Location:** Portland, Oregon
- [ ] **Previous Location:** San Francisco (moved at age 10)
- [ ] **Best Friend:** Lily (from SF, talks on Discord)

### Interests & Hobbies
- [ ] **Art:** Digital art, uses Procreate on iPad
- [ ] **Career Goal:** Concept artist for video games
- [ ] **Games:** Stardew Valley, Zelda, Animal Crossing
- [ ] **Sport:** Soccer, midfielder position
- [ ] **Practice Days:** Tuesdays and Thursdays

### Academic
- [ ] **Struggles with:** Math, specifically quadratics
- [ ] **Failed Test:** Got 52%, cried in bathroom
- [ ] **Learning Style:** Visual learner, prefers colors and diagrams

### Family (Partial)
- [ ] **Dad's Name:** David Chen
- [ ] **Dad's Job:** Software engineer at Intel
- [ ] **Dad's Personality:** Logical, "fix mode"

### Pet
- [ ] **Dog's Name:** Biscuit
- [ ] **Breed:** Corgi
- [ ] **Age:** 3 years old
- [ ] **Adopted:** From shelter when Maya was 12
- [ ] **Quirk:** Afraid of thunder, sleeps in Maya's room

---

## Session 2 Facts to Verify
Additional facts revealed in session 2:

### Family (Complete)
- [ ] **Mom's Name:** Sarah Chen (née Williams)
- [ ] **Mom's Job:** Pediatric nurse at OHSU hospital
- [ ] **Mom's Personality:** Warm, emotional, supportive
- [ ] **Brother's Name:** Ethan
- [ ] **Brother's Age:** 11 years old
- [ ] **Brother's Interest:** Obsessed with Minecraft
- [ ] **Grandmother:** Nai Nai (paternal grandmother)
- [ ] **Nai Nai speaks:** Mandarin

### Life Events
- [ ] **Art Contest Win:** Age 13, city-wide competition
- [ ] **Museum Display:** Portland Art Museum for one month
- [ ] **Dad took day off:** For the art ceremony

### Emotional/Relational
- [ ] **Dad vs Mom dynamic:** Dad logical, Mom emotional
- [ ] **Feels like disappointment:** Compared to engineer dad
- [ ] **Secret sibling appreciation:** Would miss Ethan if gone

### Grandmother Health
- [ ] **Nai Nai's stroke:** About 3 months ago
- [ ] **Maya's response:** Took over some cooking traditions
- [ ] **Baking skill:** Makes mooncakes and sesame cookies

---

## Session 3 Facts to Verify
Emotional deep dive:

### Academic Trauma
- [ ] **Test Anxiety:** Performance anxiety before tests
- [ ] **Same with Soccer:** Gets nervous before big games

### Sports Injury
- [ ] **ACL Tear:** Championship game at age 14
- [ ] **Recovery Time:** 6 months
- [ ] **Almost Quit:** Soccer entirely
- [ ] **Support:** Mom drove to physical therapy, Biscuit sat with her

### Emotional Patterns
- [ ] **Fear of not being good enough:** Core anxiety
- [ ] **Compares self to Dad:** Engineer vs creative
- [ ] **Compares self to Ethan:** Brother doing algebra in 6th grade

### Career/Future
- [ ] **Dad's view on art:** "Have a backup plan"
- [ ] **Conflict:** Wants art career, dad wants STEM options

---

## Session 4 Facts to Verify
Breakthrough session:

### Academic Progress
- [ ] **Test Score Improvement:** 52% → 78%
- [ ] **Mom's Response:** Cried happy tears
- [ ] **Dad's Response:** "Good job" (rare for him)
- [ ] **Nai Nai's Response:** Made celebratory cookies

### New Revelations
- [ ] **Secret Writing:** Fantasy stories in notebook
- [ ] **Never shown anyone:** Until potentially Lily
- [ ] **Story Character:** Mage whose magic works differently
- [ ] **Self-Aware Metaphor:** Character represents Maya's learning style

### Art Club
- [ ] **Considering joining:** But scared of judgment
- [ ] **Imposter Syndrome:** "What if I'm not good anymore"

---

## Session 5 Facts to Verify
Deep connection and growth:

### Growth Actions
- [ ] **Joined Art Club:** Teacher called work "museum quality"
- [ ] **Asked to Mentor:** Other student wanted help with digital art
- [ ] **Sent Story to Lily:** Lily loved it, encouraged more writing

### Nai Nai Update
- [ ] **Made Mooncakes:** First time since stroke
- [ ] **Maya Helped:** Did the hard crimping parts
- [ ] **Passed Torch:** Nai Nai said traditions continue through Maya

### Future Plans
- [ ] **Art School Interest:** Ringling College of Art
- [ ] **Strategy for Dad:** Present career from business angle (game industry $)
- [ ] **Brother Connection:** Might bond over Minecraft redstone = math

---

## Biography Quality Checks

### Structure
- [ ] Biography has PSYCHOLOGICAL PROFILE section
- [ ] Biography has ACADEMIC JOURNEY section
- [ ] Biography is 300-500 words
- [ ] Biography uses prose, not bullet points

### Content Quality
- [ ] Captures Maya's creative/visual learning style
- [ ] Mentions family dynamics (David, Sarah, Ethan, Nai Nai)
- [ ] Notes emotional patterns (perfectionism, imposter syndrome)
- [ ] Tracks academic progress (52% → 78%)
- [ ] References key relationships (Lily, Biscuit, Nai Nai)
- [ ] Includes career interests (concept art, game design)

### Pattern Recognition
- [ ] Notes Maya's tendency to compare herself to others
- [ ] Captures the ACL injury → test anxiety parallel
- [ ] Shows growth arc over sessions
- [ ] Identifies breakthroughs (joining art club, sharing story)

---

## Memory Search Tests

Run these searches to verify memory extraction:

```javascript
// In browser console after sessions complete:
window.memoryDebug.searchMemories("Biscuit")     // Should find dog info
window.memoryDebug.searchMemories("Nai Nai")     // Should find grandmother info
window.memoryDebug.searchMemories("soccer")      // Should find ACL injury, midfielder
window.memoryDebug.searchMemories("52%")         // Should find failed test trauma
window.memoryDebug.searchMemories("art contest") // Should find museum achievement
window.memoryDebug.searchMemories("David")       // Should find dad info
window.memoryDebug.searchMemories("Lily")        // Should find best friend info
```

---

## Emotional Arc Verification

The sessions simulate this emotional progression:
1. **Session 1:** Anxious → Surprised (got problems right)
2. **Session 2:** Opening up → Briefly sad (Nai Nai's stroke)
3. **Session 3:** Stressed → Hopeful (word problem breakthrough)
4. **Session 4:** Excited (78%!) → Vulnerable (sharing secrets)
5. **Session 5:** Confident → Grateful (feels seen)

Check if the emotional arc tracking captured these shifts.

---

## Expected Living Biography Example

After all 5 sessions, the biography should read something like:

> Maya Chen is a 15-year-old sophomore at Lincoln High School in Portland, Oregon. She's a creative soul who moved from San Francisco at age 10, leaving behind her best friend Lily (with whom she still maintains contact via Discord). Maya dreams of becoming a concept artist for video games, using her digital art skills on Procreate to work toward that goal.
>
> She lives with her father David (a software engineer at Intel), her mother Sarah (a pediatric nurse at OHSU), her younger brother Ethan (11, Minecraft enthusiast), and her grandmother Nai Nai. Maya has a deep bond with Nai Nai, who recently recovered from a stroke; Maya has taken over some traditional cooking to keep her grandmother's recipes alive.
>
> Maya struggles with math, stemming from a traumatic 52% test score that triggered feelings of inadequacy compared to her logical engineer father. However, she's shown remarkable growth, improving to 78% by learning to visualize math through her artistic lens - connecting quadratics to game physics and systems of equations to quest storylines.
>
> She plays soccer (midfielder, practices Tuesdays and Thursdays) and shares her home with Biscuit, a 3-year-old corgi she adopted from a shelter at age 12. She recently joined art club and shared her secret fantasy writing with Lily for the first time.
>
> Key growth areas: overcoming imposter syndrome, building confidence to share creative work, learning to communicate with her dad in his "logical language" about her art career dreams.
