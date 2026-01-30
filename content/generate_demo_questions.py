#!/usr/bin/env python3
"""
Generate 10 demo questions with:
- Innocent Drinks tone of voice
- Memory personalization (interests, pets, etc.)
- Different widget types
"""

import json
import os
import sys
import time
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Sample user memories for demo
DEMO_USER_MEMORIES = """
USER MEMORIES (use these to personalize questions):

interests/likes:
  - loves dinosaurs, especially T-Rex
  - really into space and planets
  - plays minecraft all the time
  - enjoys baking cookies with mom

pets:
  - has a golden retriever called Buddy
  - recently got a hamster named Nugget

family:
  - younger sister called Emma (she's 5)
  - grandma makes the best pancakes

things they find tricky (be extra gentle here):
  - sometimes confused by word problems
  - fractions are hard

things they're good at (can reference these for confidence):
  - really quick with addition
  - great at spotting patterns
"""

# Tone guidelines (Innocent Drinks style)
TONE_GUIDELINES = """
TONE GUIDELINES (innocent drinks style):

Write like innocent drinks - chatty, humble, a bit cheeky. Like a nice friend who happens to know maths.

WRITING STYLE:
• lowercase where possible, casual punctuation
• short sentences. like this. easy peasy.
• slightly self-aware and playful
• no corporate speak, no trying too hard
• gentle humour, never mean
• talk like a real person, not a textbook

EXAMPLE REWRITES:
❌ Instead of: "Count the objects. How many are there?"
✅ Write like: "so there are some apples here. have a count. how many did you get?"

❌ Instead of: "What is 3 + 2?"
✅ Write like: "you've got 3 apples. someone nice gives you 2 more. how many now? (we believe in you)"

❌ Instead of: "Select the correct answer."
✅ Write like: "pick the one you reckon is right. no pressure."

CRITICAL: every question MUST have a different opening. never repeat.

PICK ONE UNIQUE OPENER (never use the same one twice):
• "so here's the thing."
• "have a go at this."
• "here we go."
• "this one's interesting."
• "quick one."
• "try this."
• "alright."
• "ooh, this is good."
• "here's a puzzle."
• dive straight into the scenario (no opener)

BANNED PHRASES (do not use these):
• "right then"
• "right,"
• "okay this is a fun one"
• "okay, try this one"

just get into it. be natural. vary it up.

ENCOURAGEMENT TO ADD:
• "(no rush, we'll wait)"
• "(you've got this)"
• "(take your time)"
"""

# Widget type specifications
WIDGET_SPECS = {
    "radio": {
        "description": "Multiple choice with radio buttons",
        "example": {
            "content": "**question goes here**\n\n[[☃ radio 1]]",
            "widgets": {
                "radio 1": {
                    "type": "radio",
                    "options": {
                        "choices": [
                            {"content": "option A", "correct": False},
                            {"content": "option B", "correct": True},
                            {"content": "option C", "correct": False}
                        ]
                    }
                }
            }
        }
    },
    "numeric-input": {
        "description": "Single number answer input",
        "example": {
            "content": "**question goes here**\n\n[[☃ numeric-input 1]]",
            "widgets": {
                "numeric-input 1": {
                    "type": "numeric-input",
                    "options": {
                        "answers": [{"value": 42, "status": "correct"}],
                        "size": "normal"
                    }
                }
            }
        }
    },
    "dropdown": {
        "description": "Dropdown selection from options",
        "example": {
            "content": "**question goes here** [[☃ dropdown 1]]",
            "widgets": {
                "dropdown 1": {
                    "type": "dropdown",
                    "options": {
                        "choices": [
                            {"content": "option A", "correct": False},
                            {"content": "option B", "correct": True}
                        ]
                    }
                }
            }
        }
    },
    "orderer": {
        "description": "Drag items into correct order",
        "example": {
            "content": "**put these in order**\n\n[[☃ orderer 1]]",
            "widgets": {
                "orderer 1": {
                    "type": "orderer",
                    "options": {
                        "options": ["first", "second", "third"],
                        "correctOptions": ["first", "second", "third"]
                    }
                }
            }
        }
    },
    "sorter": {
        "description": "Sort items into categories",
        "example": {
            "content": "**sort these**\n\n[[☃ sorter 1]]",
            "widgets": {
                "sorter 1": {
                    "type": "sorter",
                    "options": {
                        "correct": ["item1", "item2", "item3"]
                    }
                }
            }
        }
    },
    "expression": {
        "description": "Math expression input (algebra)",
        "example": {
            "content": "**question goes here**\n\n[[☃ expression 1]]",
            "widgets": {
                "expression 1": {
                    "type": "expression",
                    "options": {
                        "answerForms": [{"value": "x+2", "form": True, "simplify": False}]
                    }
                }
            }
        }
    },
    "input-number": {
        "description": "Number input with validation",
        "example": {
            "content": "**question goes here**\n\n[[☃ input-number 1]]",
            "widgets": {
                "input-number 1": {
                    "type": "input-number",
                    "options": {
                        "value": 42,
                        "simplify": "required"
                    }
                }
            }
        }
    },
    "matcher": {
        "description": "Match items from two columns",
        "example": {
            "content": "**match these up**\n\n[[☃ matcher 1]]",
            "widgets": {
                "matcher 1": {
                    "type": "matcher",
                    "options": {
                        "left": ["A", "B", "C"],
                        "right": ["1", "2", "3"],
                        "labels": ["items", "numbers"]
                    }
                }
            }
        }
    },
    "categorizer": {
        "description": "Sort items into category buckets",
        "example": {
            "content": "**sort into groups**\n\n[[☃ categorizer 1]]",
            "widgets": {
                "categorizer 1": {
                    "type": "categorizer",
                    "options": {
                        "categories": ["group1", "group2"],
                        "items": ["item1", "item2", "item3"],
                        "values": [0, 1, 0]
                    }
                }
            }
        }
    },
    "number-line": {
        "description": "Plot point on number line",
        "example": {
            "content": "**plot the number**\n\n[[☃ number-line 1]]",
            "widgets": {
                "number-line 1": {
                    "type": "number-line",
                    "options": {
                        "range": [0, 10],
                        "correctRel": "eq",
                        "correctX": 5
                    }
                }
            }
        }
    }
}

