#!/usr/bin/env python3
"""
Ingest GSM8K (Grade School Math) dataset into AI Tutor MongoDB question bank.

Downloads openai/gsm8k from Hugging Face (MIT license), converts word problems
to multiple-choice format using an LLM to generate distractors, maps to DASH
skill IDs, and upserts into dash_questions collection.
"""

import hashlib
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
import requests
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PARQUET_URL = "https://huggingface.co/api/datasets/openai/gsm8k/parquet/main/train/0.parquet"
TARGET_QUESTIONS = 500
COLLECTION_NAME = "dash_questions"
SOURCE_TAG = "gsm8k"

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_mongo_db():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[os.environ.get("MONGODB_DB_NAME", "ai_tutor")]


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")


def call_openrouter(prompt: str, max_tokens: int = 400) -> str | None:
    """Call OpenRouter with a free model. Returns response text or None on failure."""
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set")
        sys.exit(1)
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": OPENROUTER_MODEL, "max_tokens": max_tokens,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        return content.strip() if content else None
    except Exception as e:
        print(f"  OpenRouter error: {e}")
        return None


def download_gsm8k():
    """Download and return GSM8K as list of dicts {question, answer}."""
    print(f"Downloading GSM8K from Hugging Face...")
    resp = requests.get(PARQUET_URL, timeout=60)
    resp.raise_for_status()
    table = pq.read_table(io.BytesIO(resp.content))
    rows = table.to_pydict()
    questions = rows.get("question", [])
    answers = rows.get("answer", [])
    print(f"  Downloaded {len(questions)} GSM8K problems")
    return [{"question": q, "answer": a} for q, a in zip(questions, answers)]


def extract_numeric_answer(answer_text: str) -> str:
    """Extract the final numeric answer from a GSM8K solution string."""
    # GSM8K answers end with #### <number>
    match = re.search(r"####\s*([\d,.\-]+)", answer_text)
    if match:
        return match.group(1).replace(",", "")
    # Fallback: last number in text
    nums = re.findall(r"-?\d+(?:\.\d+)?", answer_text)
    return nums[-1] if nums else "?"


def map_to_skill(question: str, skills: list[dict]) -> str:
    """Use LLM to map a question to the best matching DASH skill_id."""
    skills_list = "\n".join(f"- {s['skill_id']}: {s['name']} ({s['grade_level']})" for s in skills)
    prompt = f"""Given this math word problem, pick the SINGLE most relevant skill from the list below.
Return ONLY the skill_id, nothing else.

Problem: {question[:200]}

Skills:
{skills_list}"""
    try:
        skill_id = call_openrouter(prompt, max_tokens=50)
        if skill_id:
            skill_id = skill_id.strip().strip('"\'')
            valid_ids = {s["skill_id"] for s in skills}
            return skill_id if skill_id in valid_ids else skills[0]["skill_id"]
    except Exception:
        pass
    return skills[0]["skill_id"]


def generate_mcq(question: str, correct_answer: str) -> dict | None:
    """Convert a free-response problem to MCQ by generating 3 distractors."""
    prompt = f"""Convert this grade school math word problem into a 4-choice multiple choice question.

Problem: {question}
Correct answer: {correct_answer}

Generate 3 plausible wrong numerical answers (distractors) that a student might get by making common mistakes.

Respond with ONLY valid JSON in this exact format:
{{
  "question": "<the question text>",
  "choices": ["<choice A>", "<choice B>", "<choice C>", "<choice D>"],
  "correct_answer_index": <0-3>,
  "explanation": "<brief explanation of how to solve it>"
}}

Rules:
- correct_answer must appear as one of the 4 choices
- choices should be plausible numbers, not obviously wrong
- correct_answer_index is the 0-based index of the correct answer in choices"""

    for attempt in range(2):
        try:
            text = call_openrouter(prompt, max_tokens=400)
            if not text:
                continue
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if not json_match:
                continue
            data = json.loads(json_match.group())
            # Validate structure
            if (isinstance(data.get("choices"), list) and len(data["choices"]) == 4
                    and isinstance(data.get("correct_answer_index"), int)
                    and 0 <= data["correct_answer_index"] <= 3
                    and data.get("question") and data.get("explanation")):
                return data
        except Exception:
            if attempt == 0:
                time.sleep(1)
    return None


