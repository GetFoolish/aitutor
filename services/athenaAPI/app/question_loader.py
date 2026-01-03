"""
Question Loader for Athena Renderer

Fetches questions from MongoDB and converts Perseus format to Athena format.
Handles image URL conversion and widget normalization.
"""

import os
import sys
import random
import re
from typing import List, Dict, Any, Optional
from bson import ObjectId

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def convert_graphie_url(url: str) -> str:
    """
    Convert Perseus graphie URLs to standard HTTPS URLs.

    Perseus format: web+graphie://cdn.kastatic.org/ka-perseus-graphie/{hash}
    Athena format: https://cdn.kastatic.org/ka-perseus-graphie/{hash}.svg
    """
    if not url:
        return url

    # Handle web+graphie:// protocol
    if url.startswith('web+graphie://'):
        # Remove protocol and add https
        clean_url = url.replace('web+graphie://', 'https://')

        # Add .svg extension if not present
        if not clean_url.endswith(('.svg', '.png', '.jpg', '.jpeg', '.gif')):
            clean_url += '.svg'

        return clean_url

    return url


def convert_widget_to_athena(widget_id: str, widget_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Perseus widget to Athena format.

    Normalizes widget types and options for the Athena renderer.
    """
    widget_type = widget_data.get('type', 'unknown')
    options = widget_data.get('options', {})

    # Normalize widget type aliases for internal logic processing
    type_aliases = {
        'input-number': 'numeric-input',
    }
    normalized_type = type_aliases.get(widget_type, widget_type)

    athena_widget = {
        'type': widget_type,  # Keep original type for Perseus compatibility
        'options': options.copy(),
        'alignment': widget_data.get('alignment', 'default'),
        'graded': widget_data.get('graded', True),
        'static': widget_data.get('static', False),
        'version': widget_data.get('version', {'major': 1, 'minor': 0}),
    }

    # Convert image URLs in options
    if 'backgroundImage' in athena_widget['options']:
        bg_image = athena_widget['options']['backgroundImage']
        if isinstance(bg_image, dict) and 'url' in bg_image:
            bg_image['url'] = convert_graphie_url(bg_image['url'])

    if 'imageUrl' in athena_widget['options']:
        athena_widget['options']['imageUrl'] = convert_graphie_url(athena_widget['options']['imageUrl'])

    # Handle specific widget type conversions
    if normalized_type == 'numeric-input':
        # Ensure answers are properly formatted
        answers = athena_widget['options'].get('answers', [])
        if answers:
            for answer in answers:
                if 'status' not in answer:
                    answer['status'] = 'correct'

    elif normalized_type == 'radio':
        # Ensure choices are properly formatted
        choices = athena_widget['options'].get('choices', [])
        for i, choice in enumerate(choices):
            if isinstance(choice, dict):
                if 'content' not in choice:
                    choice['content'] = choice.get('text', '')
                if 'correct' not in choice:
                    choice['correct'] = choice.get('isCorrect', False)

    elif normalized_type == 'image':
        # Ensure image has proper dimensions
        if 'box' not in athena_widget['options']:
            bg = athena_widget['options'].get('backgroundImage', {})
            athena_widget['options']['box'] = [
                bg.get('width', 400),
                bg.get('height', 300)
            ]

    return athena_widget


    return converted


def convert_content_images(content: str, images: Dict[str, Any]) -> str:
    """
    Convert image references in content to use HTTPS URLs.
    """
    if not content:
        return content

    # Find all image URLs in the content
    # Pattern matches: ![alt](url) and web+graphie:// URLs
    converted = content

    for url, img_data in images.items():
        if url.startswith('web+graphie://'):
            new_url = convert_graphie_url(url)
            converted = converted.replace(url, new_url)

    return converted


def deep_convert_urls(obj: Any) -> Any:
    """
    Recursively find and convert web+graphie:// URLs in a dictionary or list.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if k == 'url' and isinstance(v, str) and v.startswith('web+graphie://'):
                new_dict[k] = convert_graphie_url(v)
            else:
                new_dict[k] = deep_convert_urls(v)
        return new_dict
    elif isinstance(obj, list):
        return [deep_convert_urls(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith('web+graphie://'):
        return convert_graphie_url(obj)
    return obj


def convert_question_to_athena(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Perseus question document to Athena format.
    Handles both direct 'question' field and nested 'assessmentData' structures.
    """
    # Extract question data
    question_data = doc.get('question')
    hints = doc.get('hints')
    answer_area = doc.get('answerArea')

    # Fallback to nested structure if top-level fields are missing or empty
    if (not question_data or not isinstance(question_data, dict)) and 'assessmentData' in doc:
        try:
            # Handle deep nested structure from some scrapers
            item_data = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            
            # itemData can be a JSON string or a dict
            if isinstance(item_data, str) and item_data.startswith('{'):
                import json
                item_data = json.loads(item_data)
            
            if isinstance(item_data, dict):
                question_data = item_data.get('question', {})
                hints = item_data.get('hints', [])
                answer_area = item_data.get('answerArea', {})
        except Exception as e:
            logger.warning(f"Failed to extract nested question data: {e}")

    # Ensure we have valid dictionaries/lists
    if not isinstance(question_data, dict):
        question_data = {}
    if not isinstance(hints, list):
        hints = []
    if not isinstance(answer_area, dict):
        answer_area = {}

    # Convert widgets
    athena_widgets = {}
    for widget_id, widget_data in question_data.get('widgets', {}).items():
        if isinstance(widget_data, dict):
            athena_widgets[widget_id] = convert_widget_to_athena(widget_id, widget_data)

    # Convert content (update image URLs)
    content = question_data.get('content', '')
    images = question_data.get('images', {})
    if not isinstance(images, dict):
        images = {}
    converted_content = convert_content_images(content, images)

    # Convert images dict to Athena format
    def convert_images_dict(img_dict):
        athena_imgs = {}
        if not isinstance(img_dict, dict):
            return athena_imgs
        for url, img_data in img_dict.items():
            if not isinstance(img_data, dict): continue
            new_url = convert_graphie_url(url)
            athena_imgs[new_url] = {
                'url': new_url,
                'width': img_data.get('width', 400),
                'height': img_data.get('height', 300),
                'alt': img_data.get('alt', ''),
            }
        return athena_imgs

    athena_images = convert_images_dict(images)

    # Convert hints
    athena_hints = []
    for hint in hints:
        if not isinstance(hint, dict): continue
        
        hint_widgets = {}
        for widget_id, widget_data in hint.get('widgets', {}).items():
            if isinstance(widget_data, dict):
                hint_widgets[widget_id] = convert_widget_to_athena(widget_id, widget_data)

        hint_content = hint.get('content', '')
        hint_images = hint.get('images', {})
        if not isinstance(hint_images, dict):
            hint_images = {}

        athena_hints.append({
            'content': convert_content_images(hint_content, hint_images),
            'widgets': hint_widgets,
            'images': convert_images_dict(hint_images),
            'replace': hint.get('replace', False),
        })

    # Build answer area
    athena_answer_area = {
        'calculator': bool(answer_area.get('calculator', False)),
        'periodicTable': bool(answer_area.get('periodicTable', False)),
        'chi2Table': bool(answer_area.get('chi2Table', False)),
        'tTable': bool(answer_area.get('tTable', False)),
        'zTable': bool(answer_area.get('zTable', False)),
        'financialCalculator': bool(
            answer_area.get('financialCalculatorMonthlyPayment', False) or
            answer_area.get('financialCalculatorTimeToPayOff', False) or
            answer_area.get('financialCalculatorTotalAmount', False)
        ),
    }

    # Build Athena item
    skill_prefix = doc.get('skill_prefix') or doc.get('skill_id') or ''

    # Get all widget types for filtering
    widget_types_in_item = list(set(w['type'] for w in athena_widgets.values()))

    # Build raw Perseus item (unmodified fields but with converted URLs for compatibility)
    # We use deep_convert_urls to ensure everything is web-ready
    perseus_item = deep_convert_urls({
        'question': question_data,
        'hints': hints,
        'answerArea': answer_area,
        'itemDataVersion': doc.get('itemDataVersion', {'major': 2, 'minor': 0})
    })

    # Ensure it's not a Pydantic object if coming from anywhere else
    if hasattr(perseus_item, 'dict'):
        perseus_item = perseus_item.dict()

    athena_item = {
        '_id': str(doc.get('_id', '')),
        'slug': doc.get('slug', ''),
        'skill_prefix': skill_prefix,
        'question': {
            'content': converted_content,
            'widgets': athena_widgets,
            'images': athena_images,
        },
        'hints': athena_hints,
        'answerArea': athena_answer_area,
        'itemDataVersion': doc.get('itemDataVersion', {'major': 2, 'minor': 0}),
        'widgetTypes': widget_types_in_item,
        'perseusItem': perseus_item
    }

    return athena_item







# ==========================================
# MOCK DATA (Fallback for missing widgets)
# ==========================================
MOCK_QUESTIONS = {
    "kitchen-sink-demo": {
        "_id": "kitchen-sink-demo",
        "slug": "kitchen-sink-demo",
        "skill_prefix": "audit",
        "question": {
            "content": "# Specialized Widget Demo\n\n**Chemistry:**\n[[☃ molecule 1]]\n\n**Music:**\n[[☃ music 1]]\n\n**CS Code:**\n[[☃ cs-program 1]]",
            "widgets": {
                "molecule 1": {"type": "molecule", "options": {"smiles": "CCO", "showTabs": True}},
                "music 1": {"type": "music-notation", "options": {"clef": "treble", "notes": ["C4", "E4", "G4"]}},
                "cs-program 1": {"type": "cs-program", "options": {"code": "print('Hello World')", "language": "python"}}
            },
            "images": {}
        },
        "hints": [],
        "answerArea": {"calculator": False},
        "itemDataVersion": {"major": 2, "minor": 0},
        "widgetTypes": ["molecule", "music-notation", "cs-program"]
    }
}

def get_question_by_id(question_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single question by its MongoDB ObjectId.
    Includes MOCK DATA fallback for specialized demos.
    """
    try:
        # CHECK MOCK DATA
        if question_id in MOCK_QUESTIONS:
             logger.info(f"Serving MOCK question for ID: {question_id}")
             return MOCK_QUESTIONS[question_id]

        if not ObjectId.is_valid(question_id):
            logger.warning(f"Invalid ObjectId format: {question_id}")
            return None

        doc = mongo_db.scraped_questions.find_one({'_id': ObjectId(question_id)})

        if not doc:
            logger.warning(f"Question not found: {question_id}")
            return None

        return convert_question_to_athena(doc)

    except Exception as e:
        logger.error(f"Error fetching question {question_id}: {e}")
        # Fallback to mock if DB fails
        if question_id in MOCK_QUESTIONS:
             return MOCK_QUESTIONS[question_id]
        return None


def get_questions(
    sample_size: int = 10,
    widget_types: Optional[List[str]] = None,
    skill_prefix: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple questions from MongoDB with strict widget type filtering.
    """
    try:
        pipeline = []

        # 1. Match stage for skill_prefix
        if skill_prefix:
            pipeline.append({'$match': {'skill_prefix': {'$regex': f'^{skill_prefix}', '$options': 'i'}}})

        # 2. Match stage for widget types (if provided)
        if widget_types:
            expanded_types = set()
            for wt in widget_types:
                expanded_types.add(wt)
                if wt == 'numeric-input': expanded_types.add('input-number')
                elif wt == 'input-number': expanded_types.add('numeric-input')
            
            # Robust match that checks multiple possible paths for widgets
            pipeline.append({
                '$match': {
                    '$or': [
                        # Top-level 'question.widgets'
                        {'question.widgets': {'$exists': True, '$ne': {}}},
                        # Nested 'assessmentData' variants
                        {'assessmentData.data.assessmentItem.item.itemData': {'$exists': True}},
                    ]
                }
            })

        # 3. Random sample (fetch more to allow filtering)
        fetch_limit = sample_size * 5 if widget_types else sample_size
        pipeline.append({'$sample': {'size': min(fetch_limit, 100)}})

        # Execute aggregation
        cursor = mongo_db.scraped_questions.aggregate(pipeline)

        athena_questions = []
        for doc in cursor:
            athena_item = convert_question_to_athena(doc)
            
            # Post-processing filter (STRICT)
            if widget_types:
                item_widget_types = athena_item.get('widgetTypes', [])
                
                # Expand requested types for comparison
                requested_types = set(widget_types)
                if 'numeric-input' in requested_types: requested_types.add('input-number')
                if 'input-number' in requested_types: requested_types.add('numeric-input')

                # Define interactive vs display types
                interactive_types = {
                    'radio', 'dropdown', 'numeric-input', 'input-number', 'expression',
                    'sorter', 'orderer', 'matcher', 'categorizer', 'interactive-graph',
                    'grapher', 'plotter', 'table', 'matrix', 'label-image', 'free-response'
                }

                # Find interactive widgets in this question
                question_interactive = set(item_widget_types) & interactive_types
                
                # Check if this question is primarily of the requested interactive types
                requested_interactive = requested_types & interactive_types
                
                if requested_interactive:
                    # If we asked for an interactive type, the question must have it
                    # and MUST NOT have other interactive types (no radio + numeric-input mix)
                    if not (question_interactive & requested_types):
                        continue
                    
                    # If it has other conflicting interactive types, skip
                    if question_interactive - requested_types:
                        continue
                else:
                    # If we asked for display type (e.g. passage), just check presence
                    if not (set(item_widget_types) & requested_types):
                        continue

            athena_questions.append(athena_item)
            if len(athena_questions) >= sample_size:
                break

        logger.info(f"Fetched {len(athena_questions)} questions (filter: {widget_types})")
        return athena_questions

    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        return []


def get_questions_by_ids(question_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch multiple questions by their MongoDB ObjectIds.

    Args:
        question_ids: List of MongoDB ObjectIds as strings

    Returns:
        List of Athena-formatted questions
    """
    try:
        # Convert to ObjectIds
        object_ids = []
        for qid in question_ids:
            if ObjectId.is_valid(qid):
                object_ids.append(ObjectId(qid))
            else:
                logger.warning(f"Invalid ObjectId: {qid}")

        if not object_ids:
            return []

        cursor = mongo_db.scraped_questions.find({'_id': {'$in': object_ids}})

        athena_questions = []
        for doc in cursor:
            athena_item = convert_question_to_athena(doc)
            athena_questions.append(athena_item)

        return athena_questions

    except Exception as e:
        logger.error(f"Error fetching questions by IDs: {e}")
        return []


def get_widget_types_summary() -> Dict[str, int]:
    """
    Get a summary of widget types in the database.

    Returns:
        Dictionary mapping widget type to count
    """
    try:
        pipeline = [
            {'$project': {'widgets': {'$objectToArray': '$question.widgets'}}},
            {'$unwind': '$widgets'},
            {'$group': {'_id': '$widgets.v.type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]

        result = mongo_db.scraped_questions.aggregate(pipeline)

        return {doc['_id']: doc['count'] for doc in result}

    except Exception as e:
        logger.error(f"Error getting widget types: {e}")
        return {}


def search_questions(
    search_text: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search questions by content text.

    Args:
        search_text: Text to search for
        limit: Maximum results to return

    Returns:
        List of Athena-formatted questions
    """
    try:
        query = {
            '$or': [
                {'question.content': {'$regex': search_text, '$options': 'i'}},
                {'slug': {'$regex': search_text, '$options': 'i'}},
            ]
        }

        cursor = mongo_db.scraped_questions.find(query).limit(limit)

        athena_questions = []
        for doc in cursor:
            athena_item = convert_question_to_athena(doc)
            athena_questions.append(athena_item)

        return athena_questions

    except Exception as e:
        logger.error(f"Error searching questions: {e}")
        return []
