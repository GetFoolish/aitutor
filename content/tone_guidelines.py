#!/usr/bin/env python3
"""
Tone Guidelines for Question Generation

Provides friendly, encouraging, child-appropriate tone templates
for LLM-based question generation.

STYLE: innocent drinks - chatty, humble, a bit cheeky.
Like a nice friend who happens to know maths.
"""

# Banned phrases - NEVER use these
# CRITICAL: This list is shown to the LLM in get_tone_prompt().
# Include ALL patterns that validate_tone() rejects so the LLM knows to avoid them upfront.
BANNED_PHRASES = [
    # Formulaic openers with "right"
    "right then",
    "right,",
    "right, so",
    "right so",
    "right, let's",
    "right let's",
    # Formulaic openers with "okay"
    "okay,",
    "okay, so",
    "okay so",
    "okay, let's",
    "okay let's",
    "okay, check",
    "okay check",
    "okay, here's",
    "okay here's",
    "okay here's the thing",
    "okay this is a fun one",
    "okay, try this one",
    "okay this one",
    "okay this one's",
    "okay this one is kinda",
    # Formulaic openers with "alright"
    "alright,",
    "alright, so",
    "alright so",
    "alright, let's",
    "alright let's",
    "alright, here's",
    "alright here's",
    "alright here's the thing",
    # "let's" patterns
    "let's dive in",
    "let's get started",
    "let's see if",
    "let's see if you can",
    "let's try",
    # Other formulaic patterns
    "can you figure out",
    "here's a head-scratcher",
    "here's a fun one",
    "ready? here we go",
    # Banned praise (too hype-y)
    "Great job!",
    "Excellent!",
    "Amazing!",
]


def validate_tone(content: str) -> list[str]:
    """Validate tone for the Innocent-Drinks-style content.

    Returns:
        A list of human-readable violations. Empty list means "looks ok".

    This is intentionally heuristic. The goal is to catch common failures that
    show up in production (e.g., "right, so ...", "okay this one's ...").
    """

    if not content or not isinstance(content, str):
        return ["empty content"]

    text = content.strip()
    lowered = text.lower()

    violations: list[str] = []

    # Exact/substring banned phrases (case-insensitive)
    for phrase in BANNED_PHRASES:
        if phrase.lower() in lowered:
            violations.append(f"banned phrase: {phrase}")

    # Additional common variants that slip past exact matching
    import re

    patterns: list[tuple[str, str]] = [
        # Formulaic openers that sound too scripted
        (r"\bright\s*,\s*so\b", "banned opener variant: 'right, so'"),
        (r"\bokay\s*,\s*so\b", "formulaic opener: 'okay, so'"),
        (r"\bokay\s+so\b", "formulaic opener: 'okay so'"),
        (r"\bokay\s*,\s*check\b", "formulaic opener: 'okay, check'"),
        (r"\bokay\s+check\b", "formulaic opener: 'okay check'"),
        (r"\balright\s*,\s*so\b", "formulaic opener: 'alright, so'"),
        (r"\balright\s+so\b", "formulaic opener: 'alright so'"),
        (r"\bokay\s+this\s+one\b", "banned opener variant: 'okay this one'"),
        (r"\bokay\s+this\s+one'?s\b", "banned opener variant: 'okay this one's'"),
        (r"\bokay\s+this\s+one\s+is\s+kinda\b", "banned opener variant: 'okay this one is kinda'"),
        (r"\bokay\s*,\s*here'?s\b", "too-close-to-banned opener: 'okay, here's'"),
        (r"\balright\s*,\s*here'?s\b", "too-close-to-banned opener: 'alright, here's'"),
        # Variations with "here's the thing"
        (r"\bokay\s*,?\s*here'?s\s+the\s+thing\b", "formulaic opener: 'okay here's the thing'"),
        (r"\balright\s*,?\s*here'?s\s+the\s+thing\b", "formulaic opener: 'alright here's the thing'"),
        # "okay, let's..." variants (CRITICAL: catches "okay, let's dive in")
        (r"\bokay\s*,?\s*let'?s\b", "formulaic opener: 'okay, let's'"),
        (r"\balright\s*,?\s*let'?s\b", "formulaic opener: 'alright, let's'"),
        (r"\bright\s*,?\s*let'?s\b", "formulaic opener: 'right, let's'"),
        # "let's dive in" and variants
        (r"\blet'?s\s+dive\s+in\b", "banned phrase: 'let's dive in'"),
        (r"\blet'?s\s+get\s+started\b", "formulaic opener: 'let's get started'"),
        (r"\blet'?s\s+see\s+if\b", "banned phrase: 'let's see if'"),
        (r"\blet'?s\s+try\b", "formulaic opener: 'let's try'"),
        # Banned praise
        (r"\bgreat\s+job\b", "banned praise: 'great job'"),
        (r"\bamazing\b!", "banned praise: 'amazing!'"),
        (r"\bexcellent\b!", "banned praise: 'excellent!'"),
        # Other scripted patterns
        (r"\bhere'?s\s+a\s+head[\s-]?scratcher\b", "formulaic: 'here's a head-scratcher'"),
        (r"\bhere'?s\s+a\s+fun\s+one\b", "formulaic: 'here's a fun one'"),
        (r"\bready\s*\?\s*here\s+we\s+go\b", "formulaic: 'ready? here we go'"),
    ]

    for pat, msg in patterns:
        if re.search(pat, lowered):
            violations.append(msg)

    return sorted(set(violations))

