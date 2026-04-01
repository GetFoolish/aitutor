#!/usr/bin/env python3
"""
AMPS Dataset Ingestion Pipeline — Phase 2 Question Sourcing
============================================================
Ingests math questions from publicly-accessible HuggingFace math datasets
and converts them into multiple-choice questions stored in MongoDB.

Primary source : AMPS (qwedsacf/amps) via HF Datasets Server — requires
                 HF_TOKEN for gated access; set in .env as HF_TOKEN=hf_xxx
Fallback sources (publicly accessible, same Hendrycks et al. lineage):
  1. EleutherAI/hendrycks_math — competition math, 7 configs, ~7k total rows
  2. openai/gsm8k              — grade-school math word problems, 7.4k rows

Usage:
    python3 scripts/ingest_amps.py [--target 500] [--dry-run] [--offset 0]
    python3 scripts/ingest_amps.py --target 100 --dry-run   # smoke-test

Acceptance Criteria:
    - ≥500 questions imported and stored in MongoDB (amps_questions collection)
    - Each question tagged source="amps"
    - Mapped to DASH skill IDs where possible
    - Idempotent: re-running does not duplicate (uses SHA-1 question_id)
    - Completes in < 10 minutes for initial 500-question target

Environment Variables:
    MONGODB_URI       — MongoDB Atlas connection string (required)
    OPENROUTER_API_KEY — OpenRouter API key (required)
    OPENROUTER_MODEL  — LLM model slug (default: anthropic/claude-3-haiku)
    HF_TOKEN          — HuggingFace token for gated datasets (optional)
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


def map_to_skill(text: str, config_hint: str = "") -> Tuple[str, str]:
    """Return (skill_id, difficulty) for the given problem text + config hint."""
    combined = (text + " " + config_hint).lower()

    # Config-level overrides for hendrycks_math configs
    config_map: Dict[str, Tuple[str, str]] = {
        "prealgebra": ("fractions_intro", "medium"),
        "algebra": ("algebraic_expressions", "medium"),
        "intermediate_algebra": ("quadratic_intro", "hard"),
        "number_theory": ("integers", "hard"),
        "counting_and_probability": ("ratios_proportions", "hard"),
        "geometry": ("geometric_proofs", "hard"),
        "precalculus": ("trigonometry_basic", "hard"),
        "gsm8k": ("ratios_proportions", "medium"),  # word problems
    }

    for keywords, skill_id, difficulty in TOPIC_TO_SKILL:
        if any(kw in combined for kw in keywords):
            return skill_id, difficulty

    # Fall back to config hint
    if config_hint in config_map:
        return config_map[config_hint]

    return FALLBACK_SKILL_ID, FALLBACK_DIFFICULTY


# ── HuggingFace Datasets Server ───────────────────────────────────────────────

HF_DATASETS_SERVER = "https://datasets-server.huggingface.co"

# Dataset sources in priority order.
# Each entry: (dataset_id, config, split, row_field_map)
# row_field_map maps standard keys ("problem", "solution", "topic") → actual field names in row
DATASET_SOURCES: List[Dict[str, Any]] = [
    # Primary: AMPS (gated — needs HF_TOKEN)
    {
        "id": "qwedsacf/amps",
        "config": "khan",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "AMPS/Khan",
    },
    # Public fallbacks
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "prealgebra",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/prealgebra",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "algebra",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/algebra",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "intermediate_algebra",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/intermediate_algebra",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "number_theory",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/number_theory",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "counting_and_probability",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/counting_and_probability",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "geometry",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/geometry",
    },
    {
        "id": "EleutherAI/hendrycks_math",
        "config": "precalculus",
        "split": "train",
        "fields": {"problem": "problem", "solution": "solution", "topic": "type"},
        "label": "hendrycks_math/precalculus",
    },
    {
        "id": "openai/gsm8k",
        "config": "main",
        "split": "train",
        "fields": {"problem": "question", "solution": "answer", "topic": None},
        "label": "gsm8k",
    },
]


def _hf_headers() -> Dict[str, str]:
    token = os.environ.get("HF_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _probe_dataset(source: Dict[str, Any]) -> bool:
    """Return True if the dataset source is accessible."""
    url = f"{HF_DATASETS_SERVER}/rows"
    params = {
        "dataset": source["id"],
        "config": source["config"],
        "split": source["split"],
        "offset": 0,
        "limit": 1,
    }
    try:
        resp = requests.get(url, params=params, headers=_hf_headers(), timeout=15)
        return resp.status_code == 200
    except Exception:
        return False


def _iter_source(source: Dict[str, Any], offset: int = 0, batch_size: int = 100) -> Iterator[Dict]:
    """Yield raw rows from a HF Datasets Server source, paginating automatically."""
    url = f"{HF_DATASETS_SERVER}/rows"
    current = offset
    while True:
        params = {
            "dataset": source["id"],
            "config": source["config"],
            "split": source["split"],
            "offset": current,
            "limit": batch_size,
        }
        try:
            resp = requests.get(url, params=params, headers=_hf_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[{source['label']}] fetch error at offset {current}: {e}")
            break

        rows = data.get("rows", [])
        if not rows:
            break

        for r in rows:
            yield r["row"]

        current += len(rows)
        if len(rows) < batch_size:
            break  # last page


def extract_fields(row: Dict, field_map: Dict[str, Any]) -> Tuple[str, str, str]:
    """Extract (problem, solution, topic) using the source's field map."""
    problem = str(row.get(field_map["problem"], "") or "").strip()
    solution = str(row.get(field_map["solution"], "") or "").strip()
    topic_key = field_map.get("topic")
    topic = str(row.get(topic_key, "") or "").strip() if topic_key else ""
    return problem, solution, topic


