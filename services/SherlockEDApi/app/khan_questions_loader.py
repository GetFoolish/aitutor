# Load questions from MongoDB instead of local files
import json
import os
import random
import sys
import time
from typing import List, Dict, Optional

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

from shared.logging_config import get_logger

logger = get_logger(__name__)

# Cache for parsed questions - loaded once at startup
_questions_cache: List[Dict] = []
_questions_by_widget_type: Dict[str, List[Dict]] = {}
_cache_loaded = False


def parse_scraped_question(doc):
    """Parse a scraped_questions document into standard format"""
    try:
        assessment_data = doc.get('assessmentData', {})
        if not isinstance(assessment_data, dict):
            return None

        data = assessment_data.get('data', {})
        if not isinstance(data, dict):
            return None

        assessment_item = data.get('assessmentItem', {})
        if not isinstance(assessment_item, dict):
            return None

        item = assessment_item.get('item', {})
        if not isinstance(item, dict):
            return None

        item_data_str = item.get('itemData', '')
        if not isinstance(item_data_str, str) or not item_data_str:
            return None

        item_data = json.loads(item_data_str)
        if not isinstance(item_data, dict):
            return None

        # Extract the question data
        question = item_data.get('question', {})
        hints = item_data.get('hints', [])
        answer_area = item_data.get('answerArea', {})

        # Get widget types for filtering
        widgets = question.get('widgets', {})
        widget_types = [w.get('type') for w in widgets.values() if isinstance(w, dict) and w.get('type')]

        return {
            '_id': str(doc.get('_id', '')),
            'question': question,
            'hints': hints,
            'answerArea': answer_area,
            'widgetTypes': widget_types,
            'courseName': doc.get('courseName', ''),
            'lessonName': doc.get('lessonName', ''),
        }
    except Exception as e:
        logger.debug(f"Failed to parse question: {e}")
        return None


def _load_cache():
    """Load and cache all questions at startup for fast filtering"""
    global _questions_cache, _questions_by_widget_type, _cache_loaded

    if _cache_loaded:
        return

    logger.info("Loading questions cache from MongoDB...")
    start_time = time.time()

    try:
        questions_cursor = mongo_db.scraped_questions.find({})

        for doc in questions_cursor:
            parsed = parse_scraped_question(doc)
            if parsed:
                _questions_cache.append(parsed)
                # Index by widget type for fast filtering
                for wt in parsed.get('widgetTypes', []):
                    if wt not in _questions_by_widget_type:
                        _questions_by_widget_type[wt] = []
                    _questions_by_widget_type[wt].append(parsed)

        elapsed = time.time() - start_time
        logger.info(f"Cache loaded: {len(_questions_cache)} questions in {elapsed:.2f}s")
        logger.info(f"Widget types indexed: {list(_questions_by_widget_type.keys())}")

        _cache_loaded = True
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")


def load_questions_from_mongodb(sample_size: int = 10, widget_types: list = None):
    """Load questions from cached data for fast response"""
    global _questions_cache, _questions_by_widget_type

    # Ensure cache is loaded
    if not _cache_loaded:
        _load_cache()

    try:
        # Get questions from appropriate source
        if widget_types and len(widget_types) > 0:
            # Get questions that have any of the requested widget types
            matching = []
            seen_ids = set()
            for wt in widget_types:
                for q in _questions_by_widget_type.get(wt, []):
                    if q['_id'] not in seen_ids:
                        matching.append(q)
                        seen_ids.add(q['_id'])
            parsed_questions = matching
        else:
            parsed_questions = _questions_cache

        if not parsed_questions:
            logger.warning(f"No questions found for widget types: {widget_types}")
            return []

        if sample_size <= len(parsed_questions):
            sample = random.sample(parsed_questions, sample_size)
            return sample
        else:
            logger.warning(f"Requested {sample_size} questions but only {len(parsed_questions)} available")
            return parsed_questions

    except Exception as e:
        logger.error(f"Failed to load questions: {e}")
        return []


def load_question_by_id(question_id: str):
    """Load a specific question by its _id"""
    global _questions_cache

    # Ensure cache is loaded
    if not _cache_loaded:
        _load_cache()

    # Try to find in cache first (fast)
    for q in _questions_cache:
        if q.get('_id') == question_id:
            return q

    # Fallback to MongoDB query if not in cache
    try:
        from bson import ObjectId

        doc = mongo_db.scraped_questions.find_one({"_id": question_id})

        if not doc:
            try:
                doc = mongo_db.scraped_questions.find_one({"_id": ObjectId(question_id)})
            except:
                pass

        if doc:
            return parse_scraped_question(doc)

        return None
    except Exception as e:
        logger.error(f"Failed to load question by id: {e}")
        return None


def load_questions(sample_size: int = 10, widget_types: list = None):
    """Loads the requested number of questions from MongoDB"""
    return load_questions_from_mongodb(sample_size, widget_types)