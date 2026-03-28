#!/usr/bin/env python3
"""
Ingest meta-math/MetaMathQA dataset into AI Tutor MongoDB question bank.

Downloads parquet files from Hugging Face datasets-server API, deduplicates
by problem content hash, and bulk-inserts into dash_questions. No LLM required.

Dataset: ~395K diverse rewrites of GSM8K and MATH problems with augmented solutions.
License: MIT
"""

import hashlib
import io
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import requests
from pymongo import MongoClient, UpdateOne

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

COLLECTION_NAME = "dash_questions"
SOURCE_TAG = "metamathqa"
LICENSE_TAG = "mit"
HF_DATASET = "meta-math/MetaMathQA"
HF_PARQUET_API = (
    "https://datasets-server.huggingface.co/parquet?dataset=meta-math%2FMetaMathQA"
)

TARGET_UNIQUE = 395_000
BULK_BATCH_SIZE = 1_000
MAX_FIELD_LEN = 32_000  # guard against oversized documents

# Map MetaMathQA 'type' field prefixes to DASH skill category keywords
TYPE_TO_KEYWORD = {
    "gsm": "word",
    "math": "algebra",
    "algebra": "algebra",
    "geometry": "geometry",
    "number": "number",
    "counting": "counting",
    "precalc": "algebra",
    "prealgebra": "algebra",
    "intermediate": "algebra",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------


def get_mongo_db():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[os.environ.get("MONGODB_DB_NAME", "ai_tutor")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def content_hash(query: str) -> str:
    """Stable SHA-256 hash of query text for idempotent upsert."""
    return hashlib.sha256(query.encode("utf-8", errors="replace")).hexdigest()


def safe_str(value, max_len: int = MAX_FIELD_LEN) -> str:
    """Sanitize and truncate a value to a safe string."""
    if value is None:
        return ""
    text = str(value)
    # Strip null bytes (MongoDB rejects them in strings)
    text = text.replace("\x00", "")
    return text[:max_len]


def map_skill_by_type(problem_type: str, skills: list[dict]) -> dict:
    """Map MetaMathQA type to a DASH skill without LLM, using keyword matching."""
    if not skills:
        return {"skill_id": "MATH-001", "name": "Mathematics", "grade_level": "9-12"}
    # problem_type looks like "GSM_MATH_Rephrased", "MATH_Backward", "GSM_AnsAug", etc.
    prefix = problem_type.split("_")[0].lower() if problem_type else ""
    keyword = TYPE_TO_KEYWORD.get(prefix, "")
    if keyword:
        for s in skills:
            if keyword.lower() in s.get("name", "").lower():
                return s
    return skills[0]


# ---------------------------------------------------------------------------
# HF parquet discovery
# ---------------------------------------------------------------------------


def get_parquet_urls() -> list[str]:
    """Fetch parquet file URLs from Hugging Face datasets-server API."""
    print(f"Fetching parquet file list for {HF_DATASET}...")
    resp = requests.get(HF_PARQUET_API, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    files = data.get("parquet_files", [])
    # Filter to train split only
    urls = [
        f["url"]
        for f in files
        if isinstance(f, dict) and f.get("split") == "train"
    ]
    if not urls:
        # Fallback: accept any split
        urls = [f["url"] for f in files if isinstance(f, dict) and "url" in f]
    print(f"  Found {len(urls)} parquet files")
    return urls


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def process_parquet_file(
    url: str,
    skills: list[dict],
    collection,
    seen_hashes: set,
) -> tuple[int, int]:
    """Download and process one parquet file. Returns (inserted, deduplicated)."""
    inserted = 0
    deduplicated = 0

    print(f"  Downloading {url.split('/')[-1]}...", flush=True)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()

    table = pq.read_table(io.BytesIO(resp.content))
    rows = table.to_pydict()

    queries = rows.get("query", [])
    responses = rows.get("response", []) or []
    types = rows.get("type", []) or []
    original_questions = rows.get("original_question", []) or []

    ops: list[UpdateOne] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for i, query in enumerate(queries):
        if len(seen_hashes) >= TARGET_UNIQUE:
            break

        query = safe_str(query)
        if not query:
            deduplicated += 1
            continue

        ch = content_hash(query)
        if ch in seen_hashes:
            deduplicated += 1
            continue
        seen_hashes.add(ch)

        response = safe_str(responses[i] if i < len(responses) else "")
        problem_type = safe_str(types[i] if i < len(types) else "", max_len=128)
        original_question = safe_str(
            original_questions[i] if i < len(original_questions) else ""
        )

        skill = map_skill_by_type(problem_type, skills)

        doc = {
            "question_id": f"metamathqa_{ch[:12]}",
            "skill_id": skill["skill_id"],
            "skill_name": skill.get("name", "Mathematics"),
            "grade_level": skill.get("grade_level", "9-12"),
            "content": {
                "question": query,
                "solution": response,
                "original_question": original_question,
            },
            "correct_answer": "",
            "difficulty": "medium",
            "source": SOURCE_TAG,
            "license": LICENSE_TAG,
            "problem_type": problem_type,
            "llm_generated": False,
            "content_hash": ch,
            "created_at": now_iso,
        }

        ops.append(
            UpdateOne(
                {"source": SOURCE_TAG, "content_hash": ch},
                {"$setOnInsert": doc},
                upsert=True,
            )
        )

        if len(ops) >= BULK_BATCH_SIZE:
            result = collection.bulk_write(ops, ordered=False)
            inserted += result.upserted_count
            ops = []

    # Flush remainder
    if ops:
        result = collection.bulk_write(ops, ordered=False)
        inserted += result.upserted_count

    return inserted, deduplicated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    db = get_mongo_db()
    collection = db[COLLECTION_NAME]

    # Ensure indexes
    try:
        collection.create_index(
            [("source", 1), ("content_hash", 1)],
            unique=True,
            partialFilterExpression={"content_hash": {"$type": "string"}},
            sparse=True,
        )
    except Exception as e:
        print(f"  Index note (may already exist): {e}")
    collection.create_index("skill_id")

    # Load DASH skills for mapping
    skills = list(
        db["skills"].find({}, {"skill_id": 1, "name": 1, "grade_level": 1, "_id": 0})
    )
    if not skills:
        print("ERROR: No skills found in MongoDB. Run seed scripts first.")
        sys.exit(1)
    print(f"Loaded {len(skills)} DASH skills")

    # Check existing count
    existing = collection.count_documents({"source": SOURCE_TAG})
    print(f"Existing {SOURCE_TAG} questions: {existing}")
    if existing >= TARGET_UNIQUE:
        print(f"Already have {existing} >= {TARGET_UNIQUE:,} target. Done.")
        return

    # Load existing hashes to enable resume without re-inserting
    print("Loading existing content hashes for deduplication...")
    seen_hashes: set[str] = set(
        doc["content_hash"]
        for doc in collection.find(
            {"source": SOURCE_TAG}, {"content_hash": 1, "_id": 0}
        )
        if doc.get("content_hash")
    )
    print(f"  Loaded {len(seen_hashes)} existing hashes (resume-safe)")

    # Discover parquet files
    urls = get_parquet_urls()
    if not urls:
        print("ERROR: No parquet files found from HF API")
        sys.exit(1)

    before_total = collection.count_documents({})
    total_inserted = 0
    total_dedup = 0
    start = time.time()

    for file_idx, url in enumerate(urls):
        if len(seen_hashes) >= TARGET_UNIQUE:
            print(f"\nTarget of {TARGET_UNIQUE:,} unique problems reached.")
            break

        unique_so_far = len(seen_hashes)
        print(
            f"\n[{file_idx + 1}/{len(urls)}] {url.split('/')[-1]} "
            f"| unique so far: {unique_so_far:,} / {TARGET_UNIQUE:,}"
        )

        try:
            ins, dedup = process_parquet_file(url, skills, collection, seen_hashes)
            total_inserted += ins
            total_dedup += dedup
            elapsed = time.time() - start
            rate = total_inserted / elapsed if elapsed > 0 else 0
            print(
                f"  +{ins:,} inserted | {dedup:,} dedup skipped "
                f"| cumulative: {total_inserted:,} | rate: {rate:.0f}/s"
            )
        except Exception as e:
            print(f"  ERROR on {url.split('/')[-1]}: {e}")
            continue

    after_total = collection.count_documents({})
    after_source = collection.count_documents({"source": SOURCE_TAG})
    elapsed = time.time() - start

    print(f"\n=== MetaMathQA Ingestion Complete ===")
    print(f"  Source:         {HF_DATASET}")
    print(f"  Inserted:       {total_inserted:,}")
    print(f"  Dedup skipped:  {total_dedup:,}")
    print(f"  Total {SOURCE_TAG}: {after_source:,}")
    print(f"  Total dash_questions: {after_total:,} (was {before_total:,})")
    print(f"  Elapsed: {elapsed:.1f}s")

    if after_source < TARGET_UNIQUE:
        print(
            f"\nWARNING: Only {after_source:,} inserted — "
            f"dataset may have fewer unique problems than {TARGET_UNIQUE:,}."
        )


if __name__ == "__main__":
    main()
