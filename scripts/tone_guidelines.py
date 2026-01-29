#!/usr/bin/env python3
"""
Tone Guidelines for Question Generation

Provides friendly, encouraging, child-appropriate tone templates
for LLM-based question generation.
"""

# Tone examples by grade level
TONE_GUIDELINES = {
    "K-2": {
        "description": "Warm, playful, encouraging - like a friendly teacher",
        "characteristics": [
            "Use simple, short sentences",
            "Add fun emojis or descriptions",
            "Use 'you' and 'let's' to be inclusive",
            "Celebrate small wins",
            "Use relatable scenarios (toys, animals, snacks)",
        ],
        "example_rewrites": [
            {
                "before": "Count the objects. How many are there?",
                "after": "🎈 Look at all these colorful balloons! Can you count them with me? How many do you see?"
            },
            {
                "before": "What is 3 + 2?",
                "after": "You have 3 yummy cookies, and your friend gives you 2 more! 🍪 How many cookies do you have now?"
            },
            {
                "before": "Select the correct answer.",
                "after": "You're doing great! Which answer looks right to you?"
            }
        ],
        "opening_phrases": [
            "Let's have some fun with numbers!",
            "You're doing amazing!",
            "Here's a fun puzzle for you:",
            "Can you help me figure this out?",
            "Great job so far! Now try this:",
        ],
        "encouragement": [
            "You've got this! 🌟",
            "Take your time, no rush!",
            "It's okay to try again!",
            "You're getting better every day!",
        ]
    },
    
    "3-5": {
        "description": "Friendly, curious, building confidence",
        "characteristics": [
            "Encourage problem-solving thinking",
            "Use real-world scenarios",
            "Build on what they know",
            "Celebrate effort, not just correctness",
        ],
        "example_rewrites": [
            {
                "before": "Calculate the area of the rectangle.",
                "after": "Imagine you're designing a cool poster! 🎨 If your poster is 5 inches wide and 8 inches tall, how much space do you have to draw on?"
            },
            {
                "before": "Solve for x: 2x + 4 = 10",
                "after": "Here's a mystery number puzzle! 🔍 If you double a secret number and add 4, you get 10. What's the secret number?"
            }
        ],
        "opening_phrases": [
            "Here's a brain teaser for you!",
            "Let's think like a detective:",
            "Imagine this scenario:",
            "You're getting really good at this!",
        ]
    },
    
    "6-8": {
        "description": "Respectful, challenging, real-world connections",
        "characteristics": [
            "Connect to their interests (games, sports, tech)",
            "Challenge them appropriately",
            "Explain WHY it matters",
            "Treat them as capable learners",
        ],
        "example_rewrites": [
            {
                "before": "Find the slope of the line passing through (2,3) and (5,9).",
                "after": "In a video game, your character moves from position (2,3) to (5,9). How steep is the path they're taking? (That's the slope!)"
            }
        ]
    },
    
    "9-12": {
        "description": "Mature, practical, career-connected",
        "characteristics": [
            "Connect to real careers and applications",
            "Respect their intelligence",
            "Show relevance to their future",
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

Remember: Questions should feel like they're from a friendly, encouraging teacher who believes in the student!
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
