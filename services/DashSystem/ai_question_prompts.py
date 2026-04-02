"""
Curriculum-aligned prompt templates for AI question generation.

These produce Perseus-compatible questions targeted at specific Khan Academy
skills (units) and sub-skills (lessons), with difficulty and age calibration.
"""

from typing import Any, Dict, Optional


# ── Language subject detection ──────────────────────────────────────────
# When the subject itself is a language (e.g. "Spanish", "French"), questions
# must be written in the student's instruction language (app language) and
# TEACH the target language — never immerse by writing the whole question in it.
_LANGUAGE_SUBJECTS = {
    "spanish", "french", "german", "italian", "portuguese", "chinese",
    "mandarin", "cantonese", "japanese", "korean", "arabic", "hindi",
    "russian", "latin", "greek", "hebrew", "swahili", "tagalog",
    "vietnamese", "thai", "turkish", "polish", "dutch", "swedish",
    "norwegian", "danish", "finnish", "czech", "hungarian", "romanian",
    "bengali", "urdu", "persian", "farsi", "indonesian", "malay",
    "english", "sign language", "asl",
}


def _detect_language_subject(skill_name: str) -> Optional[str]:
    """Return the language name if the skill is a foreign-language subject, else None."""
    lower = skill_name.lower()
    for lang in _LANGUAGE_SUBJECTS:
        if lang in lower:
            return lang.title()
    return None


DIFFICULTY_DESCRIPTORS = {
    (0.0, 0.2): (
        "very easy — single-step recall or recognition. "
        "Example: 'What is 3 + 5?' or 'Which continent is France in?'"
    ),
    (0.2, 0.4): (
        "easy — 1-2 step straightforward application. "
        "Example: 'If you have 12 cookies and share equally among 4 friends, how many does each get?'"
    ),
    (0.4, 0.6): (
        "medium — 2-3 step reasoning, requires understanding. "
        "Example: 'A rectangle has perimeter 24 cm and width 5 cm. What is its area?'"
    ),
    (0.6, 0.8): (
        "challenging — multi-step reasoning or conceptual transfer. "
        "Example: 'Explain why multiplying by 0.5 is the same as dividing by 2.'"
    ),
    (0.8, 0.92): (
        "hard — multi-step reasoning, novel application, or tricky edge cases. "
        "Example: 'A train leaves at 2:45 PM at 60 mph. Another leaves at 3:15 PM at 80 mph. "
        "When does the second catch up?'"
    ),
    (0.92, 1.01): (
        "synthesis — combine concepts from MULTIPLE skills, transfer to novel real-world contexts, "
        "or solve problems requiring creative application across topics. "
        "The student must SYNTHESIZE knowledge (not just apply one procedure harder). "
        "Example: 'Design a budget for a school event: 40% food ($12/person for 25 people), "
        "30% decorations, 20% entertainment, 10% contingency. What is the total budget and "
        "what is the contingency amount?' "
        "This level tests whether the student can integrate skills fluently under new conditions."
    ),
}