# Question topics to generate
QUESTIONS_TO_GENERATE = [
    {"topic": "addition", "widget": "numeric-input", "grade": "K-2"},
    {"topic": "multiplication", "widget": "radio", "grade": "3-5"},
    {"topic": "fractions", "widget": "dropdown", "grade": "3-5"},
    {"topic": "ordering numbers", "widget": "orderer", "grade": "K-2"},
    {"topic": "place value", "widget": "input-number", "grade": "K-2"},
    {"topic": "matching equivalents", "widget": "matcher", "grade": "3-5"},
    {"topic": "sorting odd/even", "widget": "categorizer", "grade": "K-2"},
    {"topic": "number line", "widget": "number-line", "grade": "K-2"},
    {"topic": "simple algebra", "widget": "expression", "grade": "6-8"},
    {"topic": "word problems", "widget": "radio", "grade": "3-5"},
]


def generate_question(topic: str, widget_type: str, grade: str, used_openers: list = None) -> dict:
    """Generate a single question using Gemini."""
    
    widget_spec = WIDGET_SPECS.get(widget_type, WIDGET_SPECS["radio"])
    
    avoid_openers = ""
    if used_openers:
        avoid_openers = f"\n\nALREADY USED OPENERS (do NOT use these again):\n" + "\n".join(f"- {o}" for o in used_openers[-5:])
    
    prompt = f"""
{DEMO_USER_MEMORIES}

{TONE_GUIDELINES}
{avoid_openers}

---

TASK: Generate a {grade} level question about {topic} using the {widget_type} widget.

WIDGET FORMAT:
{json.dumps(widget_spec['example'], indent=2)}

PERSONALIZATION INSTRUCTIONS:
- Use their interests (dinosaurs, space, minecraft) in the problem
- Use their pet names (Buddy the dog, Nugget the hamster)
- Use family names (sister Emma, grandma)
- Keep the innocent drinks tone - casual, friendly, lowercase
- Add gentle encouragement, especially for fractions (which they find tricky)

Generate a complete question in Perseus format. Return ONLY valid JSON with this structure:
{{
    "content": "the question text with widget placeholder [[☃ {widget_type} 1]]",
    "widgets": {{ ... widget config ... }},
    "hints": [
        {{"content": "hint 1", "widgets": {{}}}},
        {{"content": "hint 2", "widgets": {{}}}}
    ]
}}

Make sure:
1. The content uses the innocent drinks tone
2. It's personalized with memories (pets, interests, family)
3. Widget config has correct answer(s)
4. Include 2-3 helpful, friendly hints

Return ONLY the JSON, no markdown code blocks.
"""
    
    # Retry with backoff for rate limits
    for attempt in range(5):
        try:
            response = model.generate_content(prompt)
            break
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait = (attempt + 1) * 5
                print(f"    Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise
    
    text = response.text.strip()
    
    # Clean up response
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    
    try:
        question_data = json.loads(text)
        question_data['_meta'] = {
            'topic': topic,
            'widget_type': widget_type,
            'grade': grade
        }
        return question_data
    except json.JSONDecodeError as e:
        print(f"JSON parse error for {topic}/{widget_type}: {e}")
        print(f"Response: {text[:500]}")
        return None


def main():
    print("Generating 10 personalized questions with Innocent Drinks tone...\n", flush=True)
    
    questions = []
    used_openers = []
    
    for i, q_spec in enumerate(QUESTIONS_TO_GENERATE):
        print(f"[{i+1}/10] Generating {q_spec['topic']} ({q_spec['widget']})...", flush=True)
        
        question = generate_question(
            topic=q_spec['topic'],
            widget_type=q_spec['widget'],
            grade=q_spec['grade'],
            used_openers=used_openers
        )
        
        if question:
            questions.append(question)
            content = question.get('content', '')
            # Track the opener (first ~30 chars)
            opener = content[:30].lower().strip()
            used_openers.append(opener)
            print(f"  ✓ Generated: {content[:60]}...")
        else:
            print(f"  ✗ Failed to generate")
        
        # Rate limit protection
        time.sleep(2)
    
    # Save to file
    output_path = Path(__file__).parent / "demo_questions.json"
    with open(output_path, "w") as f:
        json.dump(questions, f, indent=2)
    
    print(f"\n✓ Saved {len(questions)} questions to {output_path}")
    
    # Also create HTML preview
    create_html_preview(questions)
    
    return questions


def create_html_preview(questions: list):
    """Create an HTML preview of the questions."""
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Demo Questions - Innocent Drinks Tone</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px; 
            margin: 0 auto; 
            padding: 40px 20px;
            background: #f8f9fa;
            color: #333;
        }
        h1 { 
            text-align: center; 
            color: #2d3436;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #636e72;
            margin-bottom: 40px;
        }
        .question-card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .question-meta {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }
        .tag {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .tag.widget { background: #e3f2fd; color: #1565c0; }
        .tag.grade { background: #fff3e0; color: #ef6c00; }
        .question-content {
            font-size: 18px;
            line-height: 1.6;
            margin-bottom: 20px;
            white-space: pre-wrap;
        }
        .widget-preview {
            background: #f5f5f5;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .widget-title {
            font-size: 12px;
            color: #666;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .radio-option, .dropdown-option {
            padding: 10px 16px;
            background: white;
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            border: 2px solid #e0e0e0;
        }
        .radio-option:hover, .dropdown-option:hover {
            border-color: #90caf9;
        }
        .radio-option.correct {
            border-color: #81c784;
            background: #e8f5e9;
        }
        .numeric-input {
            padding: 12px 16px;
            font-size: 18px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            width: 120px;
        }
        .answer-hint {
            font-size: 13px;
            color: #666;
            font-style: italic;
            margin-top: 8px;
        }
        .hints {
            border-top: 1px solid #eee;
            padding-top: 16px;
            margin-top: 16px;
        }
        .hints-title {
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 12px;
        }
        .hint {
            background: #fff8e1;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 14px;
            border-left: 3px solid #ffc107;
        }
        .orderer-item, .sorter-item {
            background: white;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 2px solid #e0e0e0;
            cursor: grab;
        }
        .orderer-item:hover { border-color: #90caf9; }
        .matcher-container {
            display: flex;
            gap: 20px;
        }
        .matcher-column {
            flex: 1;
        }
        .matcher-item {
            background: white;
            padding: 10px 16px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 2px solid #e0e0e0;
        }
        .number-line-container {
            position: relative;
            height: 60px;
            margin: 20px 0;
        }
        .number-line {
            position: absolute;
            top: 25px;
            left: 0;
            right: 0;
            height: 4px;
            background: #333;
            border-radius: 2px;
        }
        .number-line-tick {
            position: absolute;
            top: 20px;
            width: 2px;
            height: 14px;
            background: #333;
        }
        .number-line-label {
            position: absolute;
            top: 40px;
            font-size: 12px;
            transform: translateX(-50%);
        }
        .expression-input {
            font-family: 'Courier New', monospace;
            padding: 12px 16px;
            font-size: 18px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            width: 200px;
        }
        .categorizer-container {
            display: flex;
            gap: 16px;
        }
        .category-bucket {
            flex: 1;
            background: #f5f5f5;
            border-radius: 12px;
            padding: 16px;
            min-height: 120px;
        }
        .category-title {
            font-weight: 600;
            margin-bottom: 12px;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>🍎 question playground</h1>
    <p class="subtitle">personalized questions with innocent drinks tone + memory</p>
"""
    
    for i, q in enumerate(questions):
        meta = q.get('_meta', {})
        content = q.get('content', 'No content')
        widgets = q.get('widgets', {})
        hints = q.get('hints', [])
        
        # Extract widget info
        widget_type = meta.get('widget_type', 'unknown')
        widget_key = f"{widget_type} 1"
        widget_config = widgets.get(widget_key, {})
        
        html += f"""
    <div class="question-card">
        <div class="question-meta">
            <span class="tag">{meta.get('topic', 'topic')}</span>
            <span class="tag widget">{widget_type}</span>
            <span class="tag grade">{meta.get('grade', 'K-2')}</span>
        </div>
        <div class="question-content">{content.replace('[[☃ ' + widget_key + ']]', '')}</div>
        <div class="widget-preview">
            <div class="widget-title">{widget_type} widget</div>
            {render_widget_preview(widget_type, widget_config)}
        </div>
"""
        
        if hints:
            html += """        <div class="hints">
            <div class="hints-title">💡 hints</div>
"""
            for hint in hints[:3]:
                hint_content = hint.get('content', '') if isinstance(hint, dict) else str(hint)
                html += f"""            <div class="hint">{hint_content}</div>
"""
            html += """        </div>
"""
        
        html += """    </div>
"""
    
    html += """</body>
</html>
"""
    
    preview_path = Path(__file__).parent / "demo_preview.html"
    with open(preview_path, "w") as f:
        f.write(html)
    
    print(f"✓ Created HTML preview at {preview_path}")
    return preview_path


def render_widget_preview(widget_type: str, config: dict) -> str:
    """Render a preview of the widget."""
    
    options = config.get('options', {})
    
    if widget_type == "radio":
        choices = options.get('choices', [])
        html = ""
        for choice in choices:
            content = choice.get('content', '')
            is_correct = choice.get('correct', False)
            cls = "radio-option correct" if is_correct else "radio-option"
            html += f'<div class="{cls}">○ {content}</div>'
        return html
    
    elif widget_type == "numeric-input" or widget_type == "input-number":
        answers = options.get('answers', [{'value': '?'}])
        answer = answers[0].get('value', '?') if answers else '?'
        return f'<input type="text" class="numeric-input" placeholder="?" disabled><div class="answer-hint">correct answer: {answer}</div>'
    
    elif widget_type == "dropdown":
        choices = options.get('choices', [])
        html = '<select class="numeric-input" disabled>'
        for choice in choices:
            content = choice.get('content', '')
            selected = "selected" if choice.get('correct') else ""
            html += f'<option {selected}>{content}</option>'
        html += '</select>'
        correct = next((c['content'] for c in choices if c.get('correct')), '?')
        html += f'<div class="answer-hint">correct: {correct}</div>'
        return html
    
    elif widget_type == "orderer":
        items = options.get('options', options.get('correctOptions', []))
        html = '<div style="display: flex; gap: 8px;">'
        for item in items:
            html += f'<div class="orderer-item">↕️ {item}</div>'
        html += '</div>'
        return html
    
    elif widget_type == "matcher":
        left = options.get('left', [])
        right = options.get('right', [])
        html = '<div class="matcher-container">'
        html += '<div class="matcher-column">'
        for item in left:
            html += f'<div class="matcher-item">{item}</div>'
        html += '</div><div class="matcher-column">'
        for item in right:
            html += f'<div class="matcher-item">{item}</div>'
        html += '</div></div>'
        return html
    
    elif widget_type == "categorizer":
        categories = options.get('categories', [])
        html = '<div class="categorizer-container">'
        for cat in categories:
            html += f'<div class="category-bucket"><div class="category-title">{cat}</div></div>'
        html += '</div>'
        return html
    
    elif widget_type == "number-line":
        range_vals = options.get('range', [0, 10])
        correct = options.get('correctX', 5)
        html = f'<div class="number-line-container">'
        html += '<div class="number-line"></div>'
        html += f'<div class="number-line-tick" style="left: 0;"></div>'
        html += f'<div class="number-line-tick" style="left: 50%;"></div>'
        html += f'<div class="number-line-tick" style="left: 100%;"></div>'
        html += f'<div class="number-line-label" style="left: 0;">{range_vals[0]}</div>'
        html += f'<div class="number-line-label" style="left: 100%;">{range_vals[1]}</div>'
        html += f'</div><div class="answer-hint">correct position: {correct}</div>'
        return html
    
    elif widget_type == "expression":
        forms = options.get('answerForms', [{'value': 'x'}])
        answer = forms[0].get('value', 'x') if forms else 'x'
        return f'<input type="text" class="expression-input" placeholder="expression" disabled><div class="answer-hint">correct: {answer}</div>'
    
    elif widget_type == "sorter":
        items = options.get('correct', [])
        html = '<div style="display: flex; flex-wrap: wrap; gap: 8px;">'
        for item in items:
            html += f'<div class="sorter-item">{item}</div>'
        html += '</div>'
        return html
    
    else:
        return f'<div class="answer-hint">{widget_type} widget</div>'


if __name__ == "__main__":
    main()