# Tone examples by grade level
TONE_GUIDELINES = {
    "K-2": {
        "description": "innocent drinks style - chatty, humble, a bit cheeky, like your nice friend",
        "characteristics": [
            "lowercase where possible, casual punctuation",
            "short sentences. like this. easy peasy.",
            "slightly self-aware and playful",
            "no corporate speak, no trying too hard",
            "gentle humour, never mean",
            "talk like a real person, not a textbook",
        ],
        "example_rewrites": [
            {
                "before": "Count the objects. How many are there?",
                "after": "so there are some apples here. have a count. how many did you get?"
            },
            {
                "before": "What is 3 + 2?",
                "after": "you've got 3 apples. someone nice gives you 2 more. how many now? (we believe in you)"
            },
            {
                "before": "Select the correct answer.",
                "after": "pick the one you reckon is right. no pressure."
            },
            {
                "before": "Calculate the sum of 5 and 7.",
                "after": "5 plus 7. go on, you know this one."
            },
            {
                "before": "Identify the shape.",
                "after": "what shape is this then? take your time, it's not going anywhere."
            },
            {
                "before": "How many stars are in the picture?",
                "after": "ooh, stars! have a count. how many can you see?"
            }
        ],
        "opening_phrases": [
            "here's a little question for you.",
            "here we go.",
            "have a go at this.",
            "try this.",
            "so here's the thing.",
            "quick one.",
            "ooh, this is good.",
            "",  # sometimes just dive straight in
        ],
        "encouragement": [
            "(no rush, we'll wait)",
            "(you've got this)",
            "(take your time)",
            "(it's fine to guess)",
            "(we believe in you)",
        ]
    },
    
    "3-5": {
        "description": "innocent style - still chatty, a bit more substance, gentle wit",
        "characteristics": [
            "conversational, like explaining to a friend",
            "real scenarios but keep it simple",
            "a tiny bit cheeky, never patronising",
            "admit when things are tricky",
        ],
        "example_rewrites": [
            {
                "before": "Calculate the area of the rectangle.",
                "after": "you've got a rectangle. it's 5 wide and 8 tall. how much space is that altogether? (multiply them, you'll be fine)"
            },
            {
                "before": "Solve for x: 2x + 4 = 10",
                "after": "there's a mystery number here. double it, add 4, and you get 10. what's the number? bit of a puzzle, this one."
            },
            {
                "before": "What fraction is shaded?",
                "after": "some of this shape is coloured in. what fraction is that? (count the bits)"
            }
        ],
        "opening_phrases": [
            "so here's the thing.",
            "have a think about this.",
            "here's one for you.",
            "try this.",
            "here we go.",
            "",
        ],
        "encouragement": [
            "(you've got this)",
            "(take your time)",
            "(bit of a puzzle, this one)",
        ]
    },
    
    "6-8": {
        "description": "innocent style - more grown up, still friendly, no nonsense",
        "characteristics": [
            "straight talking but warm",
            "acknowledge it can be hard",
            "no fake enthusiasm",
            "treat them like smart people",
        ],
        "example_rewrites": [
            {
                "before": "Find the slope of the line passing through (2,3) and (5,9).",
                "after": "you've got two points: (2,3) and (5,9). what's the slope between them? (rise over run, remember)"
            },
            {
                "before": "Simplify the expression 3x + 2x - 5.",
                "after": "simplify this: 3x + 2x - 5. combine the like terms and you're done."
            }
        ],
        "opening_phrases": [
            "here's one.",
            "try this.",
            "have a go.",
            "",
        ],
        "encouragement": [
            "(remember the basics)",
            "(you know this)",
        ]
    },
    
    "9-12": {
        "description": "innocent style - mature, honest, slightly dry wit",
        "characteristics": [
            "respect their intelligence",
            "keep it real",
            "okay to be a bit dry/witty",
            "no dumbing down",
        ],
        "example_rewrites": [
            {
                "before": "Find the derivative of f(x) = x³ + 2x² - 5x + 1.",
                "after": "differentiate: x³ + 2x² - 5x + 1. power rule, term by term."
            }
        ],
        "opening_phrases": [
            "",
            "try this.",
        ],
        "encouragement": []
    }
}