FORMAT_INSTRUCTIONS = {
    "radio_single": (
        "Format: SINGLE-SELECT multiple choice (radio_single).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'radio 1' with type 'radio'.\n"
        "Set options.multipleSelect to false.\n"
        "Provide exactly 4 choices. Exactly ONE choice must have 'correct': true; the rest 'correct': false.\n"
        "Include plausible distractors that reflect common student mistakes.\n"
        "For EACH choice, include a 'misconception' field (string, 5-15 words) describing the common "
        "student error that choice targets. Set 'misconception': null for the correct choice."
    ),
    "radio_multi": (
        "Format: MULTI-SELECT multiple choice (radio_multi).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'radio 1' with type 'radio'.\n"
        "Set options.multipleSelect to true.\n"
        "Provide exactly 4 choices. Exactly TWO choices must have 'correct': true; the rest 'correct': false.\n"
        "The question text must make it clear that more than one answer may be correct.\n"
        "For EACH choice, include a 'misconception' field (string, 5-15 words) describing the common "
        "student error that choice targets. Set 'misconception': null for correct choices."
    ),
    "orderer": (
        "Format: ORDERING question (orderer).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'orderer 1' with type 'orderer'.\n"
        "Provide options.correctOptions as the items in the correct order.\n"
        "Provide options.options as the same items but shuffled into a DIFFERENT order.\n"
        "Set options.layout to 'horizontal'. Use 3-5 items."
    ),
    "numeric_input": (
        "Format: NUMERIC INPUT (numeric_input).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'numeric-input 1' with type 'numeric-input'.\n"
        "The widget options MUST include ALL of these fields:\n"
        '  "coefficient": false,\n'
        '  "static": false,\n'
        '  "labelText": "",\n'
        '  "size": "normal",\n'
        '  "answers": [{"status": "correct", "value": <number>, "maxError": 0.01, "simplify": "optional", "strict": false, "message": ""}]\n'
        "The question MUST require computing a specific numeric answer (not a concept question).\n"
        "The question content must reference the widget as [[☃ numeric-input 1]].\n"
        "Use this format for: arithmetic, measurement, unit conversion, counting, statistics."
    ),
    "dropdown": (
        "Format: DROPDOWN selection (dropdown).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'dropdown 1' with type 'dropdown'.\n"
        'Provide options.placeholder as "select one".\n'
        "Provide options.choices as 3-5 objects each with 'content' (string) and 'correct' (boolean).\n"
        "Exactly ONE choice must have 'correct': true.\n"
        "The question content must reference the widget as [[☃ dropdown 1]].\n"
        "Use this format for: vocabulary, classification, fill-in-the-blank, term identification.\n"
        "For EACH choice, include a 'misconception' field (string, 5-15 words) describing the common "
        "student error that choice targets. Set 'misconception': null for the correct choice."
    ),
    "expression": (
        "Format: EXPRESSION INPUT (expression).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'expression 1' with type 'expression'.\n"
        "The widget options must include:\n"
        "  - buttonsVisible: 'never'\n"
        "  - functions: ['f', 'g', 'h']\n"
        "  - times: false\n"
        "  - answerForms: an array with one object: "
        '{value: "<correct_latex>", form: true, simplify: false, considered: "correct"}\n'
        "The question MUST require the student to TYPE a mathematical expression as the answer.\n"
        "The correct answer 'value' must be valid LaTeX (e.g., '3x+5', '\\\\frac{1}{2}', 'x^2-4').\n"
        "The question content must reference the widget as [[☃ expression 1]].\n"
        "Use this format for: simplify expressions, solve equations, write formulas, factor polynomials."
    ),
    "matcher": (
        "Format: MATCHING (matcher).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'matcher 1' with type 'matcher'.\n"
        "The widget options must include:\n"
        "  - labels: ['Column A', 'Column B'] (or appropriate column headers)\n"
        "  - left: array of 4 strings (items to match FROM)\n"
        "  - right: array of 4 strings (correct matches, IN MATCHING ORDER to left)\n"
        "  - orderMatters: true\n"
        "  - padding: true\n"
        "The right array must be in the correct matching order (right[0] matches left[0], etc).\n"
        "The question content must reference the widget as [[☃ matcher 1]].\n"
        "Use this format for: vocabulary definitions, cause-effect, term-description, event-date matching."
    ),
    "sorter": (
        "Format: SORTER (sorter).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'sorter 1' with type 'sorter'.\n"
        "The widget options must include:\n"
        "  - correct: array of strings in the CORRECT order\n"
        "  - layout: 'horizontal' or 'vertical'\n"
        "  - padding: true\n"
        "Provide 4-6 items. The correct array defines the right order.\n"
        "The question content must reference the widget as [[☃ sorter 1]].\n"
        "Use this format for: chronological ordering, ranking by size/importance, process steps, sequencing events."
    ),
    "definition": (
        "Format: DEFINITION with follow-up question.\n"
        "The question must use TWO widgets in the 'widgets' object:\n"
        "  1. A 'definition 1' widget (type 'definition') with these REQUIRED options:\n"
        "     - definition: string (the term's full definition text)\n"
        "     - togglePrompt: string (the term to highlight/define)\n"
        "     - static: false\n"
        "  2. A 'radio 1' widget (type 'radio') for the follow-up question about the term\n"
        "     with 4 choices, exactly 1 correct, multipleSelect: false\n"
        "IMPORTANT: The 'widgets' object MUST contain BOTH widgets. Example:\n"
        '  "widgets": {\n'
        '    "definition 1": {"type":"definition","graded":false,"options":{"definition":"...","togglePrompt":"...","static":false}},\n'
        '    "radio 1": {"type":"radio","graded":true,"options":{"choices":[...], "multipleSelect":false}}\n'
        "  }\n"
        "The question content MUST include BOTH placeholders with text between them:\n"
        '  "content": "Read about [[☃ definition 1]]. Based on the definition, answer: [[☃ radio 1]]"\n'
        "Use this format for: vocabulary, reading comprehension, term identification, concept definitions."
    ),
    "categorizer": (
        "Format: CATEGORIZER (classify items into categories).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'categorizer 1' with type 'categorizer'.\n"
        "The widget options must include:\n"
        "  - items: array of 3-6 strings (the items to classify)\n"
        "  - categories: array of 2-4 strings (the category labels)\n"
        "  - values: array of integers (same length as items) — each is the 0-based index into categories "
        "for that item's correct category\n"
        "  - randomizeItems: false\n"
        "  - static: false\n"
        "Each item must clearly belong to exactly one category.\n"
        "The question content must reference the widget as [[☃ categorizer 1]].\n"
        "Use this format for: classification, sorting into groups, identifying types, properties of objects."
    ),
    "number_line": (
        "Format: NUMBER LINE (place a point on a number line).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'number-line 1' with type 'number-line'.\n"
        "The widget options must include:\n"
        "  - range: [min, max] — the visible number line range (integers)\n"
        "  - correctX: the correct numeric answer (a number within the range)\n"
        "  - correctRel: 'eq' (exact match)\n"
        "  - tickStep: integer step between tick marks\n"
        "  - snapDivisions: 2 (allows half-step snapping)\n"
        "  - labelStyle: 'decimal'\n"
        "  - labelTicks: true\n"
        "  - isInequality: false\n"
        "  - numDivisions: null\n"
        "  - divisionRange: [1, 10]\n"
        "  - initialX: null\n"
        "  - static: false\n"
        "  - isTickCtrl: false\n"
        "Choose range so correctX is not at the boundary. Keep numbers age-appropriate.\n"
        "The question content must reference the widget as [[☃ number-line 1]].\n"
        "Use this format for: plotting values, comparing numbers, fractions on a line, negative numbers, "
        "decimals, absolute value."
    ),
    "table": (
        "Format: TABLE (fill in cells in a table).\n"
        "The 'question.widgets' must contain exactly one widget keyed 'table 1' with type 'table'.\n"
        "The widget options must include:\n"
        "  - headers: array of column header strings (2-4 columns)\n"
        "  - rows: integer (2-5 rows to fill in)\n"
        "  - columns: integer (must match headers length)\n"
        "  - answers: 2D array of strings [row][col] with the correct cell values\n"
        "All answer values must be strings (convert numbers to strings: '42' not 42).\n"
        "The question content must reference the widget as [[☃ table 1]].\n"
        "Use this format for: completing data tables, function tables (input→output), "
        "conversion tables, pattern recognition with numbers."
    ),
}

