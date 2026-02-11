#!/usr/bin/env python3
"""
Backfill 2 additional hints on legacy ai_generated_questions that only have 1 hint.
Also un-retires radio questions after backfilling hints.

Uses Gemini to generate progressive hints based on existing question content.
"""
import os, sys, json, time, logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

import pymongo
import google.genai as genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

client = pymongo.MongoClient(os.environ["MONGODB_URI"])
db = client["ai_tutor"]
coll = db["ai_generated_questions"]

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
gemini = genai.Client(api_key=api_key)
MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")

HINT_PROMPT = """You are an expert tutor creating progressive hints for a student question.

Here is the question:
{question_text}

The existing first hint is:
{existing_hint}

Generate exactly 2 MORE hints that progress from the first hint.
- Hint 2: Should teach the relevant concept without giving the answer
- Hint 3: Should walk through the solution step by step, leading to the answer

Rules:
- Each hint must be at least 15 characters long
- Do NOT repeat the first hint
- Do NOT give the final answer directly in hint 2
- Hint 3 can nearly reveal the answer with guided walkthrough
- Use simple language appropriate for {age_band} students
- Return ONLY a JSON array of 2 strings, no other text

Example output:
["The concept here is about...", "Let's work through this step by step. First..."]
"""


def generate_hints(doc):
    """Generate 2 additional hints for a question document."""
    try:
        perseus = doc.get("perseus_json", {})
        question_text = perseus.get("question", {}).get("content", "")
        existing_hints = perseus.get("hints", [])

        if not question_text or len(existing_hints) != 1:
            return doc["_id"], None, "skip"

        existing_hint = existing_hints[0].get("content", "") if isinstance(existing_hints[0], dict) else str(existing_hints[0])
        age_band = doc.get("age_band", "middle")

        prompt = HINT_PROMPT.format(
            question_text=question_text[:500],
            existing_hint=existing_hint[:300],
            age_band=age_band,
        )

        response = gemini.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        text = response.text.strip()
        # Extract JSON array
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        new_hints = json.loads(text)
        if not isinstance(new_hints, list) or len(new_hints) < 2:
            return doc["_id"], None, "bad_format"

        # Build full 3-hint array
        hint1 = existing_hints[0] if isinstance(existing_hints[0], dict) else {"content": str(existing_hints[0])}
        # Ensure hint1 has all required fields
        hint1.setdefault("images", {})
        hint1.setdefault("replace", False)
        hint1.setdefault("widgets", {})

        all_hints = [
            hint1,
            {"content": str(new_hints[0]), "images": {}, "replace": False, "widgets": {}},
            {"content": str(new_hints[1]), "images": {}, "replace": False, "widgets": {}},
        ]

        return doc["_id"], all_hints, "ok"

    except Exception as e:
        return doc["_id"], None, f"error: {e}"


def main():
    # Get all 1-hint questions
    one_hint_docs = list(coll.find(
        {"$expr": {"$eq": [{"$size": {"$ifNull": ["$perseus_json.hints", []]}}, 1]}},
        {"_id": 1, "perseus_json": 1, "age_band": 1, "question_id": 1}
    ))

    total = len(one_hint_docs)
    logger.info(f"Found {total} questions with 1 hint to backfill")

    if total == 0:
        logger.info("Nothing to do!")
        return

    success = 0
    failed = 0
    skipped = 0

    # Process in parallel with 5 workers
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(generate_hints, doc): doc for doc in one_hint_docs}

        for i, future in enumerate(as_completed(futures)):
            doc_id, hints, status = future.result()

            if status == "ok" and hints:
                # Update DB
                coll.update_one(
                    {"_id": doc_id},
                    {"$set": {"perseus_json.hints": hints}}
                )
                success += 1
            elif status == "skip":
                skipped += 1
            else:
                failed += 1

            if (i + 1) % 50 == 0 or (i + 1) == total:
                logger.info(f"Progress: {i+1}/{total} | success={success} failed={failed} skipped={skipped}")

    # Un-retire radio questions that now have 3 hints
    unretire = coll.update_many(
        {
            "quality.retired": True,
            "quality.retired_reason": "legacy_1hint_radio_only",
            "$expr": {"$eq": [{"$size": {"$ifNull": ["$perseus_json.hints", []]}}, 3]},
        },
        {
            "$set": {
                "quality.retired": False,
                "quality.quality_score": 0.35,  # Low but usable
            },
            "$unset": {"quality.retired_reason": ""}
        }
    )
    logger.info(f"Un-retired {unretire.modified_count} radio questions (now have 3 hints)")

    # Un-deprioritize orderer questions that now have 3 hints
    undeprior = coll.update_many(
        {
            "quality.deprioritized_reason": "legacy_1hint",
            "$expr": {"$eq": [{"$size": {"$ifNull": ["$perseus_json.hints", []]}}, 3]},
        },
        {
            "$set": {"quality.quality_score": 0.45},
            "$unset": {"quality.deprioritized_reason": ""}
        }
    )
    logger.info(f"Un-deprioritized {undeprior.modified_count} orderer questions (now have 3 hints)")

    logger.info(f"\nDONE. Success={success}, Failed={failed}, Skipped={skipped}")

    client.close()


if __name__ == "__main__":
    main()