def stem_hash(skill_id: str, question: str) -> str:
    """Stable content hash for idempotent upsert."""
    return hashlib.sha256(f"{skill_id}||{question}".encode()).hexdigest()


def main():
    db = get_mongo_db()
    collection = db[COLLECTION_NAME]

    # Ensure indexes — partial filter so unique constraint only applies where content_hash exists
    try:
        collection.create_index(
            [("source", 1), ("content_hash", 1)],
            unique=True,
            partialFilterExpression={"content_hash": {"$type": "string"}},
            sparse=True,
        )
    except Exception as e:
        print(f"  Index warning (may already exist): {e}")
    collection.create_index("skill_id")

    # Load DASH skills
    skills = list(db["skills"].find({}, {"skill_id": 1, "name": 1, "grade_level": 1, "_id": 0}))
    if not skills:
        print("ERROR: No skills found in MongoDB")
        sys.exit(1)
    print(f"Loaded {len(skills)} DASH skills")

    # Check existing GSM8K count
    existing = collection.count_documents({"source": SOURCE_TAG})
    print(f"Existing {SOURCE_TAG} questions: {existing}")
    if existing >= TARGET_QUESTIONS:
        print(f"Already have {existing} >= {TARGET_QUESTIONS} target. Done.")
        return

    # Download dataset
    raw_data = download_gsm8k()

    # Process
    inserted = 0
    skipped = 0
    errors = 0
    before_total = collection.count_documents({})

    print(f"\nConverting GSM8K problems to MCQ (target: {TARGET_QUESTIONS})...")

    for i, row in enumerate(raw_data):
        if inserted + existing >= TARGET_QUESTIONS:
            break

        question_text = row["question"]
        correct_raw = extract_numeric_answer(row["answer"])

        # Map to skill
        skill_id = map_to_skill(question_text, skills)

        # Generate MCQ
        mcq = generate_mcq(question_text, correct_raw)
        if not mcq:
            errors += 1
            if i % 10 == 0:
                print(f"  [{i}] MCQ generation failed, skipping")
            continue

        # Build document
        content_hash = stem_hash(skill_id, mcq["question"])
        skill = next((s for s in skills if s["skill_id"] == skill_id), skills[0])

        doc = {
            "question_id": f"gsm8k_{content_hash[:12]}",
            "skill_id": skill_id,
            "skill_name": skill["name"],
            "grade_level": skill["grade_level"],
            "content": {
                "question": mcq["question"],
                "choices": mcq["choices"],
                "correct_answer_index": mcq["correct_answer_index"],
                "explanation": mcq["explanation"],
            },
            "correct_answer": mcq["choices"][mcq["correct_answer_index"]],
            "difficulty": "medium",
            "source": SOURCE_TAG,
            "llm_generated": False,
            "content_hash": content_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            result = collection.update_one(
                {"source": SOURCE_TAG, "content_hash": content_hash},
                {"$setOnInsert": doc},
                upsert=True,
            )
            if result.upserted_id:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            errors += 1

        if (inserted + skipped + errors) % 20 == 0:
            print(f"  Progress: {inserted} inserted, {skipped} skipped, {errors} errors")
            time.sleep(0.5)  # Rate limit buffer

    after_total = collection.count_documents({})
    after_gsm8k = collection.count_documents({"source": SOURCE_TAG})

    print(f"\n=== GSM8K Ingestion Complete ===")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (already existed): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total {SOURCE_TAG} questions: {after_gsm8k}")
    print(f"  Total dash_questions: {after_total} (was {before_total})")


if __name__ == "__main__":
    main()
