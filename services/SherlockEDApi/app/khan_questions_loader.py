# Load questions from MongoDB instead of local files
import os
import random
import sys

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

from shared.logging_config import get_logger

logger = get_logger(__name__)


def load_questions_from_mongodb(sample_size: int = 10):
    """Load questions from MongoDB perseus_questions collection"""
    try:
        # Get all questions from MongoDB
        questions_cursor = mongo_db.perseus_questions.find({}, {
            "question": 1,
            "answerArea": 1,
            "hints": 1
        })

        all_questions = list(questions_cursor)

        if not all_questions:
            logger.warning(" No questions found in MongoDB perseus_questions collection")
            return []

        if sample_size <= len(all_questions):
            sample = random.sample(all_questions, sample_size)
            return sample
        else:
            logger.warning(f" Requested {sample_size} questions but only {len(all_questions)} available")
            return all_questions

    except Exception as e:
        logger.error(f" Failed to load questions from MongoDB: {e}")
        return []

def load_questions(sample_size: int = 10):
    """Loads the requested number of questions from MongoDB"""
    return load_questions_from_mongodb(sample_size)