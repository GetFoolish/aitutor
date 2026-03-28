#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


MODERN_REQUIRED_COLLECTIONS = {
    "generated_skills": "Generated skill graph used by DASH",
    "scraped_questions": "Source question bank used by the modern runtime",
}
LEGACY_REQUIRED_COLLECTIONS = {
    "skills": "Legacy skill graph used by compatibility mode",
    "dash_questions": "Legacy question bank used by compatibility mode",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "services" / "tools"


def get_dataset_counts(db) -> tuple[dict[str, int], dict[str, int]]:
    modern_counts = {
        collection_name: db[collection_name].count_documents({})
        for collection_name in MODERN_REQUIRED_COLLECTIONS
    }
    legacy_counts = {
        collection_name: db[collection_name].count_documents({})
        for collection_name in LEGACY_REQUIRED_COLLECTIONS
    }
    return modern_counts, legacy_counts


def has_compatible_dataset(db) -> bool:
    modern_counts, legacy_counts = get_dataset_counts(db)
    modern_ready = all(count > 0 for count in modern_counts.values())
    legacy_ready = all(count > 0 for count in legacy_counts.values())
    return modern_ready or legacy_ready


def run_legacy_seed() -> bool:
    if str(TOOLS_ROOT) not in sys.path:
        sys.path.insert(0, str(TOOLS_ROOT))

    from migrate_dash_questions_to_mongodb import migrate_dash_questions
    from migrate_skills_to_mongodb import migrate_skills

    return bool(migrate_skills() and migrate_dash_questions())


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")

    if not mongo_uri:
        print("MONGODB_URI is required to seed runtime Mongo data.")
        return 1

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except PyMongoError as exc:
        print(f"Could not connect to MongoDB using MONGODB_URI: {exc}")
        return 1

    db = client[db_name]
    if has_compatible_dataset(db):
        print("Runtime dataset already present; skipping seed step.")
        client.close()
        return 0

    client.close()
    print("No compatible runtime dataset found. Seeding legacy compatibility collections...")
    if not run_legacy_seed():
        print("Runtime seed step failed while populating legacy compatibility collections.")
        return 1

    try:
        verification_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        verification_client.admin.command("ping")
    except PyMongoError as exc:
        print(f"Could not reconnect to MongoDB after seed step: {exc}")
        return 1

    verification_db = verification_client[db_name]
    if has_compatible_dataset(verification_db):
        print("Runtime seed step populated a compatible dataset.")
        verification_client.close()
        return 0

    verification_client.close()
    print("Runtime seed step completed, but no compatible dataset was found afterward.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
