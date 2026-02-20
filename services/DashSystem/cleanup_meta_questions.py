#!/usr/bin/env python3
"""
Cleanup script to remove meta-questions from the database.

Meta-questions are generic "Which of the following is true about X?" questions
that the validator is supposed to reject but may have slipped through.
"""

import re
import sys
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Add parent directory to path to import from managers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Meta-question patterns (from pre_serve_validator.py)
META_PATTERNS = [
    re.compile(r"which\s+(?:of\s+the\s+following\s+)?(?:is|are)\s+true\s+(?:about|regarding|concerning)\s+", re.IGNORECASE),
    re.compile(r"which\s+statement\s+(?:is|are)\s+(?:correct|true)\s+about\s+", re.IGNORECASE),
    re.compile(r"what\s+(?:is|are)\s+(?:some\s+)?(?:characteristic|feature|propert)(?:s|ies)\s+of\s+", re.IGNORECASE),
    re.compile(r"which\s+(?:best\s+)?describ(?:e|es)\s+", re.IGNORECASE),
    re.compile(r"select\s+(?:all|the)\s+(?:statement|option)s?\s+that\s+(?:are\s+)?(?:true|correct)\s+(?:about|for)\s+", re.IGNORECASE),
]


def is_meta_question(content: str) -> bool:
    """Check if question content matches meta-question patterns."""
    if not content:
        return False
    for pattern in META_PATTERNS:
        if pattern.search(content):
            return True
    return False


def cleanup_meta_questions(dry_run: bool = True):
    """Remove meta-questions from all question collections."""

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)

    # Collections that store questions
    collections = [
        (client.ai_tutor.ai_generated_questions, "ai_generated_questions"),
        (client.ai_tutor.ai_question_queue, "ai_question_queue"),
        (client.ai_tutor.content_pool, "content_pool"),
    ]

    total_found = 0
    total_removed = 0

    print("=" * 80)
    print("META-QUESTION CLEANUP SCRIPT")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no deletions)' if dry_run else 'LIVE (will delete)'}")
    print()

    for collection, name in collections:
        print(f"Scanning {name}...")
        found = 0
        removed = 0

        # Find all documents with Perseus questions
        cursor = collection.find({})
        batch_to_remove = []

        for doc in cursor:
            # Extract question content from Perseus format
            item = doc.get("item", {})
            question = item.get("question", {})
            content = question.get("content", "")

            if is_meta_question(content):
                found += 1
                question_id = doc.get("question_id", doc.get("_id", "unknown"))
                skill_id = doc.get("skill_id", "unknown")

                print(f"  [META] {question_id[:30]}... | Skill: {skill_id[:30]}...")
                print(f"         \"{content[:80]}...\"")

                batch_to_remove.append(doc["_id"])

        # Remove in batch
        if batch_to_remove and not dry_run:
            result = collection.delete_many({"_id": {"$in": batch_to_remove}})
            removed = result.deleted_count
        else:
            removed = len(batch_to_remove)

        print(f"  Found: {found}, {'Would remove' if dry_run else 'Removed'}: {removed}")
        print()

        total_found += found
        total_removed += removed

    print("=" * 80)
    print(f"TOTAL: {total_found} meta-questions found")
    if dry_run:
        print(f"Would remove {total_removed} questions (re-run with --live to delete)")
    else:
        print(f"Removed {total_removed} questions")
    print("=" * 80)

    client.close()
    return total_removed


if __name__ == "__main__":
    dry_run = "--live" not in sys.argv

    if not dry_run:
        print("\n⚠️  WARNING: Running in LIVE mode - will delete meta-questions!")
        response = input("Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("Aborted.")
            sys.exit(0)

    cleanup_meta_questions(dry_run=dry_run)
