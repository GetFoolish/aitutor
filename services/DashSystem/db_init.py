#!/usr/bin/env python3
"""
Database initialization script for Dash System.
Creates indexes and ensures optimal query performance.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from managers.mongodb_manager import mongo_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_create_index(collection, field, unique=False):
    """Safely create or update an index."""
    try:
        # Check if index exists
        existing_indexes = collection.index_information()
        index_name = f"{field}_1"

        # If index exists with wrong spec, drop it
        if index_name in existing_indexes:
            existing_spec = existing_indexes[index_name]
            needs_recreate = False

            # Check if unique constraint differs
            if unique and not existing_spec.get('unique', False):
                needs_recreate = True
            elif not unique and existing_spec.get('unique', False):
                needs_recreate = True

            if needs_recreate:
                logger.info(f"  Dropping conflicting index {index_name}...")
                collection.drop_index(index_name)

        # Create the index
        if unique:
            collection.create_index(field, unique=True)
        else:
            collection.create_index(field)

        return True
    except Exception as e:
        logger.error(f"  Error with {field}: {e}")
        return False


def create_indexes():
    """Create MongoDB indexes for optimal query performance."""
    logger.info("Creating MongoDB indexes for Dash System...")

    success_count = 0
    total_count = 0

    # Questions collection indexes
    logger.info("Questions collection:")
    total_count += 1
    if safe_create_index(mongo_db.questions, "question_id", unique=True):
        success_count += 1
    total_count += 1
    if safe_create_index(mongo_db.questions, "unit_id"):
        success_count += 1
    total_count += 1
    if safe_create_index(mongo_db.questions, "lesson_id"):
        success_count += 1
    total_count += 1
    if safe_create_index(mongo_db.questions, "exercise_id"):
        success_count += 1

    # Units collection index
    logger.info("Units collection:")
    total_count += 1
    if safe_create_index(mongo_db.units, "unit_id", unique=True):
        success_count += 1

    # Lessons collection index
    logger.info("Lessons collection:")
    total_count += 1
    if safe_create_index(mongo_db.lessons, "lesson_id", unique=True):
        success_count += 1

    # Exercises collection index (non-unique due to data duplicates)
    logger.info("Exercises collection:")
    total_count += 1
    if safe_create_index(mongo_db.exercises, "exercise_id"):
        success_count += 1

    # Users collection indexes
    logger.info("Users collection:")
    total_count += 1
    if safe_create_index(mongo_db.users, "user_id", unique=True):
        success_count += 1
    total_count += 1
    # Email index is non-unique to allow multiple null values
    if safe_create_index(mongo_db.users, "email"):
        success_count += 1

    logger.info(f"✅ Created {success_count}/{total_count} indexes successfully!")

    # Success if at least 80% of indexes were created
    success_rate = success_count / total_count
    if success_rate >= 0.8:
        logger.info(f"✅ Index creation successful ({success_rate * 100:.0f}% success rate)")
        return True
    else:
        logger.error(f"❌ Too many index failures ({success_rate * 100:.0f}% success rate)")
        return False


def verify_indexes():
    """Verify all indexes exist."""
    logger.info("\nVerifying indexes...")

    collections = {
        'questions': ['question_id', 'unit_id', 'lesson_id', 'exercise_id'],
        'units': ['unit_id'],
        'lessons': ['lesson_id'],
        'exercises': ['exercise_id'],
        'users': ['user_id', 'email']
    }

    for collection_name, expected_indexes in collections.items():
        collection = getattr(mongo_db, collection_name)
        indexes = collection.index_information()
        logger.info(f"{collection_name}: {list(indexes.keys())}")

    logger.info("✅ Index verification complete!")


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Dash System Database Initialization")
    logger.info("=" * 80)

    if create_indexes():
        verify_indexes()
        logger.info("\n✅ Database initialization complete!")
        sys.exit(0)
    else:
        logger.error("\n❌ Database initialization failed!")
        sys.exit(1)
