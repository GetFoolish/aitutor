"""
Create MongoDB indexes for cost tracking collections
Run this once during deployment to ensure optimal query performance
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def create_indexes():
    """Create required indexes for cost tracking"""

    # session_costs collection indexes
    logger.info("Creating indexes for session_costs collection...")

    # 1. Unique index on session_id (each session has one cost record)
    mongo_db.session_costs.create_index(
        "session_id",
        unique=True,
        name="idx_session_costs_session_id"
    )
    logger.info("✓ Created unique index on session_id")

    # 2. Index on user_id for fetching user's cost history
    mongo_db.session_costs.create_index(
        "user_id",
        name="idx_session_costs_user_id"
    )
    logger.info("✓ Created index on user_id")

    # 3. Compound index for admin analytics (user_id + started_at)
    mongo_db.session_costs.create_index(
        [("user_id", 1), ("started_at", -1)],
        name="idx_session_costs_user_started"
    )
    logger.info("✓ Created compound index on user_id + started_at")

    # 4. Index on status for querying active sessions
    mongo_db.session_costs.create_index(
        "status",
        name="idx_session_costs_status"
    )
    logger.info("✓ Created index on status")

    # 5. Index on started_at for time-based queries
    mongo_db.session_costs.create_index(
        "started_at",
        name="idx_session_costs_started_at"
    )
    logger.info("✓ Created index on started_at")

    logger.info("All indexes created successfully for session_costs")


if __name__ == "__main__":
    create_indexes()
