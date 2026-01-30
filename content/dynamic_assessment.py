#!/usr/bin/env python3
"""
Dynamic Assessment Generator

Generates assessment questions on-the-fly based on:
- Age/grade level
- Selected topics
- Difficulty mix (easy/medium/hard)

Uses the question generator to create personalized assessment questions.
"""

import os
import sys
import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import MongoClient
from dotenv import load_dotenv
from content.question_generator import QuestionGenerator

# Load environment variables (supports running without run_tutor.sh)
load_dotenv()

# MongoDB
mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")
client = MongoClient(mongodb_uri)
db = client[db_name]


def get_grade_from_age_range(age_range: str) -> str:
    """Map age range to grade level."""
    mapping = {
        '5-7': 'K-2',
        '8-10': '3-5',
        '11-13': '6-8',
        '14-17': '9-12',
        '18+': '9-12',  # Adult uses high school level
    }
    return mapping.get(age_range, '3-5')


def generate_assessment_questions(
    user_id: str,
    age_range: str,
    topics: List[str],
    question_count: int = 10,
    user_memories: Optional[Dict] = None,
    grade_override: Optional[str] = None
) -> Dict:
    """
    Generate a dynamic assessment with mixed difficulty questions.
    
    Args:
        user_id: User identifier
        age_range: Age range string (e.g., '8-10')
        topics: List of topics to assess
        question_count: Total questions to generate
        user_memories: Optional user memories for personalization
    
    Returns:
        Assessment data with questions
    """
    grade = grade_override or get_grade_from_age_range(age_range)
    
    # Calculate difficulty distribution (40% easy, 40% medium, 20% hard)
    easy_count = int(question_count * 0.4)
    medium_count = int(question_count * 0.4)
    hard_count = question_count - easy_count - medium_count
    
    # Initialize generator
    generator = QuestionGenerator()
    
    # Generate questions for each difficulty level
    all_questions = []
    generated_questions_to_store = []
    assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
    
    # Map topics to subjects
    topic_to_subject = {
        'math-basics': 'math',
        'algebra': 'math',
        'geometry': 'math',
        'fractions': 'math',
        'word-problems': 'math',
        'statistics': 'math',
        'reading': 'english',
        'writing': 'english',
        'science': 'science',
        'coding': 'computer_science',
    }
    
    # Difficulty-appropriate topic mappings
    difficulty_topics = {
        'easy': {
            'math-basics': ['counting', 'addition', 'subtraction'],
            'algebra': ['simple_equations'],
            'geometry': ['basic_shapes'],
            'fractions': ['simple_fractions'],
            'word-problems': ['simple_word_problems'],
        },
        'medium': {
            'math-basics': ['multiplication', 'division'],
            'algebra': ['linear_equations'],
            'geometry': ['area_perimeter'],
            'fractions': ['fraction_operations'],
            'word-problems': ['multi_step_problems'],
        },
        'hard': {
            'math-basics': ['order_of_operations'],
            'algebra': ['systems_of_equations'],
            'geometry': ['volume_surface_area'],
            'fractions': ['mixed_numbers'],
            'word-problems': ['complex_word_problems'],
        }
    }
    
    # Widget types to use for different difficulties
    difficulty_widgets = {
        'easy': ['radio', 'numeric-input'],  # Multiple choice and simple input
        'medium': ['numeric-input', 'dropdown'],  # More thinking required
        'hard': ['numeric-input', 'orderer'],  # Complex problem solving
    }
    
    # Generate questions per difficulty
    for difficulty, count in [('easy', easy_count), ('medium', medium_count), ('hard', hard_count)]:
        for topic in topics[:3]:  # Limit to top 3 topics
            subject = topic_to_subject.get(topic, 'math')
            sub_topics = difficulty_topics.get(difficulty, {}).get(topic, [topic])
            widgets = difficulty_widgets.get(difficulty, ['numeric-input'])
            
            questions_per_topic = max(1, count // len(topics[:3]))
            
            for sub_topic in sub_topics[:questions_per_topic]:
                widget_type = widgets[len(all_questions) % len(widgets)]
                
                try:
                    # Use correct parameters for generate_question
                    question = generator.generate_question(
                        topic=sub_topic,
                        widget_type=widget_type,
                        grade=grade,
                        subject=subject,
                        user_memories=str(user_memories) if user_memories else None
                    )
                    
                    if question:
                        if hasattr(question, '__dict__'):
                            generated_questions_to_store.append(question)
                        # Convert to dict if it's a dataclass
                        if hasattr(question, '__dict__'):
                            q_dict = {
                                'question_id': question.question_id,
                                'question': question.question,
                                'answer_area': question.answer_area,
                                'hints': question.hints,
                                'grade': question.grade,
                                'subject': question.subject,
                                'topic': question.topic,
                            }
                        else:
                            q_dict = question
                        
                        # Add assessment metadata
                        q_dict['assessment_id'] = assessment_id
                        q_dict['difficulty'] = difficulty
                        q_dict['original_topic'] = topic
                        q_dict['order'] = len(all_questions)
                        all_questions.append(q_dict)
                        
                except Exception as e:
                    print(f"[ASSESSMENT] Failed to generate {difficulty} question for {topic}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                if len(all_questions) >= question_count:
                    break
            
            if len(all_questions) >= question_count:
                break
    
    # Shuffle questions to mix difficulties
    import random
    random.shuffle(all_questions)
    
    # Re-number after shuffle
    for i, q in enumerate(all_questions):
        q['order'] = i
    
    # Convert to Perseus format for frontend
    perseus_questions = []
    for q in all_questions:
        perseus_item = {
            "question": q.get("question", {}),
            "answerArea": q.get("answer_area", {}),
            "hints": q.get("hints", []),
            "itemDataVersion": {"major": 0, "minor": 1},
            "dash_metadata": {
                "dash_question_id": q.get("question_id"),
                "assessment_id": assessment_id,
                "difficulty": q.get("difficulty"),
                "topic": q.get("original_topic"),
                "skill_ids": [f"assess_{q.get('topic', 'unknown')}"],
                "skill_names": [q.get("topic", "Assessment")],
                "grade": grade,
                "source": "dynamic_assessment"
            }
        }
        perseus_questions.append(perseus_item)
    
    # Store assessment in MongoDB
    assessment_doc = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "age_range": age_range,
        "grade": grade,
        "topics": topics,
        "question_count": len(perseus_questions),
        "questions": perseus_questions,
        "status": "in_progress",
        "created_at": datetime.utcnow(),
        "results": None
    }
    
    db.assessments.insert_one(assessment_doc)

    # Store generated questions in MongoDB content library for reuse
    if generated_questions_to_store:
        try:
            generator.save_to_mongodb(generated_questions_to_store)
        except Exception as e:
            print(f"[ASSESSMENT] Failed to store generated questions: {e}")
    
    return {
        "assessment_id": assessment_id,
        "questions": perseus_questions,
        "total_questions": len(perseus_questions),
        "grade": grade,
        "topics": topics
    }


def complete_assessment(
    assessment_id: str,
    answers: List[Dict]
) -> Dict:
    """
    Complete an assessment and generate learning path.
    
    Args:
        assessment_id: Assessment identifier
        answers: List of {question_id, is_correct, difficulty, topic}
    
    Returns:
        Assessment results with recommended learning path
    """
    # Calculate scores by topic and difficulty
    topic_scores = {}
    difficulty_scores = {'easy': {'correct': 0, 'total': 0},
                         'medium': {'correct': 0, 'total': 0},
                         'hard': {'correct': 0, 'total': 0}}
    
    for answer in answers:
        topic = answer.get('topic', 'unknown')
        difficulty = answer.get('difficulty', 'medium')
        is_correct = answer.get('is_correct', False)
        
        if topic not in topic_scores:
            topic_scores[topic] = {'correct': 0, 'total': 0}
        
        topic_scores[topic]['total'] += 1
        difficulty_scores[difficulty]['total'] += 1
        
        if is_correct:
            topic_scores[topic]['correct'] += 1
            difficulty_scores[difficulty]['correct'] += 1
    
    # Calculate overall score
    total_correct = sum(d['correct'] for d in difficulty_scores.values())
    total_questions = sum(d['total'] for d in difficulty_scores.values())
    overall_score = total_correct / total_questions if total_questions > 0 else 0
    
    # Determine skill level
    easy_pct = difficulty_scores['easy']['correct'] / max(1, difficulty_scores['easy']['total'])
    medium_pct = difficulty_scores['medium']['correct'] / max(1, difficulty_scores['medium']['total'])
    hard_pct = difficulty_scores['hard']['correct'] / max(1, difficulty_scores['hard']['total'])
    
    if hard_pct >= 0.7:
        skill_level = 'advanced'
        start_difficulty = 'medium'
    elif medium_pct >= 0.7:
        skill_level = 'intermediate'
        start_difficulty = 'easy-medium'
    elif easy_pct >= 0.7:
        skill_level = 'beginner'
        start_difficulty = 'easy'
    else:
        skill_level = 'foundations'
        start_difficulty = 'easy'
    
    # Create learning path recommendations
    weak_topics = [
        topic for topic, scores in topic_scores.items()
        if scores['correct'] / max(1, scores['total']) < 0.6
    ]
    
    strong_topics = [
        topic for topic, scores in topic_scores.items()
        if scores['correct'] / max(1, scores['total']) >= 0.8
    ]
    
    learning_path = {
        "skill_level": skill_level,
        "recommended_start_difficulty": start_difficulty,
        "focus_topics": weak_topics,
        "strong_topics": strong_topics,
        "suggested_daily_questions": 10 if skill_level == 'foundations' else 15,
        "estimated_sessions_to_mastery": {
            topic: max(1, 5 - int(scores['correct'] / max(1, scores['total']) * 5))
            for topic, scores in topic_scores.items()
        }
    }
    
    # Update assessment in MongoDB
    results = {
        "overall_score": overall_score,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "topic_scores": topic_scores,
        "difficulty_scores": difficulty_scores,
        "skill_level": skill_level,
        "learning_path": learning_path,
        "completed_at": datetime.utcnow()
    }
    
    db.assessments.update_one(
        {"assessment_id": assessment_id},
        {"$set": {"status": "completed", "results": results}}
    )
    
    return results


# API endpoint functions (called from dash_api.py)
def create_dynamic_assessment_endpoint(user_id: str, data: Dict) -> Dict:
    """API endpoint handler for creating dynamic assessment."""
    return generate_assessment_questions(
        user_id=user_id,
        age_range=data.get('age_range', '8-10'),
        topics=data.get('topics', ['math-basics']),
        question_count=data.get('question_count', 10),
        user_memories=data.get('user_memories'),
        grade_override=data.get('grade')
    )


def complete_assessment_endpoint(assessment_id: str, answers: List[Dict]) -> Dict:
    """API endpoint handler for completing assessment."""
    return complete_assessment(assessment_id, answers)