# Map format names to their widget placeholder strings
_WIDGET_PLACEHOLDERS = {
    "radio_single": "[[☃ radio 1]]",
    "radio_multi": "[[☃ radio 1]]",
    "orderer": "[[☃ orderer 1]]",
    "numeric_input": "[[☃ numeric-input 1]]",
    "dropdown": "[[☃ dropdown 1]]",
    "expression": "[[☃ expression 1]]",
    "matcher": "[[☃ matcher 1]]",
    "sorter": "[[☃ sorter 1]]",
    "definition": "[[☃ definition 1]] [[☃ radio 1]]",
    "categorizer": "[[☃ categorizer 1]]",
    "number_line": "[[☃ number-line 1]]",
    "table": "[[☃ table 1]]",
}


def _difficulty_label(difficulty: float, age: int = 10) -> str:
    for (lo, hi), label in DIFFICULTY_DESCRIPTORS.items():
        if lo <= difficulty < hi:
            # For young students, override examples to be age-appropriate
            if age <= 7:
                young_examples = {
                    (0.0, 0.2): "very easy — single-step recognition. Example: 'Which animal says moo?' or 'How many apples are in this group: 🍎🍎🍎?'",
                    (0.2, 0.4): "easy — simple 1-step task. Example: 'You have 4 crayons and get 2 more. How many now?' or 'Which shape has 3 sides?'",
                    (0.4, 0.6): "medium for this age — 2-step task with small numbers. Example: 'Sam has 8 stickers. She gives 3 to a friend. How many does she have left?'",
                }
                for (ylo, yhi), ylabel in young_examples.items():
                    if ylo <= difficulty < yhi:
                        return ylabel
            elif age <= 9:
                young_examples = {
                    (0.0, 0.2): "very easy — recall. Example: 'What is 6 + 7?' or 'Which animal is a mammal: fish, dog, or butterfly?'",
                    (0.2, 0.4): "easy — 1-2 step. Example: 'A bag has 15 marbles. 6 are red. How many are not red?'",
                    (0.4, 0.6): "medium — multi-step with whole numbers. Example: 'A recipe uses 2 cups of flour for 8 cookies. How much for 24 cookies?'",
                }
                for (ylo, yhi), ylabel in young_examples.items():
                    if ylo <= difficulty < yhi:
                        return ylabel
            return label
    return list(DIFFICULTY_DESCRIPTORS.values())[-1]