def get_tone_prompt(grade_level: str = "K-2") -> str:
    """Get tone guidelines as a prompt for LLM."""
    
    guidelines = TONE_GUIDELINES.get(grade_level, TONE_GUIDELINES["K-2"])
    
    prompt = f"""
TONE GUIDELINES FOR {grade_level} STUDENTS (innocent drinks style):

{guidelines['description']}

WRITING STYLE:
{chr(10).join(f'• {c}' for c in guidelines['characteristics'])}

EXAMPLE REWRITES (make questions sound like this):
"""
    
    for ex in guidelines.get('example_rewrites', []):
        prompt += f"""
❌ Instead of: "{ex['before']}"
✅ Write like: "{ex['after']}"
"""
    
    # Only show opening phrases that aren't empty
    opening_phrases = [p for p in guidelines.get('opening_phrases', []) if p][:4]
    if opening_phrases:
        prompt += f"""

GOOD OPENING PHRASES (vary these, don't repeat!):
{chr(10).join(f'• "{p}"' for p in opening_phrases)}
• or just dive straight into the scenario with no opener"""

    encouragement = [e for e in guidelines.get('encouragement', []) if e][:3]
    if encouragement:
        prompt += f"""

ENCOURAGEMENT TO ADD (sprinkle these in):
{chr(10).join(f'• "{e}"' for e in encouragement)}"""

    # Add banned phrases (show ALL of them - grouped for clarity)
    prompt += f"""

🚫 BANNED PHRASES (the server validates and REJECTS these - never use any of them):

BANNED OPENERS (these will fail validation immediately):
• "right," / "right, so" / "right so" / "right, let's" / "right then"
• "okay," / "okay, so" / "okay so" / "okay, let's" / "okay let's"
• "okay, here's" / "okay here's the thing" / "okay, check" / "okay check"
• "okay this one" / "okay this one's" / "okay this is a fun one" / "okay, try this one"
• "alright," / "alright, so" / "alright so" / "alright, let's" / "alright let's"
• "alright, here's" / "alright here's the thing"

BANNED "LET'S" PATTERNS:
• "let's dive in" / "let's get started" / "let's see if" / "let's try"

BANNED FORMULAIC PATTERNS:
• "can you figure out" / "here's a head-scratcher" / "here's a fun one" / "ready? here we go"

BANNED PRAISE (too hype-y):
• "Great job!" / "Excellent!" / "Amazing!"

✅ SAFE OPENERS (use these instead, or skip the opener entirely):
• "so" (just "so", not "okay, so" or "alright, so")
• "here we go."
• "have a go at this."
• "try this."
• "quick one."
• "ooh, this is good."
• or just dive straight into the scenario with NO opener at all

CRITICAL: vary your openings! if you've used "here's the thing" before, use something different.
sometimes just start with the scenario directly, no opener at all.

remember: write like innocent drinks - chatty, humble, a bit cheeky. like a nice friend who happens to know the subject. no corporate speak. no fake enthusiasm. just... nice.
"""
    
    return prompt


def rewrite_question_prompt(question: str, grade_level: str = "K-2") -> str:
    """Generate a prompt to rewrite a question in friendlier tone."""
    
    tone = get_tone_prompt(grade_level)
    
    return f"""
{tone}

---
ORIGINAL QUESTION (too formal):
{question}

TASK: Rewrite this question to be more friendly, engaging, and encouraging for {grade_level} students.
Keep the same math/learning objective, but make it feel warm and fun.

REWRITTEN QUESTION:
"""


# CLI
if __name__ == "__main__":
    import sys
    
    grade = sys.argv[1] if len(sys.argv) > 1 else "K-2"
    print(get_tone_prompt(grade))
