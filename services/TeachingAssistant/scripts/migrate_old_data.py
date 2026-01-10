"""
Migration Script: Old TA JSON files -> New MongoDB + Biography structure
Based on the Cognitive Memory Pipeline architecture

This script:
1. Reads old TA JSON files (conversations, academic/personal memories)
2. Generates initial biographies using LLM synthesis
3. Creates MongoDB documents with full student profiles
4. Seeds Pinecone with historical memory embeddings

Usage:
    python migrate_old_data.py --old-data-path "services/TeachingAssistant_old/Memory/data"
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely load a JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load {file_path}: {e}")
        return None


def find_student_data_dirs(old_data_path: Path) -> List[Path]:
    """Find all student data directories in old TA structure"""
    if not old_data_path.exists():
        logger.error(f"Old data path does not exist: {old_data_path}")
        return []

    # Look for directories that might contain student data
    student_dirs = []
    for item in old_data_path.iterdir():
        if item.is_dir():
            # Check if it looks like a student directory
            if (item / "memory").exists() or (item / "conversations").exists():
                student_dirs.append(item)

    return student_dirs


def load_old_student_data(student_dir: Path) -> Dict[str, Any]:
    """
    Load all data for a student from old TA structure.

    Expected structure:
    student_dir/
        memory/
            academic.json
            personal.json
            context.json
        conversations/
            *.json
    """
    data = {
        "student_id": student_dir.name,
        "conversations": [],
        "academic_memories": [],
        "personal_memories": [],
        "context_memories": [],
    }

    # Load memory files
    memory_dir = student_dir / "memory"
    if memory_dir.exists():
        academic = load_json_file(memory_dir / "academic.json")
        if academic:
            data["academic_memories"] = academic.get("memories", academic if isinstance(academic, list) else [])

        personal = load_json_file(memory_dir / "personal.json")
        if personal:
            data["personal_memories"] = personal.get("memories", personal if isinstance(personal, list) else [])

        context = load_json_file(memory_dir / "context.json")
        if context:
            data["context_memories"] = context.get("memories", context if isinstance(context, list) else [])

    # Load conversations
    conv_dir = student_dir / "conversations"
    if conv_dir.exists():
        for conv_file in conv_dir.glob("*.json"):
            conv = load_json_file(conv_file)
            if conv:
                data["conversations"].append(conv)

    return data


def extract_name_from_data(student_data: Dict[str, Any]) -> str:
    """Try to extract student name from data"""
    # Check personal memories for name mentions
    for memory in student_data.get("personal_memories", []):
        text = memory if isinstance(memory, str) else memory.get("text", "")
        if "name is" in text.lower():
            # Simple extraction
            parts = text.lower().split("name is")
            if len(parts) > 1:
                name = parts[1].strip().split()[0].capitalize()
                return name

    return f"Student_{student_data['student_id'][:8]}"


def generate_initial_biography(
    name: str,
    student_data: Dict[str, Any],
    biographer
) -> str:
    """
    Generate initial biography from historical data.

    Uses the Biographer Agent if available, otherwise creates a basic biography.
    """
    if biographer and biographer.enabled:
        biography = biographer.generate_from_history(
            name=name,
            conversations=student_data.get("conversations", []),
            academic_memories=[
                m if isinstance(m, str) else m.get("text", "")
                for m in student_data.get("academic_memories", [])[:20]
            ],
            personal_memories=[
                m if isinstance(m, str) else m.get("text", "")
                for m in student_data.get("personal_memories", [])[:20]
            ]
        )
        if biography:
            return biography

    # Fallback: Create basic biography
    academic = student_data.get("academic_memories", [])
    personal = student_data.get("personal_memories", [])
    num_convs = len(student_data.get("conversations", []))

    return f"""PSYCHOLOGICAL PROFILE:
{name} is a student who has completed {num_convs} tutoring sessions. Based on their history, they have shown interest in learning and growth. Their personal memories include: {', '.join([str(m)[:50] for m in personal[:3]]) if personal else 'No personal information recorded yet.'}

