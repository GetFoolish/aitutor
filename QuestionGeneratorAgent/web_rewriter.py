"""
Web-based Question Regenerator
Run this and open http://localhost:5000 in your browser

IMPORTANT: API calls are disabled by default.
Click "Enable APIs" button to allow real API calls (with your permission).
"""

import json
import re
import sys
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request

sys.path.insert(0, str(Path(__file__).parent.parent))

from QuestionGeneratorAgent.rewrite_image_questions import ImageQuestionRewriter
from QuestionGeneratorAgent.question_regenerator import QuestionRegenerator

app = Flask(__name__)

# Global storage
rewriter = None
regenerator = None
questions = []
apis_enabled = False

# API Key - loaded from environment or set manually
API_KEY = None  # Will be set via /set-api-key endpoint


def convert_graphie_url(url):
    """Convert web+graphie:// URL to actual image URL"""
    if url.startswith('web+graphie://'):
        path = url.replace('web+graphie://', '')
        return f'https://{path}.svg'
    return url


def load_question_file(file_path):
    """Load a question JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data['_file_path'] = str(file_path)
    data['_file_name'] = file_path.name
    return data


def extract_images_from_question(data):
    """Extract all image info from a question."""
    images = {}
    question_widgets = data.get('question', {}).get('widgets', {})
    for name, widget in question_widgets.items():
        if widget.get('type') == 'image':
            opts = widget.get('options', {})
            alt = opts.get('alt', '')
            url = opts.get('backgroundImage', {}).get('url', '')
            if url:
                images[name] = {
                    'name': name,
                    'alt': alt,
                    'url': convert_graphie_url(url)
                }
    return images


def extract_answers(data):
    """Extract answers from question."""
    answers = {}
    widgets = data.get('question', {}).get('widgets', {})
    for name, widget in widgets.items():
        if widget.get('type') == 'numeric-input':
            ans_list = widget.get('options', {}).get('answers', [])
            for ans in ans_list:
                if ans.get('status') == 'correct':
                    answers[name] = ans.get('value')
    return answers


def render_content_with_images(content, images, new_images=None):
    """Replace placeholders with actual images."""
    img_source = new_images if new_images else images

    def replace_placeholder(match):
        widget_name = match.group(1).strip()
        if widget_name in img_source:
            img = img_source[widget_name]
            url = img.get('url', '')
            alt = img.get('alt', '')
            return f'<img src="{url}" alt="{alt}" class="question-image" title="{alt}">'
        elif widget_name.startswith('numeric-input'):
            return '<span class="input-box">[____]</span>'
        elif widget_name.startswith('radio'):
            return '<span class="input-box">[CHOICE]</span>'
        return f'[{widget_name}]'

    rendered = re.sub(r'\[\[☃\s*([^\]]+)\]\]', replace_placeholder, content)
    rendered = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', rendered)
    rendered = re.sub(r'\$([^$]+)\$', r'<span class="math">\1</span>', rendered)
    rendered = rendered.replace('\n', '<br>')
    return rendered


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Question Regenerator</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }
        h1 { color: #00d9ff; border-bottom: 3px solid #00d9ff; padding-bottom: 10px; }

        .api-status {
            background: #2d2d44;
            padding: 16px 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff4444;
        }
        .status-indicator.enabled { background: #44ff44; }
        .api-status input {
            flex: 1;
            padding: 10px;
            border: 1px solid #444;
            border-radius: 4px;
            background: #1a1a2e;
            color: #eee;
            font-family: monospace;
        }

        .question-card {
            background: #2d2d44;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .question-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .question-title { font-size: 18px; font-weight: 600; color: #00d9ff; }
        .question-type {
            background: #00d9ff22;
            color: #00d9ff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
        }

        .comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .section-label {
            font-weight: 600;
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .rendered-question {
            background: #1a1a2e;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 20px;
            font-size: 15px;
            line-height: 1.8;
            min-height: 200px;
        }
        .rendered-question.original { border-color: #ff6b6b; }
        .rendered-question.regenerated { border-color: #51cf66; }

        .question-image {
            display: inline-block;
            max-width: 100px;
            max-height: 80px;
            vertical-align: middle;
            margin: 4px;
            border: 1px solid #555;
            border-radius: 4px;
            background: white;
        }
        .input-box {
            display: inline-block;
            background: #00d9ff22;
            border: 2px solid #00d9ff;
            border-radius: 4px;
            padding: 2px 12px;
            font-weight: bold;
            color: #00d9ff;
        }
        .math { font-family: 'Times New Roman', serif; font-style: italic; }

        .answers {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .answer-box {
            background: #1a1a2e;
            padding: 12px 16px;
            border-radius: 8px;
            flex: 1;
            text-align: center;
        }
        .answer-label { font-size: 11px; color: #888; margin-bottom: 4px; }
        .answer-value { font-weight: 600; font-size: 24px; color: #51cf66; }
        .answer-value.original { color: #ff6b6b; }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s;
            margin-right: 10px;
        }
        .btn-regenerate { background: #00d9ff; color: #1a1a2e; }
        .btn-regenerate:hover { background: #00b8d4; }
        .btn-regenerate:disabled { background: #444; color: #888; cursor: not-allowed; }
        .btn-correct { background: #51cf66; color: #1a1a2e; }
        .btn-wrong { background: #ff6b6b; color: #1a1a2e; }
        .btn-enable { background: #ffd43b; color: #1a1a2e; }

        .status {
            display: inline-block;
            margin-left: 10px;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 13px;
        }
        .status-loading { background: #ffd43b22; color: #ffd43b; }
        .status-success { background: #51cf6622; color: #51cf66; }
        .status-error { background: #ff6b6b22; color: #ff6b6b; }

        .feedback-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #444;
            display: none;
        }
        .feedback-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #444;
            border-radius: 8px;
            background: #1a1a2e;
            color: #eee;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .summary h2 { margin: 0 0 10px 0; color: white; }
        .summary-stats { display: flex; gap: 40px; }
        .stat { text-align: center; }
        .stat-value { font-size: 32px; font-weight: bold; }
        .stat-label { font-size: 12px; opacity: 0.8; }

        .warning-box {
            background: #ff6b6b22;
            border: 1px solid #ff6b6b;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
            color: #ff6b6b;
        }
    </style>
</head>
<body>
    <h1>Question Regenerator</h1>

    <div class="api-status">
        <div class="status-indicator" id="api-indicator"></div>
        <span id="api-status-text">APIs DISABLED</span>
        <input type="password" id="api-key-input" placeholder="Paste OpenRouter API key here...">
        <button class="btn btn-enable" id="btn-enable" onclick="enableAPIs()">Enable APIs</button>
        <button class="btn btn-wrong" id="btn-disable" onclick="disableAPIs()" style="display:none;">Disable APIs</button>
    </div>

    <div class="warning-box" id="warning-box">
        ⚠️ APIs are currently DISABLED. Questions will show placeholder images only.
        To generate real images with LLM, enter your API key and click "Enable APIs".
    </div>

    <div class="summary">
        <h2>Question Review</h2>
        <div class="summary-stats">
            <div class="stat">
                <div class="stat-value" id="total-count">{{ questions|length }}</div>
                <div class="stat-label">Total</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="regenerated-count">0</div>
                <div class="stat-label">Regenerated</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="correct-count">0</div>
                <div class="stat-label">Correct</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="wrong-count">0</div>
                <div class="stat-label">Wrong</div>
            </div>
        </div>
    </div>

    <div id="questions-container">
        {% for q in questions %}
        <div class="question-card" id="card-{{ loop.index0 }}">
            <div class="question-header">
                <div class="question-title">#{{ loop.index }}: {{ q.file }}</div>
                <div class="question-type">{{ q.type }}</div>
            </div>

            <div class="comparison">
                <div>
                    <div class="section-label">ORIGINAL ({{ q.original_answer }})</div>
                    <div class="rendered-question original">{{ q.original_rendered|safe }}</div>
                </div>
                <div>
                    <div class="section-label">REGENERATED (easier)</div>
                    <div class="rendered-question regenerated" id="regenerated-{{ loop.index0 }}">
                        Click "Regenerate" to create easier version
                    </div>
                </div>
            </div>

            <div class="answers">
                <div class="answer-box">
                    <div class="answer-label">Original Answer</div>
                    <div class="answer-value original">{{ q.original_answer }}</div>
                </div>
                <div class="answer-box">
                    <div class="answer-label">New Answer</div>
                    <div class="answer-value" id="new-answer-{{ loop.index0 }}">?</div>
                </div>
            </div>

            <div>
                <button class="btn btn-regenerate" onclick="regenerateQuestion({{ loop.index0 }})">
                    Regenerate (Easier)
                </button>
                <button class="btn btn-correct" onclick="markCorrect({{ loop.index0 }})">Correct</button>
                <button class="btn btn-wrong" onclick="markWrong({{ loop.index0 }})">Wrong</button>
                <span class="status" id="status-{{ loop.index0 }}" style="display:none;"></span>
            </div>

            <div class="feedback-section" id="feedback-{{ loop.index0 }}">
                <input type="text" class="feedback-input" id="feedback-input-{{ loop.index0 }}"
                       placeholder="What's wrong? Tell me...">
                <button class="btn btn-regenerate" onclick="submitFeedback({{ loop.index0 }})">Submit</button>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        let apisEnabled = false;
        let stats = { regenerated: 0, correct: 0, wrong: 0 };

        function updateStats() {
            document.getElementById('regenerated-count').textContent = stats.regenerated;
            document.getElementById('correct-count').textContent = stats.correct;
            document.getElementById('wrong-count').textContent = stats.wrong;
        }

        function setStatus(idx, message, type) {
            const status = document.getElementById('status-' + idx);
            status.style.display = 'inline-block';
            status.className = 'status status-' + type;
            status.textContent = message;
        }

        async function enableAPIs() {
            const apiKey = document.getElementById('api-key-input').value;
            if (!apiKey) {
                alert('Please enter your API key first');
                return;
            }

            const response = await fetch('/enable-apis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            });

            const data = await response.json();
            if (data.success) {
                apisEnabled = true;
                document.getElementById('api-indicator').classList.add('enabled');
                document.getElementById('api-status-text').textContent = 'APIs ENABLED';
                document.getElementById('warning-box').style.display = 'none';
                document.getElementById('api-key-input').value = '';
                document.getElementById('btn-enable').style.display = 'none';
                document.getElementById('btn-disable').style.display = 'inline-block';
            }
        }

        async function disableAPIs() {
            const response = await fetch('/disable-apis', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                apisEnabled = false;
                document.getElementById('api-indicator').classList.remove('enabled');
                document.getElementById('api-status-text').textContent = 'APIs DISABLED';
                document.getElementById('warning-box').style.display = 'block';
                document.getElementById('btn-enable').style.display = 'inline-block';
                document.getElementById('btn-disable').style.display = 'none';
            }
        }

        async function regenerateQuestion(idx) {
            setStatus(idx, 'Regenerating...', 'loading');

            try {
                const response = await fetch('/regenerate/' + idx, { method: 'POST' });
                const data = await response.json();

                if (data.success) {
                    document.getElementById('regenerated-' + idx).innerHTML = data.rendered_html;
                    document.getElementById('new-answer-' + idx).textContent = data.new_answer;
                    setStatus(idx, 'Done!', 'success');
                    stats.regenerated++;
                    updateStats();
                } else {
                    setStatus(idx, 'Error: ' + data.error, 'error');
                }
            } catch (err) {
                setStatus(idx, 'Error: ' + err.message, 'error');
            }
        }

        function markCorrect(idx) {
            document.getElementById('card-' + idx).style.borderLeft = '4px solid #51cf66';
            setStatus(idx, 'CORRECT', 'success');
            stats.correct++;
            updateStats();
        }

        function markWrong(idx) {
            document.getElementById('card-' + idx).style.borderLeft = '4px solid #ff6b6b';
            document.getElementById('feedback-' + idx).style.display = 'block';
            setStatus(idx, 'WRONG', 'error');
            stats.wrong++;
            updateStats();
        }

        async function submitFeedback(idx) {
            const feedback = document.getElementById('feedback-input-' + idx).value;
            await fetch('/feedback/' + idx, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feedback: feedback })
            });
            setStatus(idx, 'Feedback saved', 'success');
            document.getElementById('feedback-' + idx).style.display = 'none';
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    global rewriter, questions

    curriculum_dir = Path(__file__).parent.parent / "SherlockEDApi" / "CurriculumBuilder"
    rewriter = ImageQuestionRewriter(curriculum_dir)
    loaded = rewriter.load_image_questions(limit=50)

    questions = []
    for q in loaded[:10]:
        file_path = q.file_path
        data = load_question_file(file_path)
        images = extract_images_from_question(data)
        answers = extract_answers(data)

        content = data.get('question', {}).get('content', '')
        original_rendered = render_content_with_images(content, images)

        # Calculate original answer
        original_answer = list(answers.values())[-1] if answers else '?'

        questions.append({
            'file': file_path.name,
            'type': q.question_type,
            'data': data,
            'images': images,
            'original_content': content,
            'original_rendered': original_rendered,
            'original_answer': original_answer,
            'answers': answers
        })

    return render_template_string(HTML_TEMPLATE, questions=questions)


@app.route('/enable-apis', methods=['POST'])
def enable_apis():
    global regenerator, apis_enabled, API_KEY

    data = request.json
    API_KEY = data.get('api_key', '')

    if API_KEY:
        regenerator = QuestionRegenerator(API_KEY)
        regenerator.enable_apis()
        apis_enabled = True
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'No API key provided'})


@app.route('/disable-apis', methods=['POST'])
def disable_apis():
    global regenerator, apis_enabled, API_KEY

    if regenerator:
        regenerator.disable_apis()
    apis_enabled = False
    API_KEY = None

    return jsonify({'success': True})


@app.route('/regenerate/<int:idx>', methods=['POST'])
def regenerate(idx):
    global questions, regenerator, apis_enabled

    try:
        if idx >= len(questions):
            return jsonify({'success': False, 'error': 'Invalid index'})

        q = questions[idx]

        if regenerator is None:
            # Create regenerator without API key - will use placeholders
            regenerator = QuestionRegenerator("")

        result = regenerator.regenerate_question(q['data'], target_difficulty="easier")

        # Build new images dict
        new_images = {}
        for img in result.new_images:
            new_images[img['name']] = img

        # Render the new content with new images
        rendered_html = render_content_with_images(result.new_content, q['images'], new_images)

        return jsonify({
            'success': True,
            'rendered_html': rendered_html,
            'new_answer': result.new_answer,
            'changes': result.changes_made
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/feedback/<int:idx>', methods=['POST'])
def feedback(idx):
    data = request.json
    feedback_text = data.get('feedback', '')

    print(f"FEEDBACK for question {idx}: {feedback_text}")

    feedback_file = Path(__file__).parent / "feedback.json"
    try:
        if feedback_file.exists():
            with open(feedback_file, 'r') as f:
                all_feedback = json.load(f)
        else:
            all_feedback = []

        all_feedback.append({
            'question_idx': idx,
            'question_file': questions[idx]['file'] if idx < len(questions) else 'unknown',
            'feedback': feedback_text
        })

        with open(feedback_file, 'w') as f:
            json.dump(all_feedback, f, indent=2)
    except Exception as e:
        print(f"Error saving feedback: {e}")

    return jsonify({'success': True})


if __name__ == '__main__':
    print("=" * 60)
    print("QUESTION REGENERATOR")
    print("=" * 60)
    print("\nOpen http://localhost:5000")
    print("\nAPIs are DISABLED by default.")
    print("Enter your API key in the web interface to enable.")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    app.run(debug=True, port=5000)