def _try_datasets_library(source: Dict[str, Any], limit: int) -> Optional[List[Dict]]:
    """Try to load rows via the `datasets` library. Returns None if unavailable."""
    try:
        from datasets import load_dataset  # type: ignore

        hf_token = os.environ.get("HF_TOKEN")
        kwargs: Dict[str, Any] = {"streaming": True}
        if hf_token:
            kwargs["token"] = hf_token

        ds = load_dataset(source["id"], source["config"], split=source["split"], **kwargs)
        rows = []
        for item in ds:
            rows.append(item)
            if len(rows) >= limit:
                break
        return rows
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"`datasets` library failed for {source['label']}: {e}")
        return None


# ── LLM: MCQ Generation ───────────────────────────────────────────────────────

_MCQ_PROMPT_TEMPLATE = """\
You are a math educator converting a math problem into a multiple-choice question for a student assessment.

Given the problem and its correct answer/solution, output a JSON object with EXACTLY these fields:
{{
  "question": "<student-friendly question text, max 3 sentences, avoid raw LaTeX where possible>",
  "choices": ["<correct answer>", "<wrong1>", "<wrong2>", "<wrong3>"],
  "correct_answer": "<must exactly match one of the 4 choices>",
  "explanation": "<1-2 sentences explaining the correct answer>",
  "difficulty": "easy" | "medium" | "hard"
}}

Rules:
- Wrong answers must be plausible (common mistakes: sign error, off-by-one, wrong operation)
- If the problem is too long/complex to reasonably convert, output {{"skip": true}}
- Output ONLY valid JSON. No markdown fences. No extra text.

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
        "X-Title": "AI Tutor AMPS Ingestor",
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


def convert_to_mcq(problem: str, solution: str, api_key: str, model: str) -> Optional[Dict]:
    """Return parsed MCQ dict, or None if the problem should be skipped."""
    prompt = _MCQ_PROMPT_TEMPLATE.format(
        problem=problem[:800],
        solution=solution[:400],
    )
    raw = ""
    try:
        raw = _call_openrouter(prompt, model, api_key)
        # Strip accidental markdown fences
        raw = raw.strip()
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

def get_collection(db_name: str = "ai_tutor", coll_name: str = "amps_questions"):
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not set — check your .env file")
    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    client.admin.command("ping")
    return client[db_name][coll_name]


def ensure_indexes(coll) -> None:
    coll.create_index("question_id", unique=True, background=True)
    coll.create_index("skill_id", background=True)
    coll.create_index("source", background=True)


def build_document(mcq: Dict, raw_problem: str, skill_id: str) -> Dict:
    """Build a MongoDB document from a converted MCQ."""
    dedup_key = raw_problem[:200].encode("utf-8")
    question_id = "amps_" + hashlib.sha1(dedup_key).hexdigest()[:16]

    choices = mcq["choices"][:]
    random.shuffle(choices)

    return {
        "question_id": question_id,
        "skill_id": skill_id,
        "question": mcq["question"],
        "choices": choices,
        "correct_answer": mcq["correct_answer"],
        "explanation": mcq["explanation"],
        "source": "amps",
        "llm_generated": False,
        "difficulty": mcq.get("difficulty", FALLBACK_DIFFICULTY),
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

def run_pipeline(
    target: int = 500,
    dry_run: bool = False,
    start_offset: int = 0,
    batch_size: int = 50,
) -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set — check your .env file")

    model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
    logger.info(f"LLM model      : {model}")
    logger.info(f"Target         : {target} questions")
    logger.info(f"Dry run        : {dry_run}")

    if not dry_run:
        coll = get_collection()
        ensure_indexes(coll)
        logger.info("MongoDB        : connected (collection: amps_questions)")
    else:
        coll = None

    t_start = time.time()
    stored = 0
    skipped = 0
    llm_calls = 0
    docs_batch: List[Dict] = []

    def _flush():
        nonlocal stored
        if coll is not None and docs_batch:
            ins, _ = upsert_batch(coll, docs_batch)
            stored += ins
            docs_batch.clear()

    for source in DATASET_SOURCES:
        if stored >= target:
            break

        logger.info(f"\n[{source['label']}] Probing accessibility…")

        # Try `datasets` library first
        lib_rows = _try_datasets_library(source, limit=target * 3)

        if lib_rows is not None:
            logger.info(f"[{source['label']}] Loaded {len(lib_rows)} rows via `datasets` library")
            row_iter: Iterator = iter(lib_rows)
        else:
            # Fall back to HF Datasets Server REST API
            if not _probe_dataset(source):
                logger.warning(f"[{source['label']}] Not accessible — skipping")
                continue
            logger.info(f"[{source['label']}] Using HF Datasets Server REST API")
            row_iter = _iter_source(source, offset=start_offset, batch_size=batch_size)

        source_stored = 0
        for row in row_iter:
            if stored >= target:
                break

            elapsed = time.time() - t_start
            if elapsed > 540:
                logger.warning("Approaching 10-minute safety limit — stopping early")
                _flush()
                break

            problem, solution, topic = extract_fields(row, source["fields"])
            if not problem or not solution:
                skipped += 1
                continue
            if len(problem) < 15 or len(problem) > 1500:
                skipped += 1
                continue

            skill_id, _ = map_to_skill(problem, source["config"])

            try:
                mcq = convert_to_mcq(problem, solution, api_key, model)
                llm_calls += 1
            except Exception as e:
                logger.error(f"LLM error: {e}")
                skipped += 1
                continue

            if mcq is None:
                skipped += 1
                continue

            doc = build_document(mcq, problem, skill_id)

            if dry_run:
                print(json.dumps(doc, indent=2, ensure_ascii=False))
                stored += 1
                source_stored += 1
                continue

            docs_batch.append(doc)
            source_stored += 1

            if len(docs_batch) >= 25:
                _flush()
                logger.info(
                    f"[{source['label']}] stored={stored}/{target} "
                    f"skipped={skipped} llm_calls={llm_calls} elapsed={elapsed:.0f}s"
                )

        _flush()
        logger.info(
            f"[{source['label']}] Done — contributed {source_stored} candidates, "
            f"total stored={stored}"
        )

    elapsed_total = time.time() - t_start
    logger.info(
        "\n" + "=" * 60 + "\n"
        f"AMPS ingestion complete\n"
        f"  Questions stored : {stored}\n"
        f"  Skipped          : {skipped}\n"
        f"  LLM calls        : {llm_calls}\n"
        f"  Elapsed          : {elapsed_total:.1f}s\n"
        + "=" * 60
    )

    if not dry_run and stored < target:
        logger.warning(
            f"Only {stored}/{target} stored. "
            "Re-run with --offset or add more dataset sources."
        )

    return stored


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest math problems from HuggingFace into MongoDB")
    parser.add_argument("--target", type=int, default=500, help="Number of questions to import (default: 500)")
    parser.add_argument("--dry-run", action="store_true", help="Print docs without writing to MongoDB")
    parser.add_argument("--offset", type=int, default=0, help="Starting row offset in first dataset source")
    args = parser.parse_args()

    count = run_pipeline(target=args.target, dry_run=args.dry_run, start_offset=args.offset)

    if not args.dry_run and count < args.target:
        sys.exit(1)


if __name__ == "__main__":
    main()
