#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


REQUIRED_COLLECTIONS = {
    "generated_skills": "Generated skill graph used by DASH",
    "scraped_questions": "Source question bank used for runtime question loading",
}
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")

    if not mongo_uri:
        print("MONGODB_URI is required to verify seeded Mongo data.")
        return 1

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except PyMongoError as exc:
        print(f"Could not connect to MongoDB using MONGODB_URI: {exc}")
        return 1

    db = client[db_name]

    missing = []
    for collection_name, description in REQUIRED_COLLECTIONS.items():
        count = db[collection_name].count_documents({})
        print(f"{collection_name}: {count}")
        if count == 0:
            missing.append(f"{collection_name} ({description})")

    client.close()

    if missing:
        print("Seed verification failed. Missing required data:")
        for item in missing:
            print(f" - {item}")
        return 1

    print("Seed verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
