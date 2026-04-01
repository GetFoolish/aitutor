#!/usr/bin/env python3
"""
MATH Dataset Ingestion Pipeline — Phase 4 Question Sourcing
============================================================
Ingests math questions from the Hendrycks MATH dataset on HuggingFace
and converts them into multiple-choice questions stored in MongoDB.

Primary dataset: EleutherAI/hendrycks_math (publicly accessible via HF
Datasets Server). This is the canonical Hendrycks et al. MATH competition
benchmark — same data as lighteval/MATH. ~12,500 rows across 7 configs:
algebra, counting_and_probability, geometry, intermediate_algebra,
number_theory, prealgebra, precalculus. MIT license.

Usage:
    python3 scripts/ingest_math_dataset.py [--target 7500] [--dry-run] [--offset 0]
    python3 scripts/ingest_math_dataset.py --target 5 --dry-run   # smoke-test

Acceptance Criteria:
    - ≥1,000 questions imported and stored in MongoDB (math_questions collection)
    - Each question tagged source="math_dataset"
    - Mapped to DASH skill IDs where possible
    - Idempotent: re-running does not duplicate (uses SHA-1 question_id)
    - Uses OpenRouter free model (NOT Anthropic API key)

Environment Variables:
    MONGODB_URI         — MongoDB Atlas connection string (required)
    OPENROUTER_API_KEY  — OpenRouter API key (required)
    OPENROUTER_MODEL    — LLM model slug (default: moonshotai/kimi-k2-0905)
    HF_TOKEN            — HuggingFace token (optional, dataset is public)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# ── Setup ─────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Load .env from project root (two dirs up from scripts/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path)

# ── DASH Skill Mapping ────────────────────────────────────────────────────────

# Maps topic keywords → (skill_id, difficulty)
# Order matters: first match wins; use most-specific patterns first.
TOPIC_TO_SKILL: List[Tuple[List[str], str, str]] = [
    (["count", "number recognition"], "counting_1_10", "easy"),
    (["basic addition", "add single", "addition fact"], "addition_basic", "easy"),
    (["basic subtraction", "subtract single", "subtraction fact"], "subtraction_basic", "easy"),
    (["count to 100", "skip count", "count by"], "counting_100", "easy"),
    (["two-digit addition", "2-digit add"], "addition_2digit", "easy"),
    (["two-digit subtraction", "2-digit subtract"], "subtraction_2digit", "easy"),
    (["times table", "multiplication table", "multiply single"], "multiplication_tables", "easy"),
    (["division", "divide", "quotient", "divisible by"], "division_basic", "medium"),
    (["fraction operation", "add fraction", "subtract fraction", "fraction multipl"], "fractions_operations", "medium"),
    (["fraction", "numerator", "denominator", "1/2", "1/3", "1/4"], "fractions_intro", "medium"),
    (["decimal operation", "add decimal", "subtract decimal", "multiply decimal"], "decimals_operations", "medium"),
    (["decimal", "hundredths", "tenths", "place value"], "decimals_intro", "medium"),
    (["percent", "percentage", "%"], "percentages", "medium"),
    (["integer", "negative number", "absolute value", "opposite of"], "integers", "medium"),
    (["ratio", "proportion", "unit rate", "rate of"], "ratios_proportions", "medium"),
    (["simplify expression", "evaluate expression", "algebraic expression"], "algebraic_expressions", "medium"),
    (["solve for x", "one-step equation", "two-step equation", "linear equation in one"], "linear_equations_1var", "medium"),
    (["system of equations", "two variables", "simultaneous equation"], "linear_equations_2var", "hard"),
    (["quadratic formula", "solve quadratic", "discriminant"], "quadratic_equations", "hard"),
    (["quadratic", "parabola", "vertex form", "completing the square"], "quadratic_intro", "hard"),
    (["polynomial", "binomial", "trinomial", "degree of polynomial"], "polynomial_operations", "hard"),
    (["geometry proof", "congruent triangle", "similar triangle", "theorem"], "geometric_proofs", "hard"),
    (["sin(", "cos(", "tan(", "right triangle trig", "trigonometry"], "trigonometry_basic", "hard"),
    (["logarithm", "log base", "ln(", "exponential growth", "exponential decay"], "exponentials_logs", "hard"),
    (["law of sines", "law of cosines", "unit circle", "radian"], "trigonometry_advanced", "hard"),
    (["limit", "approaches infinity", "lim "], "limits", "hard"),
    (["derivative", "differentiate", "rate of change", "slope of tangent"], "derivatives", "hard"),
    # Broader matches come last
    (["multiply", "multiplication"], "multiplication_intro", "easy"),
    (["shape", "area", "perimeter", "rectangle", "circle", "triangle", "polygon"], "basic_shapes", "easy"),
    (["variable", "expression", "algebraic"], "algebraic_expressions", "medium"),
]

FALLBACK_SKILL_ID = "algebraic_expressions"
FALLBACK_DIFFICULTY = "medium"

# lighteval/MATH subject type → (skill_id, difficulty) override
TYPE_TO_SKILL: Dict[str, Tuple[str, str]] = {
    "prealgebra": ("fractions_intro", "medium"),
    "algebra": ("algebraic_expressions", "medium"),
    "intermediate_algebra": ("quadratic_intro", "hard"),
    "number_theory": ("integers", "hard"),
    "counting_and_probability": ("ratios_proportions", "hard"),
    "geometry": ("geometric_proofs", "hard"),
    "precalculus": ("trigonometry_basic", "hard"),
}

# MATH level → difficulty override
LEVEL_TO_DIFFICULTY: Dict[str, str] = {
    "Level 1": "easy",
    "Level 2": "easy",
    "Level 3": "medium",
    "Level 4": "hard",
    "Level 5": "hard",
}


def map_to_skill(text: str, subject_type: str = "", level: str = "") -> Tuple[str, str]:
    """Return (skill_id, difficulty) for the given problem text + type hint."""
    combined = (text + " " + subject_type).lower()

    for keywords, skill_id, difficulty in TOPIC_TO_SKILL:
        if any(kw in combined for kw in keywords):
            # Override difficulty if level is present
            if level in LEVEL_TO_DIFFICULTY:
                difficulty = LEVEL_TO_DIFFICULTY[level]
            return skill_id, difficulty

    # Fall back to subject type map
    if subject_type.lower() in TYPE_TO_SKILL:
        skill_id, difficulty = TYPE_TO_SKILL[subject_type.lower()]
        if level in LEVEL_TO_DIFFICULTY:
            difficulty = LEVEL_TO_DIFFICULTY[level]
        return skill_id, difficulty

    diff = LEVEL_TO_DIFFICULTY.get(level, FALLBACK_DIFFICULTY)
    return FALLBACK_SKILL_ID, diff


# ── HuggingFace Datasets ───────────────────────────────────────────────────────

HF_DATASETS_SERVER = "https://datasets-server.huggingface.co"

# EleutherAI/hendrycks_math configs — one per subject
# Ordered by expected MCQ yield (easier/word-problem configs first)
# intermediate_algebra and precalculus contain hard competition problems
# with complex notation — lower yield, placed last
MATH_DATASET_ID = "EleutherAI/hendrycks_math"
MATH_CONFIGS: List[str] = [
    "algebra",                   # ~2,931 rows, good yield
    "prealgebra",                # ~2,076 rows, good yield
    "number_theory",             # ~1,409 rows, reasonable yield
    "counting_and_probability",  # ~1,245 rows, reasonable yield
    "geometry",                  # ~1,349 rows, mixed yield
    "precalculus",               # ~1,292 rows, lower yield
    "intermediate_algebra",      # ~2,198 rows, lowest yield (complex notation)
]


def _hf_headers() -> Dict[str, str]:
    token = os.environ.get("HF_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _probe_dataset(dataset_id: str, config: str, split: str = "train") -> bool:
    """Return True if the dataset/config/split is accessible via HF Datasets Server."""
    url = f"{HF_DATASETS_SERVER}/rows"
    params = {"dataset": dataset_id, "config": config, "split": split, "offset": 0, "limit": 1}
    try:
        resp = requests.get(url, params=params, headers=_hf_headers(), timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def _iter_hf_server(
    dataset_id: str,
    config: str,
    split: str,
    offset: int = 0,
    batch_size: int = 100,
) -> Iterator[Dict]:
    """Yield raw rows from HF Datasets Server, paginating automatically."""
    url = f"{HF_DATASETS_SERVER}/rows"
    current = offset
    while True:
        params = {
            "dataset": dataset_id,
            "config": config,
            "split": split,
            "offset": current,
            "limit": batch_size,
        }
        try:
            resp = requests.get(url, params=params, headers=_hf_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"HF server fetch error at offset {current}: {e}")
            break

        rows = data.get("rows", [])
        if not rows:
            break

        for r in rows:
            yield r["row"]

        current += len(rows)
        if len(rows) < batch_size:
            break  # last page


def iter_math_rows(
    target: int,
    start_offset: int = 0,
    batch_size: int = 100,
) -> Iterator[Tuple[str, str, str, str]]:
    """
    Yield (problem, solution, subject_type, level) tuples from EleutherAI/hendrycks_math.

    Iterates train then test splits for each config (subject).
    Fields: problem, solution, type (subject), level (Level 1-5).
    """
    yielded = 0

    for config in MATH_CONFIGS:
        if yielded >= target * 3:  # fetch 3× headroom to account for LLM skips
            break

        for split in ("train", "test"):
            logger.info(f"\n[{MATH_DATASET_ID}/{config}/{split}] Loading…")

            if not _probe_dataset(MATH_DATASET_ID, config, split):
                logger.warning(f"[{MATH_DATASET_ID}/{config}/{split}] Not accessible — skipping")
                continue

            row_iter: Iterator[Dict] = _iter_hf_server(
                MATH_DATASET_ID, config, split, offset=start_offset, batch_size=batch_size
            )

            config_yielded = 0
            for row in row_iter:
                problem = str(row.get("problem", "") or "").strip()
                solution = str(row.get("solution", "") or "").strip()
                subject_type = str(row.get("type", "") or "").strip()
                level = str(row.get("level", "") or "").strip()

                if not problem or not solution:
                    continue
                if len(problem) < 15 or len(problem) > 1500:
                    continue

                yield problem, solution, subject_type, level
                yielded += 1
                config_yielded += 1


# ── LLM: MCQ Generation ───────────────────────────────────────────────────────

_MCQ_PROMPT_TEMPLATE = """\
You are a math educator converting a math problem into a multiple-choice question for student assessment.

