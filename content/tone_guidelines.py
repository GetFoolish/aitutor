#!/usr/bin/env python3
"""
Tone Guidelines for Question Generation

Provides friendly, encouraging, child-appropriate tone templates
for LLM-based question generation.
"""

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
                "after": "right then. you've got 3 apples. someone nice gives you 2 more. how many now? (we believe in you)"
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
            }
        ],
        "opening_phrases": [
            "here's a little question for you.",
            "right, let's see.",
            "okay, try this one.",
            "here we go.",
            "have a go at this.",
        ],
        "encouragement": [
            "(no rush, we'll wait)",
            "(you've got this)",
            "(take your time)",
            "(it's fine to guess)",
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
            }
        ],
        "opening_phrases": [
            "alright, here's the thing.",
            "let's figure this out.",
            "okay this one's interesting.",
            "have a think about this.",
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
            }
        ]
    },
    
    "9-12": {
        "description": "innocent style - mature, honest, slightly dry wit",
        "characteristics": [
            "respect their intelligence",
            "keep it real",
            "okay to be a bit dry/witty",
            "no dumbing down",
        ]
    }
}


def get_tone_prompt(grade_level: str = "K-2") -> str:
    """Get tone guidelines as a prompt for LLM."""
    
    guidelines = TONE_GUIDELINES.get(grade_level, TONE_GUIDELINES["K-2"])
    
    prompt = f"""
TONE GUIDELINES FOR {grade_level} STUDENTS:

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
    
    prompt += f"""

GOOD OPENING PHRASES:
{chr(10).join(f'• "{p}"' for p in guidelines.get('opening_phrases', [])[:3])}

ENCOURAGEMENT TO ADD:
{chr(10).join(f'• "{e}"' for e in guidelines.get('encouragement', [])[:2])}

remember: write like innocent drinks - chatty, humble, a bit cheeky. like a nice friend who happens to know maths. no corporate speak. no fake enthusiasm. just... nice.
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