def _age_guidance(age: int) -> str:
    if age <= 7:
        return (
            "STRICT AGE RULES for age {age} (K-2nd grade):\n"
            "- Use ONLY 1-2 syllable words (cat, big, run — NOT hypothesis, equation)\n"
            "- Max sentence length: 8 words\n"
            "- Use concrete, relatable scenarios a {age}-year-old encounters\n"
            "- Numbers must be 20 or less for most problems, 100 or less for counting only\n"
            "- NO fractions, decimals, negative numbers, or variables\n"
            "- NO abstract concepts (probability, ratios, inference)\n"
            "- Question text must be 30 words or fewer total\n"
            "- CRITICAL: Every subject can be taught at this age. A 5-year-old can learn:\n"
            "  - Programming: giving step-by-step instructions, sequencing, what a computer does\n"
            "  - Philosophy: fairness, feelings, 'how do you know?', right vs wrong\n"
            "  - Economics: needs vs wants, sharing, trading\n"
            "  - Science: senses, animals, weather, plants\n"
            "  - History: family, community helpers, then vs now\n"
            "  - Art: colors, shapes, what tools artists use\n"
            "  - Music: loud vs quiet, fast vs slow, high vs low sounds\n"
            "  - Languages: greetings, colors, animals, family words — questions IN the app language, teaching target language words\n"
            "  NEVER fall back to arithmetic. Teach the ACTUAL subject using age-appropriate concepts."
        ).format(age=age)
    if age <= 9:
        return (
            "STRICT AGE RULES for age {age} (3rd-4th grade):\n"
            "- Use simple, familiar vocabulary (avoid: 'determine', 'evaluate', 'significant')\n"
            "- Max sentence length: 12 words\n"
            "- Contexts: school, sports, pets, cooking, games\n"
            "- Numbers can go up to 1,000; simple fractions OK (1/2, 1/4)\n"
            "- NO algebra, no variables, no scientific notation\n"
            "- Question text must be 50 words or fewer total\n"
            "- CRITICAL: Teach the ACTUAL subject at this age level. Do NOT default to math.\n"
            "  Every subject has age-appropriate concepts a {age}-year-old can grasp."
        ).format(age=age)
    if age <= 13:
        return (
            "AGE GUIDANCE for age {age} (5th-8th grade):\n"
            "- Clear, direct language; avoid unnecessarily complex vocabulary\n"
            "- Contexts: sports stats, cooking ratios, money, geography, science\n"
            "- Fractions, decimals, basic algebra, percentages OK\n"
            "- Can use multi-step word problems\n"
            "- Question text should be 80 words or fewer"
        ).format(age=age)
    return (
        "AGE GUIDANCE for age {age} (high school):\n"
        "- Mature, clear language; technical terms OK when topic-appropriate\n"
        "- Real-world contexts: finance, engineering, science, data analysis\n"
        "- Advanced math, algebra, geometry, statistics all OK\n"
        "- Can include multi-paragraph scenarios if needed"
    ).format(age=age)