Given the problem and its solution, output a JSON object with EXACTLY these fields:
{{
  "question": "<student-friendly question, max 2 sentences, avoid raw LaTeX>",
  "choices": ["<correct answer>", "<wrong1>", "<wrong2>", "<wrong3>"],
  "correct_answer": "<must exactly match one of the 4 choices exactly>",
  "explanation": "<1 sentence explanation>",
  "difficulty": "easy" | "medium" | "hard"
}}

Rules:
- Wrong answers must be plausible (sign error, off-by-one, wrong formula)
- choices must have exactly 4 distinct items
- correct_answer must be a short final answer (number, expression, or brief phrase)
- Simplify the question if needed — paraphrase to make it student-friendly
- Only output {{"skip": true}} if the problem REQUIRES a diagram or image to solve
- Output ONLY valid JSON. No markdown. No extra text.

Problem:
{problem}

Correct Answer / Solution:
{solution}

JSON:"""


def _call_openrouter(prompt: str, model: str, api_key: str, max_tokens: int = 512) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "AI Tutor MATH Ingestor",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=35)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"OpenRouter failed after 3 attempts: {e}") from e
    return ""


def convert_to_mcq(
    problem: str,
    solution: str,
    api_key: str,
    model: str,
) -> Optional[Dict]:
    """Return parsed MCQ dict, or None if the problem should be skipped."""
    prompt = _MCQ_PROMPT_TEMPLATE.format(
        problem=problem[:800],
        solution=solution[:400],
    )
    raw = ""
    try:
        raw = _call_openrouter(prompt, model, api_key)
        raw = raw.strip()
        # Strip accidental markdown fences
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if parsed.get("skip"):
            return None
        required = {"question", "choices", "correct_answer", "explanation", "difficulty"}
        if not required.issubset(parsed.keys()):
            return None
        if len(parsed["choices"]) != 4:
            return None
        if parsed["correct_answer"] not in parsed["choices"]:
            return None
        return parsed
    except Exception as e:
        logger.debug(f"MCQ parse error: {e} | raw={raw[:120]!r}")
        return None


# ── MongoDB ───────────────────────────────────────────────────────────────────

COLLECTION_NAME = "math_questions"


def get_collection(db_name: str = "ai_tutor"):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not set — check your .env file")
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    return client[db_name][COLLECTION_NAME]


def ensure_indexes(coll) -> None:
    coll.create_index("question_id", unique=True, background=True)
    coll.create_index("skill_id", background=True)
    coll.create_index("source", background=True)
    coll.create_index("difficulty", background=True)


def build_document(
    mcq: Dict,
    raw_problem: str,
    skill_id: str,
    difficulty_override: Optional[str] = None,
) -> Dict:
    """Build a MongoDB document from a converted MCQ."""
    dedup_key = raw_problem[:200].encode("utf-8")
    question_id = "math_" + hashlib.sha1(dedup_key).hexdigest()[:16]

    choices = mcq["choices"][:]
    random.shuffle(choices)

    difficulty = difficulty_override or mcq.get("difficulty", FALLBACK_DIFFICULTY)

    return {
        "question_id": question_id,
        "skill_id": skill_id,
        "question": mcq["question"],
        "choices": choices,
        "correct_answer": mcq["correct_answer"],
        "explanation": mcq["explanation"],
        "source": "math_dataset",
        "llm_generated": False,
        "difficulty": difficulty,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_batch(coll, docs: List[Dict]) -> Tuple[int, int]:
    if not docs:
        return 0, 0
    ops = [
        UpdateOne(
            {"question_id": doc["question_id"]},
            {"$setOnInsert": doc},
            upsert=True,
        )
        for doc in docs
    ]
    result = coll.bulk_write(ops, ordered=False)
    return result.upserted_count, result.modified_count


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def _process_row(
    row_tuple: Tuple[str, str, str, str],
    api_key: str,
    model: str,
) -> Optional[Dict]:
    """Convert one raw row to a MongoDB document. Returns None to skip."""
    problem, solution, subject_type, level = row_tuple
    skill_id, difficulty = map_to_skill(problem, subject_type, level)
    try:
        mcq = convert_to_mcq(problem, solution, api_key, model)
    except Exception as e:
        logger.debug(f"LLM error for row: {e}")
        return None
    if mcq is None:
        return None
    return build_document(mcq, problem, skill_id, difficulty_override=difficulty)


def run_pipeline(
    target: int = 7500,
    dry_run: bool = False,
    start_offset: int = 0,
    batch_size: int = 100,
    workers: int = 10,
    time_limit_sec: int = 3300,  # 55 min safety cap
) -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set — check your .env file")

    model = os.environ.get("OPENROUTER_MODEL", "moonshotai/kimi-k2-0905")
    logger.info(f"LLM model      : {model}")
    logger.info(f"Target         : {target} questions")
    logger.info(f"Workers        : {workers}")
    logger.info(f"Dry run        : {dry_run}")
    logger.info(f"Dataset        : {MATH_DATASET_ID}")

    if not dry_run:
        coll = get_collection()
        ensure_indexes(coll)
        existing = coll.count_documents({"source": "math_dataset"})
        logger.info(f"MongoDB        : connected (collection: {COLLECTION_NAME}, existing: {existing})")
    else:
        coll = None
        existing = 0

    # Remaining needed (idempotent)
    remaining = max(0, target - existing)
    if remaining == 0:
        logger.info(f"Already have {existing} ≥ {target} — nothing to do.")
        return existing

    logger.info(f"Need to ingest : {remaining} more questions")

    t_start = time.time()
    stored = 0
    skipped = 0
    llm_calls = 0
    docs_batch: List[Dict] = []

    def _flush() -> None:
        nonlocal stored
        if coll is not None and docs_batch:
            ins, _ = upsert_batch(coll, docs_batch)
            stored += ins
            docs_batch.clear()

    # Collect rows for parallel processing in batches
    row_buffer: List[Tuple[str, str, str, str]] = []
    SUBMIT_BATCH = workers * 3  # submit 3× workers at a time

    def _submit_and_collect() -> None:
        nonlocal stored, skipped, llm_calls
        if not row_buffer:
            return
        batch = row_buffer[:]
        row_buffer.clear()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process_row, r, api_key, model): r for r in batch}
            for fut in as_completed(futures):
                llm_calls += 1
                doc = fut.result()
                if doc is None:
                    skipped += 1
                else:
                    if dry_run:
                        print(json.dumps(doc, indent=2, ensure_ascii=False))
                        stored += 1
                    else:
                        docs_batch.append(doc)

        if not dry_run:
            _flush()

        elapsed = time.time() - t_start
        logger.info(
            f"stored={stored}/{remaining} skipped={skipped} "
            f"llm_calls={llm_calls} elapsed={elapsed:.0f}s"
        )

    for row_tuple in iter_math_rows(
        target=remaining,
        start_offset=start_offset,
        batch_size=batch_size,
    ):
        if stored >= remaining:
            break

        elapsed = time.time() - t_start
        if elapsed > time_limit_sec:
            logger.warning(f"Approaching {time_limit_sec}s safety limit — stopping early")
            break

        if dry_run and stored >= min(5, remaining):
            break

        row_buffer.append(row_tuple)

        if len(row_buffer) >= SUBMIT_BATCH:
            _submit_and_collect()
            if stored >= remaining:
                break

    # Process any remaining rows
    if row_buffer and stored < remaining:
        _submit_and_collect()

    _flush()

    total = existing + stored
    elapsed_total = time.time() - t_start
    logger.info(
        "\n" + "=" * 60 + "\n"
        f"MATH dataset ingestion complete\n"
        f"  New questions stored : {stored}\n"
        f"  Total in collection  : {total}\n"
        f"  Skipped              : {skipped}\n"
        f"  LLM calls            : {llm_calls}\n"
        f"  Elapsed              : {elapsed_total:.1f}s\n"
        + "=" * 60
    )

    if not dry_run and total < target:
        logger.warning(
            f"Only {total}/{target} total. "
            "Re-run with --offset or wait for rate limits to clear."
        )

    return total


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest MATH dataset problems from HuggingFace into MongoDB"
    )
    parser.add_argument(
        "--target", type=int, default=7500,
        help="Target total questions in collection (default: 7500)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print up to 5 docs without writing to MongoDB",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Starting row offset in dataset (default: 0)",
    )
    parser.add_argument(
        "--workers", type=int, default=10,
        help="Parallel LLM workers (default: 10)",
    )
    args = parser.parse_args()

    total = run_pipeline(
        target=args.target,
        dry_run=args.dry_run,
        start_offset=args.offset,
        workers=args.workers,
    )

    if not args.dry_run and total < args.target:
        sys.exit(1)


if __name__ == "__main__":
    main()
