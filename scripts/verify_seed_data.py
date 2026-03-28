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


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")

    if not mongo_uri:
        print("MONGODB_URI not set — skipping seed verification (Cloud Run services receive the secret at runtime).")
        return 0

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except PyMongoError as exc:
        print(f"Could not connect to MongoDB using MONGODB_URI: {exc}")
        return 1

    db = client[db_name]

    modern_counts = {}
    legacy_counts = {}

    for collection_name in MODERN_REQUIRED_COLLECTIONS:
        modern_counts[collection_name] = db[collection_name].count_documents({})
        print(f"{collection_name}: {modern_counts[collection_name]}")

    for collection_name in LEGACY_REQUIRED_COLLECTIONS:
        legacy_counts[collection_name] = db[collection_name].count_documents({})
        print(f"{collection_name}: {legacy_counts[collection_name]}")

    client.close()

    modern_ready = all(count > 0 for count in modern_counts.values())
    legacy_ready = all(count > 0 for count in legacy_counts.values())

    if modern_ready:
        print("Seed verification passed using modern runtime collections.")
        return 0

    if legacy_ready:
        print("Seed verification passed using legacy compatibility collections.")
        if modern_counts["generated_skills"] > 0 and modern_counts["scraped_questions"] == 0:
            print("Modern generated_skills exists but scraped_questions is empty; runtime will use legacy compatibility mode.")
        return 0

    print("Seed verification failed. No compatible runtime dataset was found.")
    print("Missing modern collections:")
    for collection_name, description in MODERN_REQUIRED_COLLECTIONS.items():
        if modern_counts[collection_name] == 0:
            print(f" - {collection_name} ({description})")

    print("Missing legacy collections:")
    for collection_name, description in LEGACY_REQUIRED_COLLECTIONS.items():
        if legacy_counts[collection_name] == 0:
            print(f" - {collection_name} ({description})")

    return 1


if __name__ == "__main__":
    sys.exit(main())