def build_image_prompt(skill_name: str, lesson_name: str, age: int, question_text: str) -> str:
    """Build a prompt for Gemini image generation tied to a specific question."""
    age_style = "very simple cartoon-style" if age <= 9 else "clean diagram-style"
    return (
        f"Create a {age_style} educational illustration for this question:\n"
        f"Topic: {skill_name} — {lesson_name}\n"
        f"Question: {question_text}\n\n"
        "Requirements:\n"
        "- Clean white or light background\n"
        "- No text, watermarks, logos, or branding anywhere in the image\n"
        "- No software icons, tool palettes, or UI elements\n"
        "- Simple, clear shapes and labels only\n"
        "- Khan Academy illustration style\n"
        "- Suitable for educational use\n"
        "- Pure illustration — absolutely no watermarks, signatures, or overlaid text\n"
        "- If math: show geometric shapes, number lines, or graphs as appropriate\n"
        "- If science: show diagrams, organisms, or experimental setups\n"
        "- If history/social studies: show maps, timelines, or simple scenes"
    )


def build_skill_question_prompt(
    skill_name: str,
    lesson_name: str,
    difficulty: float,
    age: int,
    fmt: str,
    memory: Dict[str, Any],
    khan_example: str = "",
    subject: str = "",
) -> str:
    """
    Build a Gemini prompt that generates a Perseus JSON question aligned to a
    specific Khan Academy skill (unit) and optionally a lesson (sub-skill).

    The prompt is curriculum-aware: it uses the exact skill and lesson names
    so Gemini generates questions on the correct topic at the correct level.
    """
    difficulty_label = _difficulty_label(difficulty, age)
    age_guidance = _age_guidance(age)
    format_instruction = FORMAT_INSTRUCTIONS.get(fmt, FORMAT_INSTRUCTIONS["radio_single"])
    widget_placeholder = _WIDGET_PLACEHOLDERS.get(fmt, "[[☃ radio 1]]")

    # Detect if this is a language-learning subject
    language_target = _detect_language_subject(skill_name)

    # The app's interface language — questions & hints are written in this language.
    # Currently English; parameterise when multi-language UI is added.
    instruction_lang = "English"

    memory_snippet = ""
    if memory:
        interests = memory.get("interests", [])
        if interests:
            memory_snippet = (
                f"The student's interests include: {', '.join(interests[:3])}. "
                "Try to use these as context in the question when it fits naturally."
            )

    subject_line = f"SUBJECT: {subject}\n" if subject else ""

    prompt = (
        "You are an expert educational content author who writes questions for Khan Academy. "
        "Your questions are pedagogically sound, precisely targeted to the stated skill, "
        "and indistinguishable from professionally authored Khan Academy exercises.\n"
        "Generate exactly ONE question as strict JSON with these top-level keys: "
        "question, answerArea, hints.\n"
        "Do NOT include any text outside the JSON object. No markdown fences.\n\n"

        f"{subject_line}"
        f"SKILL (Unit): {skill_name}\n"
        f"SUB-SKILL (Lesson): {lesson_name}\n"
        f"Difficulty: {difficulty:.2f} — {difficulty_label}\n"
        "Your question's cognitive demand MUST match this difficulty level. "
        "Do NOT make it easier or harder than specified.\n"
        f"Student age: {age}\n\n"

        "IMPORTANT: The question MUST be specifically about the SUBJECT and SKILL stated above. "
        "Do NOT generate questions about unrelated topics.\n\n"

        f"{age_guidance}\n\n"
    )

    # ── Language-subject teaching rules ──────────────────────────────
    if language_target:
        prompt += (
            f"LANGUAGE TEACHING RULES (this is a {language_target} language course):\n"
            f"- ALL question text, answer choices, and hints MUST be written in {instruction_lang}.\n"
            f"- You are teaching {language_target} TO a student whose app language is {instruction_lang}.\n"
            f"- Include {language_target} words or short phrases as the CONTENT being tested, "
            f"but frame every instruction, choice label, and hint in {instruction_lang}.\n"
            f"- Good examples:\n"
            f'  - "What does \'hola\' mean in {instruction_lang}?" ✓\n'
            f'  - "Which {language_target} word means \'hello\'?" ✓\n'
            f'  - "Choose the correct {language_target} translation for \'thank you\'." ✓\n'
            f"- BAD examples (NEVER do this):\n"
            f'  - "¿Cuál es la capital de España?" ✗ — entire question in {language_target}\n'
            f'  - "Choisissez la bonne réponse" ✗ — instructions in {language_target}\n'
            f"- For vocabulary: test translation, meaning, or usage of {language_target} words/phrases\n"
            f"- For grammar: explain {language_target} grammar rules in {instruction_lang}, "
            f"then test the student's ability to apply them\n"
            f"- NEVER write the entire question or hints in {language_target}.\n"
            f"- NEVER assume the student already speaks {language_target}.\n\n"
        )

    prompt += f"{format_instruction}\n\n"

    # Few-shot Khan example if available
    if khan_example:
        prompt += (
            "REFERENCE EXAMPLE (for format and style — do NOT copy content):\n"
            f"{khan_example}\n\n"
            "Generate a NEW question on the stated skill. Match the structural quality "
            "and format of the example above, but create completely original content.\n\n"
        )

    prompt += (
        "REQUIRED JSON STRUCTURE:\n"
        "{\n"
        '  "question": {\n'
        f'    "content": "<question text> {widget_placeholder}",\n'
        '    "images": {},\n'
        '    "widgets": { <widget(s) as described above — definition format needs TWO widgets> }\n'
        "  },\n"
        '  "answerArea": { "calculator": false },\n'
        '  "hints": [\n'
        '    { "content": "<Hint 1: gentle conceptual nudge — ask a guiding question>" },\n'
        '    { "content": "<Hint 2: explain the key concept or method needed>" },\n'
        '    { "content": "<Hint 3: walk through most of the solution, stopping just before the answer>" }\n'
        "  ]\n"
        "}\n\n"

        "RULES:\n"
        "- The question MUST test CONTENT KNOWLEDGE of the stated skill and sub-skill.\n"
        "- NEVER substitute a different subject. If the skill is 'Python', ask about Python concepts "
        "(sequences, instructions, loops, variables) — NOT arithmetic word problems. "
        "If the skill is 'Philosophy', ask about ideas, fairness, reasoning — NOT counting. "
        "Every subject can be taught at every age. Find the right concept, not a different subject.\n"
        "- NEVER generate open-ended, essay, or free-text questions. Every question MUST use "
        "the specified widget format with a clear correct answer.\n"
        "- CRITICAL: DO NOT list wrong answers in the question stem. NEVER write questions like "
        "'Is it A, B, or C?' where A and B are wrong and C is the dropdown answer. The question stem "
        "must not eliminate choices or give away the answer. Examples of BAD stems:\n"
        "  * 'Is it a variable, a sequence, or a ___?' (eliminates variable/sequence)\n"
        "  * 'It's not X or Y, so it must be ___?' (gives away answer)\n"
        "  * 'What is [Subject]?' where the answer is '[Subject]' (too trivial)\n"
        "- Ask SUBSTANTIVE questions that test actual knowledge, not just definitions of the subject name.\n"
        "  * GOOD: 'In Python, what command makes code repeat 5 times?'\n"
        "  * BAD: 'What is the study of economics?' (answer: 'economics')\n"
        "- NEVER put term definitions inline in the question text using parentheses, e.g. NEVER write "
        "'A treaty (a formal agreement between countries) was signed...' — "
        "this clutters the question and gives away context. If a key term needs defining, put it "
        "in a separate 'KEY TERM' line at the start: 'KEY TERM: Treaty — a formal agreement between countries.\n\n"
        "Which treaty ended World War I?' — or simply trust the student knows the term.\n"
        "- The question content MUST include the widget placeholder (e.g., [[☃ radio 1]]). "
        "Without the placeholder, the widget won't render.\n"
        "- NEVER ask meta-questions about 'learning strategies' or 'study habits'.\n"
        "- NEVER use phrases like 'which is the best approach to learn X'.\n"
        "- Numbers, expressions, and content must be grade-appropriate.\n"
        "- Include exactly 3 hints with PROGRESSIVE scaffolding:\n"
        "  - Hint 1: A guiding question that points toward the right approach "
        "(e.g., 'What operation do you need?')\n"
        "  - Hint 2: Teach the specific concept or formula needed "
        "(e.g., 'Area of a rectangle = length x width')\n"
        "  - Hint 3: Walk through the solution steps, stopping just before revealing the final answer\n"
        "- Each hint must be substantive (10+ words). "
        "Never use vague hints like 'Think about it' or 'Try again.'\n"
        "- Use LaTeX ($...$) for math expressions when appropriate.\n"
        "- Each choice 'content' must be a string (not a number).\n"
        "- Distractor choices must be plausible wrong answers reflecting real student misconceptions.\n"
    )
    # Add age-appropriate distractor enforcement
    if age <= 7:
        prompt += (
            "- CRITICAL DISTRACTOR RULE for age 5-7: Wrong answer choices must use ONLY words a kindergartener knows. "
            "Choices must be concrete objects, simple numbers (1-20), or single familiar words. "
            "NEVER use: fractions, percentages, algebra terms, scientific vocabulary, or multi-word technical phrases. "
            "Example of GOOD wrong answers for a shapes question: 'circle', 'square', 'triangle'. "
            "Example of BAD wrong answers: 'obtuse angle', 'perpendicular lines', 'hypotenuse'.\n"
        )
    elif age <= 9:
        prompt += (
            "- DISTRACTOR RULE for age 8-9: Wrong answer choices must use vocabulary a 3rd-4th grader knows. "
            "No algebra, no variables, no scientific notation, no multi-syllable technical terms. "
            "Distractors should be plausible mistakes with familiar numbers and everyday words.\n"
        )
    elif age <= 11:
        prompt += (
            "- DISTRACTOR RULE for age 10-11: Distractors should reflect computation errors or concept confusion "
            "a 5th-6th grader would make. Avoid high-school-level vocabulary in answer choices.\n"
        )
    prompt += (
        "- For math: all numbers in answer choices must be reachable via computation, not random.\n"
        "- For language subjects (Spanish, French, etc.): ALWAYS write questions, choices, "
        "and hints in the app's instruction language. Only include target-language words/phrases "
        "as the content being tested — never write the entire question in the target language.\n"
        "- For phonics/listening questions: ALWAYS put the target word in single quotes "
        "(e.g., \"Listen carefully to the word 'sun'.\" or \"What sound does the word 'cat' start with?\"). "
        "The system will auto-play audio using text-to-speech. "
        "NEVER reference pictures, images, or visual media in questions "
        "(e.g., 'Look at the picture', 'In the image below') — "
        "images are only added separately by the system, not by you. "
        "Write questions that are fully self-contained with text only.\n"
        f"- CRITICAL: The question 'content' field must contain the question text "
        f"and the widget placeholder {widget_placeholder}. "
        "Do NOT write the word 'widget' as literal text. Do NOT add any text after "
        "the placeholder. The placeholder is rendered by the system — "
        "never explain or reference it in the question text.\n"
    )

    if memory_snippet:
        prompt += f"\nPERSONALIZATION:\n{memory_snippet}\n"

    return prompt


