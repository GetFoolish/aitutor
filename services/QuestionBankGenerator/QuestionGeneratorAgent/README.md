# Question Generator Agent

An AI-powered agent that generates variations of educational questions while maintaining difficulty levels and learning objectives.

## Features

- **Multi-subject Support**: Math, Science, History, Arts, etc.
- **Smart Validation**: Mathematical correctness checking and fact-based validation
- **Duplicate Detection**: Prevents generating similar questions
- **Source Attribution**: Tracks sources for fact-based questions
- **Metadata Tracking**: Records generation details, model used, timestamps

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   - Get an API key from [OpenRouter](https://openrouter.ai/keys)
   - Add to `.env` file:
     ```
     OPENROUTER_API_KEY=your_key_here
     ```

3. **Configure Models** (optional):
   - Edit `config.json` to change LLM models
   - Default: Claude 3 Haiku for generation, GPT-4 Turbo for validation

## Usage

```python
from QuestionGeneratorAgent import QuestionGeneratorAgent

# Initialize agent
generator = QuestionGeneratorAgent()

# Generate math question variations
new_questions = generator.generate_variations(
    source_question_id="g1_add_1",
    num_variations=3,
    subject="math"
)

# Generate science question variations
new_questions = generator.generate_variations(
    source_question_id="g5_sci_1",
    num_variations=2,
    subject="science"
)
```

## Architecture

```
QuestionGeneratorAgent/
├── question_generator_agent.py  # Main agent logic
├── validators.py               # Subject-specific validation
└── README.md                   # This file

LLMBase/                        # Shared LLM components
├── llm_client.py              # OpenRouter API client
└── __init__.py

config.json                     # Model configurations
.env                           # API keys
```

## Generated Question Structure

```json
{
  "question_id": "g1_add_1_gen_001",
  "content": "What is 4 + 7?",
  "difficulty": 0.1,
  "expected_time_seconds": 30,
  "correct_answer": "11",
  "metadata": {
    "generated": true,
    "source_question_id": "g1_add_1",
    "generated_at": "2024-01-20T10:30:00Z",
    "subject": "math",
    "explanation": "Changed numbers from 2+3 to 4+7",
    "model_used": "anthropic/claude-3-haiku"
  }
}
```

## Validation Types

- **Math**: Checks mathematical correctness, equation formats, numeric validity
- **Fact-based**: Validates sources, checks content length, ensures proper attribution

## Future Enhancements

- [ ] Batch processing for efficiency
- [ ] Difficulty adjustment algorithms
- [ ] Multi-language support
- [ ] Image-based question generation
- [ ] Integration with external fact-checking APIs