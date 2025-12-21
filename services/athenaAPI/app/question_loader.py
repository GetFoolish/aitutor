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

    # Normalize widget type aliases
    type_aliases = {
        'input-number': 'numeric-input',
    }
    normalized_type = type_aliases.get(widget_type, widget_type)

    athena_widget = {
        'type': normalized_type,
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


def convert_question_to_athena(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Perseus question document to Athena format.

    Input: MongoDB document with Perseus format
    Output: Athena-compatible question format
    """
    # Extract question data
    question_data = doc.get('question')
    hints = doc.get('hints')
    answer_area = doc.get('answerArea')

    # Fallback to nested structure if top-level fields are missing
    if not question_data and 'assessmentData' in doc:
        try:
            item_data_str = doc.get('assessmentData', {}).get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if item_data_str:
                import json
                item_data = json.loads(item_data_str)
                question_data = item_data.get('question', {})
                hints = item_data.get('hints', [])
                answer_area = item_data.get('answerArea', {})
        except Exception as e:
            logger.warning(f"Failed to extract nested question data: {e}")

    if not question_data:
        question_data = {}
    if not hints:
        hints = []
    if not answer_area:
        answer_area = {}

    # Convert widgets
    athena_widgets = {}
    for widget_id, widget_data in question_data.get('widgets', {}).items():
        athena_widgets[widget_id] = convert_widget_to_athena(widget_id, widget_data)

    # Convert content (update image URLs)
    content = question_data.get('content', '')
    images = question_data.get('images', {})
    converted_content = convert_content_images(content, images)

    # Convert images dict
    athena_images = {}
    for url, img_data in images.items():
        new_url = convert_graphie_url(url)
        athena_images[new_url] = {
            'url': new_url,
            'width': img_data.get('width', 400),
            'height': img_data.get('height', 300),
            'alt': img_data.get('alt', ''),
        }

    # Convert hints
    athena_hints = []
    for hint in hints:
        hint_widgets = {}
        for widget_id, widget_data in hint.get('widgets', {}).items():
            hint_widgets[widget_id] = convert_widget_to_athena(widget_id, widget_data)

        hint_content = hint.get('content', '')
        hint_images = hint.get('images', {})

        athena_hints.append({
            'content': convert_content_images(hint_content, hint_images),
            'widgets': hint_widgets,
            'images': hint_images,
            'replace': hint.get('replace', False),
        })

    # Build answer area
    athena_answer_area = {
        'calculator': answer_area.get('calculator', False),
        'periodicTable': answer_area.get('periodicTable', False),
        'chi2Table': answer_area.get('chi2Table', False),
        'tTable': answer_area.get('tTable', False),
        'zTable': answer_area.get('zTable', False),
        'financialCalculator': (
            answer_area.get('financialCalculatorMonthlyPayment', False) or
            answer_area.get('financialCalculatorTimeToPayOff', False) or
            answer_area.get('financialCalculatorTotalAmount', False)
        ),
    }

    # Build Athena item
    skill_prefix = doc.get('skill_prefix') or doc.get('skill_id') or ''

    athena_item = {
        '_id': str(doc.get('_id', '')),
        'slug': doc.get('slug', ''),
        'skill_prefix': skill_prefix,

        # Question data
        'question': {
            'content': converted_content,
            'widgets': athena_widgets,
            'images': athena_images,
        },

        # Hints
        'hints': athena_hints,

        # Answer area with tool toggles
        'answerArea': athena_answer_area,

        # Metadata
        'itemDataVersion': doc.get('itemDataVersion', {'major': 2, 'minor': 0}),

        # Widget type summary (for debugging/filtering)
        'widgetTypes': list(set(w['type'] for w in athena_widgets.values())),
    }

    return athena_item


def get_question_by_id(question_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single question by its MongoDB ObjectId.

    Args:
        question_id: MongoDB ObjectId as string

    Returns:
        Athena-formatted question or None if not found
    """
    try:
        # Validate ObjectId format
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
        return None


def get_questions(
    sample_size: int = 10,
    widget_types: Optional[List[str]] = None,
    skill_prefix: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple questions from MongoDB.

    Args:
        sample_size: Number of questions to fetch
        widget_types: Filter by widget types (optional)
        skill_prefix: Filter by skill prefix (optional)

    Returns:
        List of Athena-formatted questions
    """
    try:
        # Build aggregation pipeline
        pipeline = []

        # Initial match stage for skill_prefix
        match_stage = {}
        if skill_prefix:
            match_stage['skill_prefix'] = {'$regex': f'^{skill_prefix}', '$options': 'i'}

        if match_stage:
            pipeline.append({'$match': match_stage})

        if widget_types:
            # Expand widget type aliases
            expanded_types = set()
            for wt in widget_types:
                expanded_types.add(wt)
                # Add aliases
                if wt == 'numeric-input':
                    expanded_types.add('input-number')
                elif wt == 'input-number':
                    expanded_types.add('numeric-input')

            expanded_types = list(expanded_types)

            # Use aggregation to filter by widget type
            # Convert widgets object to array, then filter
            pipeline.extend([
                # Add a field with widgets as array
                {'$addFields': {
                    'widgetsArray': {'$objectToArray': '$question.widgets'}
                }},
                # Filter to only include questions where at least one widget matches
                {'$match': {
                    'widgetsArray.v.type': {'$in': expanded_types}
                }},
                # Remove the temporary field
                {'$project': {
                    'widgetsArray': 0
                }}
            ])

        # Add random sampling
        pipeline.append({'$sample': {'size': sample_size * 3}})  # Fetch more for better variety

        # Execute pipeline
        cursor = mongo_db.scraped_questions.aggregate(pipeline)

        # Convert to Athena format and filter
        athena_questions = []
        for doc in cursor:
            athena_item = convert_question_to_athena(doc)

            # Strict widget type filter (post-processing)
            # Only include questions where the PRIMARY INTERACTIVE widget matches
            if widget_types:
                item_widget_types = athena_item.get('widgetTypes', [])

                # Build expanded type set including aliases
                expanded_types_set = set()
                for wt in widget_types:
                    expanded_types_set.add(wt)
                    if wt == 'numeric-input':
                        expanded_types_set.add('input-number')
                    elif wt == 'input-number':
                        expanded_types_set.add('numeric-input')

                if len(item_widget_types) == 0:
                    continue  # No widgets, skip

                # Define interactive widget types (widgets that users interact with for answers)
                # These are mutually exclusive - a question shouldn't have both radio AND numeric-input
                interactive_types = {
                    'radio', 'dropdown', 'numeric-input', 'input-number', 'expression',
                    'sorter', 'orderer', 'matcher', 'categorizer', 'interactive-graph',
                    'grapher', 'plotter', 'table', 'matrix', 'label-image', 'free-response'
                }

                # Display-only widget types (these don't affect filtering)
                display_types = {'image', 'passage', 'passage-ref', 'video', 'explanation', 'definition'}

                # Find the interactive widgets in this question
                interactive_widgets_in_question = set(item_widget_types) & interactive_types

                # Check if ANY of the requested types match the interactive widgets
                requested_interactive = expanded_types_set & interactive_types

                if requested_interactive:
                    # User is filtering for an interactive widget type
                    # The question MUST have that type and NOT have other conflicting interactive types
                    if not (interactive_widgets_in_question & expanded_types_set):
                        continue  # Skip - doesn't have the requested interactive widget type

                    # Check for conflicting interactive types (e.g., filtering for numeric-input but has radio)
                    conflicting_types = interactive_widgets_in_question - expanded_types_set
                    if conflicting_types:
                        continue  # Skip - has conflicting interactive widget types
                else:
                    # User is filtering for a display-only type (e.g., image, passage)
                    if not (set(item_widget_types) & expanded_types_set):
                        continue  # Skip - doesn't have the requested type

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