def build_responsive_hint_prompt(
    skill_name: str,
    question_text: str,
    selected_answer: str,
    correct_answer: str,
    age: int = 10,
    misconception: str = "",
) -> str:
    """
    Build a Gemini prompt that generates a targeted Socratic hint based on
    the student's specific wrong answer.
    """
    age_note = (
        "Use very simple words (1-2 syllable). Short sentences."
        if age <= 7
        else "Use clear, age-appropriate language."
        if age <= 13
        else "You may use standard academic vocabulary."
    )

    return (
        "You are a patient tutor helping a student who just answered a question incorrectly.\n\n"
        f"Skill being tested: {skill_name}\n"
        f"Question: {question_text}\n"
        f"Student's answer: {selected_answer}\n"
        f"Correct answer: {correct_answer}\n\n"
        "Generate a BRIEF Socratic hint (2-3 sentences max) that:\n"
        "1. Acknowledges what the student might have been thinking (without saying 'wrong').\n"
        "2. Points out the specific error or gap in reasoning.\n"
        "3. Asks ONE guiding question that leads toward the correct approach.\n\n"
        "RULES:\n"
        "- Do NOT reveal the correct answer.\n"
        "- Do NOT say 'incorrect' or 'wrong'. Use phrases like 'almost' or 'not quite'.\n"
        "- Be encouraging but concise. No filler phrases.\n"
        "- Use LaTeX ($...$) for any math expressions.\n"
        f"- Student is {age} years old. {age_note}\n"
        + (f"- Known misconception: \"{misconception}\". Address this specific error pattern.\n"
           if misconception else "")
        + "\nReturn ONLY the hint text. No JSON, no labels, no extra formatting."
    )