ACADEMIC JOURNEY:
{name} has been working through various math topics. Key academic notes: {', '.join([str(m)[:50] for m in academic[:3]]) if academic else 'No specific academic progress recorded.'} They are continuing their learning journey on this platform."""


def extract_onboarding_data(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract onboarding-like data from historical memories"""
    onboarding = {
        "core_values": [],
        "north_star_goals": [],
        "personality_traits": [],
        "blind_spots": [],
        "emotional_baseline": "neutral",
        "interests": [],
        "created_at": datetime.utcnow(),
    }

    # Extract interests from personal memories
    for memory in student_data.get("personal_memories", []):
        text = memory if isinstance(memory, str) else memory.get("text", "")
        text_lower = text.lower()

        # Look for interest indicators
        interest_keywords = ["like", "love", "enjoy", "interested in", "favorite"]
        for keyword in interest_keywords:
            if keyword in text_lower:
                # Simple extraction - take the memory as an interest
                if len(text) < 100:
                    onboarding["interests"].append(text)
                break

    return onboarding


def calculate_statistics(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics from historical data"""
    conversations = student_data.get("conversations", [])

    total_questions = 0
    total_correct = 0
    total_duration = 0.0

    for conv in conversations:
        if isinstance(conv, dict):
            total_questions += conv.get("questions_answered", 0)
            total_correct += conv.get("questions_correct", 0)
            total_duration += conv.get("duration_minutes", 0)

    return {
        "total_sessions": len(conversations),
        "total_questions_answered": total_questions,
        "total_questions_correct": total_correct,
        "average_session_duration_minutes": round(total_duration / len(conversations), 2) if conversations else 0,
        "last_session_date": datetime.utcnow(),
    }


def create_student_document(
    student_data: Dict[str, Any],
    name: str,
    biography: str
) -> Dict[str, Any]:
    """Create the full student document for MongoDB"""
    now = datetime.utcnow()

    return {
        "_id": student_data["student_id"],
        "name": name,
        "email": None,
        "onboarding_data": extract_onboarding_data(student_data),
        "biography": {
            "text": biography,
            "version": 1,
            "last_updated": now,
            "session_count": len(student_data.get("conversations", [])),
        },
        "biography_history": [
            {
                "version": 1,
                "text": biography,
                "created_at": now,
                "session_count": len(student_data.get("conversations", [])),
            }
        ],
        "academic_journey": {
            "current_topic": "",
            "mastered_topics": [],
            "struggling_topics": [],
            "milestones": [],
        },
        "statistics": calculate_statistics(student_data),
        "created_at": now,
        "updated_at": now,
        "migrated_from_old_ta": True,
        "migration_date": now,
    }


def create_memory_documents(
    student_id: str,
    student_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Create memory documents from old data"""
    import uuid
    memories = []
    now = datetime.utcnow()

    # Process academic memories
    for memory in student_data.get("academic_memories", []):
        text = memory if isinstance(memory, str) else memory.get("text", "")
        if text:
            memories.append({
                "_id": f"mem_{uuid.uuid4().hex[:12]}",
                "student_id": student_id,
                "session_id": "migrated",
                "type": "academic",
                "text": text,
                "importance": 0.6,
                "timestamp": now,
                "metadata": {
                    "migrated": True,
                    "confidence": 0.7,
                },
            })

    # Process personal memories
    for memory in student_data.get("personal_memories", []):
        text = memory if isinstance(memory, str) else memory.get("text", "")
        if text:
            memories.append({
                "_id": f"mem_{uuid.uuid4().hex[:12]}",
                "student_id": student_id,
                "session_id": "migrated",
                "type": "personal",
                "text": text,
                "importance": 0.5,
                "timestamp": now,
                "metadata": {
                    "migrated": True,
                    "confidence": 0.7,
                },
            })

    return memories


def migrate_student(
    student_data: Dict[str, Any],
    mongo_db,
    pinecone_client,
    biographer,
    dry_run: bool = False
) -> bool:
    """
    Migrate a single student to the new system.

    Args:
        student_data: Data loaded from old TA
        mongo_db: MongoDB database instance
        pinecone_client: Pinecone client for memory embeddings
        biographer: Biographer agent for biography generation
        dry_run: If True, don't actually write to databases

    Returns:
        True if successful
    """
    student_id = student_data["student_id"]
    logger.info(f"Migrating student: {student_id}")

    try:
        # Extract name
        name = extract_name_from_data(student_data)
        logger.info(f"  Name: {name}")

        # Generate biography
        biography = generate_initial_biography(name, student_data, biographer)
        logger.info(f"  Biography generated ({len(biography)} chars)")

        # Create student document
        student_doc = create_student_document(student_data, name, biography)

        # Create memory documents
        memory_docs = create_memory_documents(student_id, student_data)
        logger.info(f"  Memories to migrate: {len(memory_docs)}")

        if dry_run:
            logger.info(f"  [DRY RUN] Would insert student doc and {len(memory_docs)} memories")
            return True

        # Insert to MongoDB
        existing = mongo_db.students.find_one({"_id": student_id})
        if existing:
            logger.warning(f"  Student {student_id} already exists, skipping")
            return False

        mongo_db.students.insert_one(student_doc)
        logger.info(f"  Inserted student document")

        if memory_docs:
            mongo_db.memories.insert_many(memory_docs)
            logger.info(f"  Inserted {len(memory_docs)} memories")

        # Upsert to Pinecone
        if pinecone_client and pinecone_client.enabled and memory_docs:
            pinecone_memories = [
                {
                    "id": m["_id"],
                    "student_id": m["student_id"],
                    "text": m["text"],
                    "memory_type": m["type"],
                    "importance": m["importance"],
                    "timestamp": m["timestamp"].isoformat(),
                }
                for m in memory_docs
            ]
            count = pinecone_client.upsert_memories_batch(pinecone_memories)
            logger.info(f"  Upserted {count} memories to Pinecone")

        logger.info(f"  ✅ Migration complete for {student_id}")
        return True

    except Exception as e:
        logger.error(f"  ❌ Migration failed for {student_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate old TA data to new Cognitive Memory Pipeline"
    )
    parser.add_argument(
        "--old-data-path",
        type=str,
        required=True,
        help="Path to old TA data directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually write to databases"
    )
    parser.add_argument(
        "--student-id",
        type=str,
        help="Migrate only this specific student"
    )

    args = parser.parse_args()

    old_data_path = Path(args.old_data_path)

    logger.info("=" * 60)
    logger.info("TeachingAssistant v5 Migration Script")
    logger.info("=" * 60)
    logger.info(f"Old data path: {old_data_path}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")

    # Initialize services
    mongo_db = None
    pinecone_client = None
    biographer = None

    try:
        from managers.mongodb_manager import MongoDBManager
        mongo = MongoDBManager()
        mongo_db = mongo.db
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        if not args.dry_run:
            return 1

    try:
        from services.TeachingAssistant.database.pinecone_client import pinecone_client as pc
        pinecone_client = pc
        if pc.enabled:
            logger.info("✅ Pinecone connected")
        else:
            logger.warning("⚠️ Pinecone not available")
    except Exception as e:
        logger.warning(f"⚠️ Pinecone not available: {e}")

    try:
        from services.TeachingAssistant.core.biographer import biographer_agent
        biographer = biographer_agent
        if biographer.enabled:
            logger.info("✅ Biographer Agent available")
        else:
            logger.warning("⚠️ Biographer Agent disabled (no OpenAI key)")
    except Exception as e:
        logger.warning(f"⚠️ Biographer Agent not available: {e}")

    logger.info("")

    # Find student directories
    if args.student_id:
        student_dir = old_data_path / args.student_id
        if student_dir.exists():
            student_dirs = [student_dir]
        else:
            logger.error(f"Student directory not found: {student_dir}")
            return 1
    else:
        student_dirs = find_student_data_dirs(old_data_path)

    if not student_dirs:
        logger.warning("No student data directories found")
        return 0

    logger.info(f"Found {len(student_dirs)} student(s) to migrate")
    logger.info("")

    # Migrate each student
    success_count = 0
    fail_count = 0

    for student_dir in student_dirs:
        student_data = load_old_student_data(student_dir)

        if migrate_student(
            student_data,
            mongo_db,
            pinecone_client,
            biographer,
            args.dry_run
        ):
            success_count += 1
        else:
            fail_count += 1

        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Total students: {len(student_dirs)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {fail_count}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
