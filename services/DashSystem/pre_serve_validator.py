"""
Pre-Serve Validation Gate — catches broken/unanswerable questions at serve time.

Runs on every question before it reaches the student. Pure Python, no LLM calls,
no network I/O. Target: < 10ms per question.

Three independent checks:
  1. Answerability   — correct answer exists and has required fields per widget type
  2. Dry-run scoring — Python port of frontend scoring confirms correct=True
  3. Relevance       — question text relates to skill/subject (keyword match)

Master function validate_pre_serve() runs all checks, returns ValidationResult,
and logs failures asynchronously to MongoDB.
"""

import logging
import math
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

DISPLAY_ONLY_TYPES = {"image", "definition"}

SCOREABLE_TYPES = {
    "radio", "numeric-input", "dropdown", "expression",
    "orderer", "matcher", "sorter", "categorizer",
    "number-line", "table",
}


@dataclass
class CheckResult:
    """Result of a single validation check."""
    passed: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Aggregate result of all pre-serve validation checks."""
    passed: bool = True
    checks_run: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    question_id: str = ""
    skill_id: str = ""


# ---------------------------------------------------------------------------
# Expression normalization (faithful port of frontend deepNormalize)
# ---------------------------------------------------------------------------

_RE_WHITESPACE = re.compile(r"\s+")
_RE_UNICODE_MULT = re.compile(r"[\u00d7\u00b7]")
_RE_LATEX_WRAP = re.compile(r"\\(?:text|mathrm|mathit)\{([^}]*)\}")
_RE_FRAC = re.compile(r"\\frac\{([^}]*)\}\{([^}]*)\}")
_RE_LATEX_MULT = re.compile(r"\\(?:cdot|times)")
_RE_GROUPING_BRACES = re.compile(r"\{([^{}]+)\}")
_RE_TRIVIAL_PARENS = re.compile(r"\((\w+)\)")
_RE_SIMPLE_EXP = re.compile(r"(\d+)\^(\d+)")
_RE_SIMPLE_DIV = re.compile(r"^\d+/\d+$")
_RE_SPLIT_ADDITIVE = re.compile(r"(?=[+-])")


def deep_normalize(s: str) -> str:
    """Port of frontend deepNormalize() from scoring-utils.ts."""
    n = _RE_WHITESPACE.sub("", s).lower()
    n = _RE_UNICODE_MULT.sub("*", n)
    n = _RE_LATEX_WRAP.sub(r"\1", n)
    n = _RE_FRAC.sub(r"(\1)/(\2)", n)
    n = _RE_LATEX_MULT.sub("*", n)
    # Remove grouping braces (loop for nested)
    while _RE_GROUPING_BRACES.search(n):
        n = _RE_GROUPING_BRACES.sub(r"\1", n)
    # Strip trivial parentheses around single tokens
    while _RE_TRIVIAL_PARENS.search(n):
        n = _RE_TRIVIAL_PARENS.sub(r"\1", n)
    # Evaluate simple integer exponents: 2^3 -> 8
    def _eval_exp(m):
        base, exp = int(m.group(1)), int(m.group(2))
        result = base ** exp
        return str(result) if isinstance(result, int) and result < 1_000_000 else m.group(0)
    n = _RE_SIMPLE_EXP.sub(_eval_exp, n)
    # Evaluate simple integer division when it's the entire expression
    if _RE_SIMPLE_DIV.match(n):
        num_s, den_s = n.split("/")
        num, den = int(num_s), int(den_s)
        if den != 0 and num % den == 0:
            n = str(num // den)
    # Sort additive terms for commutativity (only pure addition)
    terms = [t for t in _RE_SPLIT_ADDITIVE.split(n) if t]
    if len(terms) > 1:
        has_sub = any(t.startswith("-") for t in terms)
        has_mult = any("*" in t or "^" in t for t in terms)
        if not has_sub and not has_mult and "(" not in n and "/" not in n:
            normalized = [
                t if t.startswith("+") or t.startswith("-") else "+" + t
                for t in terms
            ]
            n = "".join(sorted(normalized)).lstrip("+")
    return n


# ---------------------------------------------------------------------------
# 1. Answerability check
# ---------------------------------------------------------------------------

def validate_answerability(question_data: dict) -> CheckResult:
    """Verify every scoreable widget has a valid correct answer defined."""
    reasons: List[str] = []

    question = question_data.get("question")
    if not isinstance(question, dict):
        return CheckResult(passed=False, reasons=["no 'question' dict in question_data"])

    widgets = question.get("widgets")
    if not isinstance(widgets, dict) or len(widgets) == 0:
        return CheckResult(passed=False, reasons=["no widgets found"])

    content = question.get("content", "")
    if not isinstance(content, str) or len(content.strip()) < 5:
        reasons.append("question content is empty or too short")

    scoreable_count = 0

    for wid, wdef in widgets.items():
        if not isinstance(wdef, dict):
            continue
        wtype = wdef.get("type", "")
        if wtype in DISPLAY_ONLY_TYPES:
            continue
        if wtype not in SCOREABLE_TYPES:
            # Unknown widget type — not necessarily a failure, skip
            continue

        opts = wdef.get("options") or {}
        scoreable_count += 1

        if wtype == "radio":
            choices = opts.get("choices", [])
            if not isinstance(choices, list) or len(choices) < 2:
                reasons.append(f"{wid}: radio has <2 choices")
                continue
            correct_count = sum(1 for c in choices if c.get("correct"))
            if correct_count == 0:
                reasons.append(f"{wid}: radio has no correct choice")

        elif wtype == "numeric-input":
            answers = opts.get("answers", [])
            if not isinstance(answers, list) or len(answers) == 0:
                reasons.append(f"{wid}: numeric-input has no answers")
                continue
            correct = [a for a in answers if a.get("status") == "correct"]
            if not correct:
                reasons.append(f"{wid}: numeric-input has no correct answer")
            elif not isinstance(correct[0].get("value"), (int, float)):
                reasons.append(f"{wid}: numeric-input correct answer has no numeric value")

        elif wtype == "dropdown":
            choices = opts.get("choices", [])
            if not isinstance(choices, list) or len(choices) < 2:
                reasons.append(f"{wid}: dropdown has <2 choices")
                continue
            correct_count = sum(1 for c in choices if c.get("correct"))
            if correct_count == 0:
                reasons.append(f"{wid}: dropdown has no correct choice")

        elif wtype == "expression":
            forms = opts.get("answerForms", [])
            if not isinstance(forms, list) or len(forms) == 0:
                reasons.append(f"{wid}: expression has no answerForms")
                continue
            correct = [f for f in forms if f.get("considered") == "correct"]
            if not correct:
                reasons.append(f"{wid}: expression has no correct answerForm")
            elif not correct[0].get("value"):
                reasons.append(f"{wid}: expression correct form has empty value")

        elif wtype == "orderer":
            correct_opts = opts.get("correctOptions", [])
            if not isinstance(correct_opts, list) or len(correct_opts) < 2:
                reasons.append(f"{wid}: orderer has <2 correctOptions")

        elif wtype == "matcher":
            left = opts.get("left", [])
            right = opts.get("right", [])
            if not isinstance(left, list) or not isinstance(right, list):
                reasons.append(f"{wid}: matcher missing left/right arrays")
            elif len(left) < 2 or len(right) < 2:
                reasons.append(f"{wid}: matcher has <2 items")
            elif len(left) != len(right):
                reasons.append(f"{wid}: matcher left/right length mismatch")

        elif wtype == "sorter":
            correct = opts.get("correct", [])
            if not isinstance(correct, list) or len(correct) < 2:
                reasons.append(f"{wid}: sorter has <2 correct items")

        elif wtype == "categorizer":
            items = opts.get("items", [])
            categories = opts.get("categories", [])
            values = opts.get("values", [])
            if not items or not categories or not values:
                reasons.append(f"{wid}: categorizer missing items/categories/values")
            elif len(values) != len(items):
                reasons.append(f"{wid}: categorizer values length != items length")
            elif any(not isinstance(v, int) or v < 0 or v >= len(categories) for v in values):
                reasons.append(f"{wid}: categorizer has invalid value indices")

        elif wtype == "number-line":
            correct_x = opts.get("correctX")
            if not isinstance(correct_x, (int, float)):
                reasons.append(f"{wid}: number-line has no numeric correctX")
            else:
                rng = opts.get("range", [])
                if isinstance(rng, list) and len(rng) == 2:
                    if correct_x < rng[0] or correct_x > rng[1]:
                        reasons.append(f"{wid}: number-line correctX outside range")

        elif wtype == "table":
            answers = opts.get("answers", [])
            if not isinstance(answers, list) or len(answers) == 0:
                reasons.append(f"{wid}: table has no answers")
            elif any(not isinstance(row, list) or len(row) == 0 for row in answers):
                reasons.append(f"{wid}: table has empty answer rows")

    if scoreable_count == 0:
        reasons.append("no scoreable widgets found")

    return CheckResult(passed=len(reasons) == 0, reasons=reasons)


# ---------------------------------------------------------------------------
# 2. Dry-run scoring (Python port of frontend scorePerseusQuestion)
# ---------------------------------------------------------------------------

def _build_mock_input(wtype: str, opts: dict) -> Optional[dict]:
    """Build the 'perfect' user input for a widget from its answer definition.
    Returns None for display-only widgets. Returns empty dict if can't build input.
    """
    if wtype in DISPLAY_ONLY_TYPES:
        return None

    if wtype == "radio":
        choices = opts.get("choices", [])
        is_multi = opts.get("multipleSelect", False)
        correct_indices = [i for i, c in enumerate(choices) if c.get("correct")]
        if not correct_indices:
            return {}
        if is_multi:
            return {"selectedChoiceIds": [f"choice-{i}" for i in correct_indices]}
        else:
            # Single-select: pick only the first correct choice
            return {"selectedChoiceIds": [f"choice-{correct_indices[0]}"]}

    elif wtype == "numeric-input":
        answers = opts.get("answers", [])
        correct = next((a for a in answers if a.get("status") == "correct"), None)
        if not correct or not isinstance(correct.get("value"), (int, float)):
            return {}
        return {"currentValue": str(correct["value"])}

    elif wtype == "dropdown":
        choices = opts.get("choices", [])
        correct_idx = next((i for i, c in enumerate(choices) if c.get("correct")), None)
        if correct_idx is None:
            return {}
        return {"value": correct_idx}

    elif wtype == "expression":
        forms = opts.get("answerForms", [])
        correct = next((f for f in forms if f.get("considered") == "correct"), None)
        if not correct or not correct.get("value"):
            return {}
        return {"currentValue": correct["value"]}

    elif wtype == "orderer":
        correct_opts = opts.get("correctOptions", [])
        return {"current": correct_opts} if correct_opts else {}

    elif wtype == "matcher":
        right = opts.get("right", [])
        return {"right": right} if right else {}

    elif wtype == "sorter":
        correct = opts.get("correct", [])
        return {"options": correct} if correct else {}

    elif wtype == "categorizer":
        values = opts.get("values", [])
        return {"values": values} if values else {}

    elif wtype == "number-line":
        correct_x = opts.get("correctX")
        if isinstance(correct_x, (int, float)):
            return {"numLinePosition": correct_x}
        return {}

    elif wtype == "table":
        answers = opts.get("answers", [])
        return {"answers": answers} if answers else {}

    return {}


def _score_widget(wtype: str, opts: dict, user_input: dict) -> bool:
    """Score a single widget given its definition and user input.
    Faithfully ports the frontend scoring-utils.ts logic.
    """
    if wtype == "radio":
        choices = opts.get("choices", [])
        selected_ids = user_input.get("selectedChoiceIds", [])
        is_multi = opts.get("multipleSelect", False)
        if is_multi:
            correct_indices = {i for i, c in enumerate(choices) if c.get("correct")}
            selected_indices = set()
            for sid in selected_ids:
                m = re.match(r"choice-(\d+)", sid)
                if m:
                    selected_indices.add(int(m.group(1)))
            return correct_indices == selected_indices
        else:
            if len(selected_ids) == 1:
                m = re.match(r"choice-(\d+)", selected_ids[0])
                if m:
                    idx = int(m.group(1))
                    return bool(choices[idx].get("correct")) if idx < len(choices) else False
        return False

    elif wtype == "numeric-input":
        answers = opts.get("answers", [])
        raw = user_input.get("currentValue", "")
        try:
            user_val = float(raw)
        except (ValueError, TypeError):
            return False
        correct = next((a for a in answers if a.get("status") == "correct"), None)
        if not correct:
            return False
        max_error = correct.get("maxError")
        if max_error is None or max_error <= 0:
            cv = correct["value"]
            if cv == 0:
                max_error = 0.001
            else:
                max_error = max(0.01, abs(cv) * 0.01)
        return abs(user_val - correct["value"]) <= max_error

    elif wtype == "dropdown":
        choices = opts.get("choices", [])
        selected_idx = user_input.get("value")
        if selected_idx is None:
            selected_idx = user_input.get("selected")
        if selected_idx is not None and 0 <= selected_idx < len(choices):
            return bool(choices[selected_idx].get("correct"))
        return False

    elif wtype == "expression":
        forms = opts.get("answerForms", [])
        if isinstance(user_input, str):
            raw = user_input
        else:
            raw = user_input.get("currentValue", "")
        if not raw or not raw.strip():
            return False
        user_norm = deep_normalize(raw)
        return any(
            f.get("considered") == "correct" and deep_normalize(f.get("value", "")) == user_norm
            for f in forms
        )

    elif wtype == "orderer":
        correct_opts = opts.get("correctOptions", [])
        user_order = user_input.get("current", [])
        if len(correct_opts) != len(user_order):
            return False
        for co, uo in zip(correct_opts, user_order):
            cc = (co if isinstance(co, str) else co.get("content", "")).strip()
            uc = (uo if isinstance(uo, str) else uo.get("content", "")).strip()
            if cc != uc:
                return False
        return True

    elif wtype == "matcher":
        correct_right = opts.get("right", [])
        user_right = user_input.get("right", [])
        if len(correct_right) == 0 or len(correct_right) != len(user_right):
            return False
        return all(c == u for c, u in zip(correct_right, user_right))

    elif wtype == "sorter":
        correct_order = opts.get("correct", [])
        user_order = user_input.get("options") or user_input.get("current", [])
        if len(correct_order) == 0 or len(correct_order) != len(user_order):
            return False
        return all(
            (c if isinstance(c, str) else "").strip() == (u if isinstance(u, str) else "").strip()
            for c, u in zip(correct_order, user_order)
        )

    elif wtype == "categorizer":
        correct_values = opts.get("values", [])
        user_values = user_input.get("values", [])
        if len(correct_values) == 0 or len(correct_values) != len(user_values):
            return False
        return all(
            uv is not None and cv == uv
            for cv, uv in zip(correct_values, user_values)
        )

    elif wtype == "number-line":
        correct_x = opts.get("correctX")
        correct_rel = opts.get("correctRel", "eq")
        user_x = user_input.get("numLinePosition")
        if correct_x is None or user_x is None:
            return False
        snap = opts.get("snapDivisions", 2)
        tick = opts.get("tickStep", 1)
        tol = tick / snap / 2
        if correct_rel == "eq":
            return abs(user_x - correct_x) <= tol
        elif correct_rel == "lt":
            return user_x < correct_x
        elif correct_rel == "gt":
            return user_x > correct_x
        elif correct_rel == "le":
            return user_x <= correct_x + tol
        elif correct_rel == "ge":
            return user_x >= correct_x - tol
        elif correct_rel == "ne":
            return abs(user_x - correct_x) > tol
        return abs(user_x - correct_x) <= tol

    elif wtype == "table":
        correct_answers = opts.get("answers", [])
        user_answers = user_input.get("answers", [])
        if len(correct_answers) == 0 or len(correct_answers) != len(user_answers):
            return False
        for crow, urow in zip(correct_answers, user_answers):
            if not isinstance(crow, list) or not isinstance(urow, list):
                return False
            if len(crow) != len(urow):
                return False
            for cc, uc in zip(crow, urow):
                cc_s = str(cc).strip()
                uc_s = str(uc).strip()
                try:
                    if abs(float(uc_s) - float(cc_s)) < 0.01:
                        continue
                except (ValueError, TypeError):
                    pass
                if uc_s.lower() != cc_s.lower():
                    return False
        return True

    return False


def dry_run_score(question_data: dict) -> CheckResult:
    """Construct mock 'perfect' input and run scoring. Question must score correct."""
    reasons: List[str] = []
    question = question_data.get("question")
    if not isinstance(question, dict):
        return CheckResult(passed=False, reasons=["no 'question' dict"])

    widgets = question.get("widgets")
    if not isinstance(widgets, dict):
        return CheckResult(passed=False, reasons=["no widgets dict"])

    scoreable_count = 0
    correct_count = 0

    for wid, wdef in widgets.items():
        if not isinstance(wdef, dict):
            continue
        wtype = wdef.get("type", "")
        if wtype in DISPLAY_ONLY_TYPES:
            continue
        if wtype not in SCOREABLE_TYPES:
            continue

        opts = wdef.get("options") or {}
        mock_input = _build_mock_input(wtype, opts)
        if mock_input is None:
            continue  # display-only
        if not mock_input:
            reasons.append(f"{wid}: cannot build mock input for {wtype}")
            scoreable_count += 1
            continue

        scoreable_count += 1
        if _score_widget(wtype, opts, mock_input):
            correct_count += 1
        else:
            reasons.append(f"{wid}: dry-run scoring returned incorrect for {wtype}")

    if scoreable_count == 0:
        reasons.append("scoreableCount is 0")

    passed = scoreable_count > 0 and correct_count == scoreable_count and len(reasons) == 0
    return CheckResult(passed=passed, reasons=reasons)


# ---------------------------------------------------------------------------
# 3. Relevance check
# ---------------------------------------------------------------------------

_RE_PERSEUS_WIDGETS = re.compile(r"\[\[.*?\]\]")
_RE_HTML_TAGS = re.compile(r"<[^>]+>")
_STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
    "was", "one", "our", "out", "has", "had", "this", "that", "with",
    "from", "have", "what", "which", "their", "will", "each", "about",
    "how", "they", "been", "some", "when", "into", "than", "other",
    "its", "also", "after", "use", "two", "way", "would", "like",
    "grade", "question", "answer", "following", "below", "above",
}


def _extract_text(question_data: dict) -> str:
    """Extract all readable text from question content + choice labels."""
    parts: List[str] = []
    q = question_data.get("question", {})
    content = q.get("content", "")
    # Strip Perseus widget placeholders and HTML
    content = _RE_PERSEUS_WIDGETS.sub(" ", content)
    content = _RE_HTML_TAGS.sub(" ", content)
    parts.append(content)

    # Extract choice text from radio/dropdown widgets
    widgets = q.get("widgets", {})
    for wdef in widgets.values():
        if not isinstance(wdef, dict):
            continue
        opts = wdef.get("options", {})
        for choice in opts.get("choices", []):
            if isinstance(choice, dict):
                parts.append(choice.get("content", ""))
        # Matcher left/right
        for item in opts.get("left", []):
            parts.append(str(item) if not isinstance(item, dict) else item.get("content", ""))
        for item in opts.get("right", []):
            parts.append(str(item) if not isinstance(item, dict) else item.get("content", ""))
        # Sorter/orderer items
        for item in opts.get("correct", []):
            parts.append(str(item))
        for item in opts.get("correctOptions", []):
            parts.append(str(item) if not isinstance(item, dict) else item.get("content", ""))

    return " ".join(parts).lower()


def _is_hex_like(token: str) -> bool:
    """Check if a token looks like a hex hash (not a real word)."""
    clean = token.lstrip("x")
    return len(clean) >= 4 and all(c in "0123456789abcdef" for c in clean)


def _skill_keywords(skill_id: str) -> set:
    """Split skill_id into meaningful keywords."""
    # Split on underscores, hyphens, spaces, colons, and digits-only tokens
    tokens = re.split(r"[_\-\s:,/]+", skill_id.lower())
    return {
        t for t in tokens
        if len(t) >= 3 and t not in _STOP_WORDS and not _is_hex_like(t)
        and not t.isdigit()
    }


def validate_relevance(question_data: dict, skill_id: str, subject: str) -> CheckResult:
    """Check that question text relates to the skill/subject via keyword matching."""
    reasons: List[str] = []

    if not skill_id and not subject:
        return CheckResult(passed=True)

    text = _extract_text(question_data)
    if len(text.strip()) < 50:
        # Too little text to judge relevance — pass
        return CheckResult(passed=True)

    # Check skill keywords (use stem matching: keyword[:4] substring match)
    if skill_id:
        keywords = _skill_keywords(skill_id)
        if keywords:
            # Lenient: a keyword matches if its first 4+ chars appear as substring in text
            found = any(
                kw in text or (len(kw) >= 4 and kw[:4] in text)
                for kw in keywords
            )
            if not found:
                reasons.append(f"no skill keywords ({', '.join(sorted(keywords)[:5])}) found in question text")

    return CheckResult(passed=len(reasons) == 0, reasons=reasons)


# ---------------------------------------------------------------------------
# 4. Meta-question detection
# ---------------------------------------------------------------------------

# Patterns that indicate a generic "about the topic" meta-question rather than
# a question that actually tests subject knowledge.
_META_QUESTION_PATTERNS = [
    re.compile(r"which\s+(?:of\s+the\s+following\s+)?(?:is|are)\s+true\s+about", re.I),
    re.compile(r"which\s+(?:of\s+the\s+following\s+)?(?:statement|description)s?\s+(?:is|are)\s+(?:most\s+)?(?:true|accurate|correct)\s+about", re.I),
    re.compile(r"which\s+(?:best\s+)?describes?\s+(?:the\s+)?(?:study|field|subject|topic|area)\s+of", re.I),
    re.compile(r"(?:can\s+only\s+be\s+learned\s+by\s+watching\s+tv)", re.I),
    re.compile(r"(?:has\s+nothing\s+to\s+do\s+with\s+thinking)", re.I),
    re.compile(r"(?:nobody\s+studies\s+.+\s+in\s+school)", re.I),
    re.compile(r"involves\s+learning\s+and\s+practicing\s+specific\s+skills", re.I),
]

# Boilerplate distractor patterns that appear in meta-questions
_META_DISTRACTOR_PATTERNS = [
    re.compile(r"can\s+only\s+be\s+learned\s+by\s+watching", re.I),
    re.compile(r"has\s+nothing\s+to\s+do\s+with", re.I),
    re.compile(r"nobody\s+(?:studies|learns|teaches)", re.I),
    re.compile(r"is\s+not\s+(?:a\s+)?(?:real|important|useful)\s+(?:subject|topic|field)", re.I),
]


def validate_not_meta_question(question_data: dict) -> CheckResult:
    """Reject generic meta-questions that describe a topic instead of testing knowledge."""
    text = _extract_text(question_data)

    # Check question content for meta-question patterns
    for pat in _META_QUESTION_PATTERNS:
        if pat.search(text):
            return CheckResult(
                passed=False,
                reasons=[f"meta-question detected: matches pattern '{pat.pattern[:60]}'"],
            )

    # Check if 2+ distractor choices match boilerplate meta-patterns
    distractor_hits = sum(1 for pat in _META_DISTRACTOR_PATTERNS if pat.search(text))
    if distractor_hits >= 2:
        return CheckResult(
            passed=False,
            reasons=[f"meta-question detected: {distractor_hits} boilerplate distractor patterns found"],
        )

    return CheckResult(passed=True)


# ---------------------------------------------------------------------------
# Async failure logging
# ---------------------------------------------------------------------------

def _log_failure_async(db_collection, result: "ValidationResult", question_data: dict):
    """Fire-and-forget MongoDB insert for validation failures."""
    def _insert():
        try:
            db_collection.insert_one({
                "question_id": result.question_id,
                "skill_id": result.skill_id,
                "checks_run": result.checks_run,
                "failures": result.failures,
                "elapsed_ms": result.elapsed_ms,
                "question_content_preview": str(
                    question_data.get("question", {}).get("content", "")
                )[:500],
                "timestamp": datetime.utcnow(),
            })
        except Exception as e:
            logger.warning(f"[PRE_SERVE] Failure logging error (non-fatal): {e}")

    threading.Thread(target=_insert, daemon=True).start()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _extract_question_id(question_data) -> str:
    """Best-effort extraction of question ID from question data."""
    if not isinstance(question_data, dict):
        return ""
    if "question_id" in question_data:
        return str(question_data["question_id"])
    dm = question_data.get("dash_metadata", {})
    if isinstance(dm, dict) and "dash_question_id" in dm:
        return str(dm["dash_question_id"])
    return ""


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def validate_pre_serve(
    question_data: dict,
    skill_id: Optional[str] = None,
    subject: Optional[str] = None,
    db_collection=None,
) -> ValidationResult:
    """Run all pre-serve validation checks.

    Fail-open: if the validator itself errors, pass the question through.
    """
    start = time.monotonic()

    try:
        result = ValidationResult(
            question_id=_extract_question_id(question_data),
            skill_id=skill_id or "",
        )

        # Check 1: Answerability
        ans = validate_answerability(question_data)
        result.checks_run.append("answerability")
        if not ans.passed:
            result.failures.extend(f"[answerability] {r}" for r in ans.reasons)

        # Check 2: Dry-run scoring
        score = dry_run_score(question_data)
        result.checks_run.append("dry_run_score")
        if not score.passed:
            result.failures.extend(f"[dry_run_score] {r}" for r in score.reasons)

        # Check 3: Relevance
        if skill_id or subject:
            rel = validate_relevance(question_data, skill_id or "", subject or "")
            result.checks_run.append("relevance")
            if not rel.passed:
                result.failures.extend(f"[relevance] {r}" for r in rel.reasons)

        # Check 4: Meta-question detection
        meta = validate_not_meta_question(question_data)
        result.checks_run.append("meta_question")
        if not meta.passed:
            result.failures.extend(f"[meta_question] {r}" for r in meta.reasons)

        result.passed = len(result.failures) == 0

    except Exception as e:
        logger.error(f"[PRE_SERVE] Validator internal error (fail-open): {e}")
        result = ValidationResult(passed=True)
        result.checks_run.append("error_failopen")

    result.elapsed_ms = round((time.monotonic() - start) * 1000, 2)

    if not result.passed:
        logger.warning(f"[PRE_SERVE] REJECT {result.question_id}: {result.failures}")
        if db_collection is not None:
            _log_failure_async(db_collection, result, question_data)

    return result
