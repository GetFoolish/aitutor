"""
Deterministic Question Verifier — Axiom-inspired generate→verify→refine pipeline.

Provides subject-aware algorithmic verification for AI-generated questions.
No LLM calls — verification is fully deterministic using SymPy (math),
curated fact databases (science, history), and language rules (english).

Usage:
    verifier = DeterministicVerifier()
    result = verifier.verify(item, skill_name, lesson_name, fmt, age, difficulty)
    if not result.passed:
        # Inject result.failures into next generation prompt
"""

import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from shared.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    passed: bool
    subject: str                        # "math", "science", "english", "history", "geography", "economics", "civics", "computer_science", "art_history", "music", "health", "social_studies", "unknown"
    checks_run: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    confidence: float = 0.5             # 0.0–1.0
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# Subject keyword sets (for detection)
# ---------------------------------------------------------------------------

_SUBJECT_KEYWORDS: Dict[str, frozenset] = {
    "math": frozenset({
        "math", "arithmetic", "algebra", "geometry", "calculus", "fraction",
        "decimal", "equation", "polynomial", "number", "multiply", "divide",
        "add", "subtract", "percent", "ratio", "proportion", "exponent",
        "factor", "statistics", "probability", "trigonometry", "measurement",
        "integer", "prime", "square root", "area", "perimeter", "volume",
        "counting", "place value", "rounding", "estimation",
        # Curriculum skill names that should route to math
        "addition", "subtraction", "multiplication", "division",
        "data analysis", "graph", "function", "radical", "logarithm",
        "exponential", "linear", "quadratic", "inequalit", "coordinate",
        "angle", "circle", "triangle", "polygon", "congruent", "symmetry",
        "2nd-grade-math", "3rd-grade-math", "4th-grade-math", "5th-grade-math",
        "6th-grade-math", "7th-grade-math", "8th-grade-math",
        "grade-math", "pre-algebra", "precalculus",
    }),
    "science": frozenset({
        "science", "biology", "physics", "chemistry", "astronomy",
        "organism", "cell", "ecosystem", "force", "energy", "circuit",
        "planet", "solar system", "weather", "atom", "molecule",
        "experiment", "hypothesis", "evolution", "gravity", "element",
        "compound", "reaction", "photosynthesis", "genetics", "habitat",
        "climate", "human body", "organ", "species", "motion",
    }),
    "english": frozenset({
        "grammar", "vocabulary", "reading", "writing", "literature",
        "english", "spelling", "punctuation", "poetry", "comprehension",
        "sentence", "noun", "verb", "adjective", "adverb", "pronoun",
        "prefix", "suffix", "synonym", "antonym", "phonics", "rhyme",
        "homophone", "metaphor", "simile", "language arts",
    }),
    "history": frozenset({
        "history", "social studies", "war", "revolution", "president",
        "ancient", "medieval", "colonial", "independence", "civil rights",
        "civilization", "empire", "dynasty", "treaty", "world war",
        "founding fathers", "civil war", "cold war", "slavery",
    }),
    "economics": frozenset({
        "economics", "economy", "supply", "demand", "market", "inflation",
        "gdp", "trade", "finance", "budget", "investment", "tax",
        "monetary", "fiscal", "scarcity", "opportunity cost", "capitalism",
        "socialism", "stock", "banking", "interest rate", "unemployment",
        "consumer", "producer", "profit", "microeconomics", "macroeconomics",
        "personal finance", "credit", "saving",
    }),
    "civics": frozenset({
        "civics", "government", "constitution", "democracy", "election",
        "voting", "rights", "congress", "senate", "judicial", "executive",
        "legislative", "amendment", "bill of rights", "supreme court",
        "citizenship", "law", "republic", "political", "civic",
        "branches of government", "checks and balances",
    }),
    "geography": frozenset({
        "geography", "continent", "ocean", "map", "country", "capital",
        "latitude", "longitude", "climate zone", "landform", "population",
        "region", "hemisphere", "equator", "mountain", "river", "desert",
        "island", "peninsula", "plateau", "border", "territory",
        "topography", "cartography", "compass", "scale",
    }),
    "computer_science": frozenset({
        "computer", "programming", "algorithm", "code", "coding",
        "data structure", "binary", "internet", "cybersecurity", "variable",
        "function", "loop", "array", "software", "hardware", "database",
        "html", "css", "javascript", "python", "scratch", "encryption",
        "boolean", "debugging", "compiler", "web", "network",
    }),
    "art_history": frozenset({
        "art history", "painting", "sculpture", "artist", "museum",
        "impressionism", "renaissance", "cubism", "abstract", "portrait",
        "color theory", "art movement", "gallery", "canvas", "sketch",
        "pottery", "mosaic", "architecture", "baroque", "surrealism",
        "expressionism", "pop art", "art elements", "perspective",
    }),
    "music": frozenset({
        "music", "rhythm", "melody", "harmony", "tempo", "pitch",
        "note", "chord", "scale", "octave", "treble", "bass",
        "orchestra", "instrument", "composer", "symphony", "opera",
        "jazz", "classical music", "musical", "beat", "measure",
        "staff", "clef", "key signature", "time signature",
        "dynamics", "forte", "piano", "sonata",
    }),
    "health": frozenset({
        "health", "nutrition", "exercise", "fitness", "diet", "vitamin",
        "mineral", "calorie", "protein", "carbohydrate", "fat", "hygiene",
        "immune", "vaccine", "disease", "mental health", "stress",
        "anxiety", "self-esteem", "sleep", "body system", "muscle",
        "aerobic", "physical education", "wellness", "first aid",
        "food group", "MyPlate",
    }),
    "social_studies": frozenset({
        "culture", "religion", "human rights", "United Nations",
        "global", "world religion", "Buddhism", "Christianity",
        "Islam", "Judaism", "Hinduism", "diversity", "tradition",
        "heritage", "society", "community", "civil liberties",
        "humanitarian", "refugee", "international law",
    }),
}


# ---------------------------------------------------------------------------
# Base verifier
# ---------------------------------------------------------------------------

class SubjectVerifier(ABC):
    @abstractmethod
    def verify(self, item: Dict, fmt: str, age: int, difficulty: float,
               skill_name: str, lesson_name: str) -> VerificationResult:
        ...

    # -- helpers shared across verifiers --

    @staticmethod
    def _extract_correct_answer_text(item: Dict, fmt: str) -> str:
        """Return the text of the correct answer for radio/dropdown/matcher."""
        widgets = item.get("question", {}).get("widgets", {})
        for w in widgets.values():
            wtype = w.get("type", "")
            opts = w.get("options", {})
            if wtype == "radio":
                for ch in opts.get("choices", []):
                    if ch.get("correct"):
                        return ch.get("content", "")
            elif wtype == "dropdown":
                for ch in opts.get("choices", []):
                    if ch.get("correct"):
                        return ch.get("content", "")
            elif wtype == "numeric-input":
                for a in opts.get("answers", []):
                    if a.get("status") == "correct":
                        return str(a.get("value", ""))
            elif wtype == "expression":
                for af in opts.get("answerForms", []):
                    if af.get("considered") == "correct":
                        return str(af.get("value", ""))
            elif wtype == "matcher":
                left = opts.get("left", [])
                right = opts.get("right", [])
                if left and right:
                    return json.dumps({"left": left, "right": right})
            elif wtype == "sorter":
                correct = opts.get("correct", opts.get("correctOptions", []))
                if correct:
                    return json.dumps({"correct_order": correct})
            elif wtype == "orderer":
                correct = opts.get("correctOptions", opts.get("correct", []))
                if correct:
                    return json.dumps({"correct_order": correct})
        return ""

    _STOP_WORDS = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "it", "its",
        "or", "and", "but", "if", "not", "no", "so", "up", "out", "that",
        "this", "what", "which", "who", "how", "when", "where", "than",
        # Filler words common in skill names but not in question text
        "intro", "introduction", "basics", "overview", "practice", "review",
        "module", "unit", "lesson", "part", "advanced", "beginning",
    })

    # Synonym map: skill keyword → words/symbols that prove the topic is covered
    _TOPIC_SYNONYMS = {
        # Math operations
        "addition": {"add", "adding", "sum", "plus", "total", "combine", "altogether"},
        "subtraction": {"subtract", "subtracting", "minus", "difference", "fewer", "left", "remain", "away"},
        "multiplication": {"multiply", "multiplying", "times", "product", "groups"},
        "division": {"divide", "dividing", "quotient", "split", "shared", "equally"},
        "fractions": {"fraction", "numerator", "denominator", "half", "quarter", "third", "whole"},
        "decimals": {"decimal", "tenths", "hundredths", "point"},
        "equations": {"equation", "solve", "variable", "equals"},
        "geometry": {"shape", "triangle", "circle", "square", "rectangle", "angle", "polygon", "area", "perimeter"},
        "algebra": {"variable", "expression", "equation", "solve", "simplify", "factor"},
        "trigonometry": {"sine", "cosine", "tangent", "angle", "hypotenuse", "opposite", "adjacent"},
        "statistics": {"mean", "median", "mode", "average", "data", "graph", "probability"},
        "measurement": {"measure", "length", "width", "height", "weight", "volume", "capacity"},
        "counting": {"count", "number", "many", "few", "more", "less"},
        "patterns": {"pattern", "sequence", "next", "rule", "repeat"},
        # Science
        "photosynthesis": {"sunlight", "chlorophyll", "oxygen", "glucose", "plant"},
        "evolution": {"selection", "species", "adapt", "mutation", "fossil", "trait"},
        "gravity": {"force", "weight", "fall", "attract", "mass", "newton"},
        "electricity": {"circuit", "current", "voltage", "battery", "wire", "charge"},
        # English
        "grammar": {"noun", "verb", "adjective", "adverb", "sentence", "subject", "predicate"},
        "vocabulary": {"word", "meaning", "definition", "synonym", "antonym"},
        "reading": {"passage", "text", "read", "comprehension", "author"},
        "writing": {"write", "essay", "paragraph", "sentence", "topic"},
        "phonics": {"sound", "letter", "blend", "syllable", "vowel", "consonant", "rhyme"},
        # History
        "revolution": {"revolt", "independence", "colony", "uprising", "overthrow"},
        "civilization": {"empire", "dynasty", "kingdom", "society", "culture", "ancient"},
        "government": {"democracy", "republic", "constitution", "law", "congress", "president"},
    }

    # Math symbols that prove a math topic is being tested
    _MATH_SYMBOLS = {"+", "-", "×", "÷", "=", "*", "/", "<", ">", "≤", "≥"}

    @staticmethod
    def _check_multi_correct_radio(item: Dict) -> Optional[str]:
        """Detect multiple correct choices in a non-multiSelect radio widget."""
        widgets = item.get("question", {}).get("widgets", {})
        for w in widgets.values():
            wtype = w.get("type", "")
            if wtype == "radio":
                opts = w.get("options", {})
                multi_select = opts.get("multipleSelect", False)
                if not multi_select:
                    correct_count = sum(1 for ch in opts.get("choices", []) if ch.get("correct"))
                    if correct_count > 1:
                        return (
                            f"Radio widget has {correct_count} correct choices but "
                            f"multipleSelect is not enabled. Either enable multipleSelect "
                            f"or ensure exactly 1 choice is marked correct."
                        )
        return None

    @staticmethod
    def _fuzzy_contains(haystack: str, needle: str, threshold: int = 3) -> bool:
        """Check if needle appears in haystack with minor variation (ignoring stop words)."""
        h = haystack.lower().strip()
        n = needle.lower().strip()
        if n in h:
            return True
        # Word-overlap check excluding common stop words
        n_words = set(n.split()) - SubjectVerifier._STOP_WORDS
        h_words = set(h.split()) - SubjectVerifier._STOP_WORDS
        if not n_words:
            return False
        overlap = len(n_words & h_words)
        return overlap >= min(threshold, len(n_words))


# ---------------------------------------------------------------------------
# Math Verifier
# ---------------------------------------------------------------------------

class MathVerifier(SubjectVerifier):
    """Deterministic math verification via SymPy."""

    # Age-appropriate number ranges
    _AGE_MAX = {7: 100, 9: 1000, 13: 100000, 18: 1e12}

    def verify(self, item, fmt, age, difficulty, skill_name, lesson_name):
        t0 = time.time()
        checks, failures = [], []

        q_text = item.get("question", {}).get("content", "")
        widgets = item.get("question", {}).get("widgets", {})

        # Check 1: Numeric-input / expression answer computation
        for w in widgets.values():
            wtype = w.get("type", "")
            if wtype == "numeric-input":
                checks.append("answer_computation")
                ok = self._verify_numeric_input(w, q_text)
                if not ok:
                    failures.append(
                        "The computed answer does not match the stated correct answer. "
                        "Re-check the arithmetic in the question and provide the correct numerical answer."
                    )
            elif wtype == "expression":
                checks.append("expression_parseable")
                ok = self._verify_expression(w)
                if not ok:
                    failures.append(
                        "The expression answer contains invalid or unparseable LaTeX. "
                        "Ensure the answer is valid LaTeX that can be evaluated."
                    )

        # Check 2: Number range for age appropriateness
        checks.append("number_range")
        max_num = self._max_for_age(age)
        numbers = [float(m) for m in re.findall(r'(?<!\w)(\d+(?:\.\d+)?)(?!\w)', q_text)]
        oversized = [n for n in numbers if abs(n) > max_num and n != 0]
        if oversized:
            failures.append(
                f"Numbers {oversized[:3]} exceed the age-appropriate range "
                f"(max {int(max_num)} for age {age}). Use smaller numbers."
            )

        # Check 3: Distractor plausibility for radio/dropdown math
        if fmt in ("radio_single", "radio_multi", "dropdown"):
            checks.append("distractor_plausibility")
            dp_fail = self._check_distractors(item, fmt)
            if dp_fail:
                failures.append(dp_fail)

        elapsed = (time.time() - t0) * 1000
        return VerificationResult(
            passed=len(failures) == 0,
            subject="math",
            checks_run=checks,
            failures=failures,
            confidence=0.9 if fmt in ("numeric_input", "expression") else 0.75,
            elapsed_ms=elapsed,
        )

    def _max_for_age(self, age: int) -> float:
        for limit_age, limit_num in sorted(self._AGE_MAX.items()):
            if age <= limit_age:
                return limit_num
        return 1e12

    def _verify_numeric_input(self, widget: Dict, q_text: str) -> bool:
        """Verify numeric-input answer by extracting arithmetic from question text."""
        try:
            answers = widget.get("options", {}).get("answers", [])
            correct = next((a for a in answers if a.get("status") == "correct"), None)
            if not correct:
                return True
            stated = float(correct["value"])
            max_error = float(correct.get("maxError", 0.01))

            patterns = [
                # Symbol-based operators
                (r'[Ww]hat is\s+(\d+(?:\.\d+)?)\s*[\*x×]\s*(\d+(?:\.\d+)?)', lambda a, b: a * b),
                (r'[Ww]hat is\s+(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)', lambda a, b: a + b),
                (r'[Ww]hat is\s+(\d+(?:\.\d+)?)\s*[-−]\s*(\d+(?:\.\d+)?)', lambda a, b: a - b),
                (r'[Ww]hat is\s+(\d+(?:\.\d+)?)\s*[/÷]\s*(\d+(?:\.\d+)?)', lambda a, b: a / b if b else None),
                # Word-based operators
                (r'(\d+(?:\.\d+)?)\s+times\s+(\d+(?:\.\d+)?)', lambda a, b: a * b),
                (r'(\d+(?:\.\d+)?)\s+plus\s+(\d+(?:\.\d+)?)', lambda a, b: a + b),
                (r'(\d+(?:\.\d+)?)\s+minus\s+(\d+(?:\.\d+)?)', lambda a, b: a - b),
                (r'(\d+(?:\.\d+)?)\s+divided\s+by\s+(\d+(?:\.\d+)?)', lambda a, b: a / b if b else None),
                (r'(\d+(?:\.\d+)?)\s+multiplied\s+by\s+(\d+(?:\.\d+)?)', lambda a, b: a * b),
                # LaTeX operators
                (r'\$\s*(\d+(?:\.\d+)?)\s*\\times\s*(\d+(?:\.\d+)?)\s*\$', lambda a, b: a * b),
                (r'\$\s*(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s*\$', lambda a, b: a + b),
                (r'\$\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*\$', lambda a, b: a - b),
                (r'\$\s*\\frac\{(\d+(?:\.\d+)?)\}\{(\d+(?:\.\d+)?)\}\s*\$', lambda a, b: a / b if b else None),
                # Evaluate X when patterns
                (r'(\d+(?:\.\d+)?)\s*\+\s*\\blue\{(\d+(?:\.\d+)?)\}', lambda a, b: a + b),
                (r'\\blue\{(\d+(?:\.\d+)?)\}\s*\+\s*(\d+(?:\.\d+)?)', lambda a, b: a + b),
            ]
            for pat, op in patterns:
                m = re.search(pat, q_text)
                if m:
                    a, b = float(m.group(1)), float(m.group(2))
                    expected = op(a, b)
                    if expected is not None and abs(expected - stated) > max_error:
                        logger.warning(f"[MATH_VERIFY] numeric: computed={expected}, stated={stated}")
                        return False
                    return True

            # Try SymPy on $...$ LaTeX
            latex_m = re.search(r'\$([^$]+)\$', q_text)
            if latex_m:
                try:
                    from sympy.parsing.latex import parse_latex
                    expr = parse_latex(latex_m.group(1))
                    computed = float(expr.evalf())
                    if abs(computed - stated) > max_error:
                        logger.warning(f"[MATH_VERIFY] LaTeX: computed={computed}, stated={stated}")
                        return False
                    return True
                except Exception:
                    pass
            # No extractable arithmetic patterns found — fail-closed so the
            # question gets flagged for manual/LLM review rather than silently passing.
            return False
        except Exception:
            return True

    def _verify_expression(self, widget: Dict) -> bool:
        """Verify expression answer is valid parseable LaTeX."""
        try:
            from sympy.parsing.latex import parse_latex
            forms = widget.get("options", {}).get("answerForms", [])
            correct = next((f for f in forms if f.get("considered") == "correct"), None)
            if not correct or not correct.get("value"):
                return True
            parsed = parse_latex(correct["value"])
            return parsed is not None
        except Exception:
            return True  # Don't block on parse errors

    def _check_distractors(self, item: Dict, fmt: str) -> Optional[str]:
        """Check that radio/dropdown distractors are plausible for math."""
        widgets = item.get("question", {}).get("widgets", {})
        for w in widgets.values():
            wtype = w.get("type", "")
            if wtype in ("radio", "dropdown"):
                choices = w.get("options", {}).get("choices", [])
                # Try to extract numeric values from choices
                values = []
                for ch in choices:
                    nums = re.findall(r'[-−]?\d+(?:\.\d+)?', ch.get("content", ""))
                    if nums:
                        values.append(float(nums[0].replace("−", "-")))
                if len(values) >= 3:
                    correct_val = None
                    for ch, v in zip(choices, values):
                        if ch.get("correct"):
                            correct_val = v
                            break
                    if correct_val is not None:
                        # All distractors should be within 10x of correct (not random huge numbers)
                        for v in values:
                            if v != correct_val and correct_val != 0:
                                ratio = abs(v / correct_val) if correct_val else abs(v)
                                if ratio > 20:
                                    return (
                                        f"Distractor value {v} is implausibly far from correct answer "
                                        f"{correct_val}. Make distractors closer to the correct answer "
                                        f"(common mistake results)."
                                    )
        return None


# ---------------------------------------------------------------------------
# Generic Fact-DB Verifier (used by science, geography, CS, economics, etc.)
# ---------------------------------------------------------------------------

class FactDBVerifier(SubjectVerifier):
    """Generic fact-database verification for any subject with facts_by_topic structure."""

    # Synonym groups for normalizing directional/common words before matching
    _SYNONYMS = [
        ({"goes up", "increases", "rises", "grows", "higher", "more"}, "INCREASES"),
        ({"goes down", "decreases", "falls", "drops", "shrinks", "lower", "fewer", "less"}, "DECREASES"),
        ({"is the same", "stays the same", "remains the same", "unchanged", "equal"}, "UNCHANGED"),
        ({"largest", "biggest", "greatest", "most"}, "LARGEST"),
        ({"smallest", "least", "fewest", "lowest"}, "SMALLEST"),
    ]

    def __init__(self, subject_name: str, facts: Dict, confidence: float = 0.6):
        self._subject = subject_name
        self._facts = facts
        self._topics = facts.get("facts_by_topic", {})
        self._confidence = confidence

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Replace synonym phrases with canonical forms for better matching."""
        t = text.lower()
        for synonyms, canonical in cls._SYNONYMS:
            for syn in synonyms:
                t = t.replace(syn, canonical)
        return t

    @classmethod
    def _ordered_content_match(cls, haystack: str, needle: str, min_words: int = 3) -> bool:
        """Check if needle's content words appear as an ordered subsequence in haystack.
        Ignores stop words. Uses simple stemming for fuzzy word matching.
        Requires at least min_words content words to match."""
        stop = SubjectVerifier._STOP_WORDS

        def _stem(w: str) -> str:
            """Minimal stemming: demand/demanded/demands → demand."""
            s = w
            for suffix in ("ed", "ing", "tion", "s", "es", "ly"):
                if s.endswith(suffix) and len(s) - len(suffix) >= 3:
                    s = s[:-len(suffix)]
                    break
            return s

        needle_words = [w for w in needle.split() if w not in stop and len(w) > 1]
        hay_words = [w for w in haystack.split() if w not in stop and len(w) > 1]
        if len(needle_words) < min_words:
            return False
        # Build stemmed haystack for fuzzy matching
        hay_stems = [_stem(w) for w in hay_words]
        # Check ordered subsequence using stemmed comparison
        hi = 0
        matched = 0
        for nw in needle_words:
            nw_stem = _stem(nw)
            while hi < len(hay_stems):
                if hay_stems[hi] == nw_stem or hay_words[hi] == nw:
                    matched += 1
                    hi += 1
                    break
                hi += 1
        return matched >= len(needle_words)

    def verify(self, item, fmt, age, difficulty, skill_name, lesson_name):
        t0 = time.time()
        checks, failures = [], []
        q_text = item.get("question", {}).get("content", "").lower()
        correct_text = self._extract_correct_answer_text(item, fmt).lower()
        combined = f"{q_text} {correct_text}"

        matched_topic = self._match_topic(combined)

        # Check 1: Common errors (try both raw and normalized text)
        checks.append("common_error_check")
        if matched_topic:
            correct_context = f"{q_text} {correct_text}"
            norm_context = self._normalize(correct_context)
            for err in self._topics.get(matched_topic, {}).get("common_errors", []):
                err_wrong = err["wrong"].lower()
                norm_wrong = self._normalize(err_wrong)
                # Raw fuzzy match OR normalized ordered-subsequence match
                if (self._fuzzy_contains(correct_context, err_wrong, threshold=3) or
                        self._ordered_content_match(norm_context, norm_wrong)):
                    failures.append(
                        f"Correct answer matches known error: '{err['wrong']}'. "
                        f"The fact is: {err['correct']}. Fix the correct answer."
                    )

        # Check 2: Fact cross-reference (check for contradictions)
        if matched_topic:
            checks.append("fact_cross_reference")
            grade = self._age_to_grade(age)
            for fact in self._topics.get(matched_topic, {}).get("facts", []):
                if fact["grade_min"] <= grade <= fact["grade_max"]:
                    contradiction = self._check_contradiction(combined, fact["statement"].lower())
                    if contradiction:
                        failures.append(
                            f"Content may contradict known fact: '{fact['statement']}'. "
                            f"Verify the question and answer are factually accurate."
                        )

        # Check 3: Formula verification (only if formulas exist in the DB)
        formulas = self._facts.get("formulas", {})
        if formulas and fmt == "numeric_input":
            checks.append("formula_verification")
            for fname, fdata in formulas.items():
                if any(v in combined for v in fdata.get("variables", [])):
                    break

        elapsed = (time.time() - t0) * 1000
        return VerificationResult(
            passed=len(failures) == 0,
            subject=self._subject,
            checks_run=checks,
            failures=failures,
            confidence=self._confidence,
            elapsed_ms=elapsed,
        )

    def _match_topic(self, text: str) -> Optional[str]:
        best, best_score = None, 0
        for topic_key, topic_data in self._topics.items():
            kws = topic_data.get("keywords", [])
            score = sum(1 for kw in kws if kw in text)
            if score > best_score:
                best_score = score
                best = topic_key
        return best if best_score >= 1 else None

    @staticmethod
    def _age_to_grade(age: int) -> int:
        return max(0, min(12, age - 5))

    @staticmethod
    def _check_contradiction(text: str, fact: str) -> bool:
        """Simple contradiction detector: negation of key fact words."""
        fact_words = set(fact.split())
        negation_patterns = [
            r"(?:is|are|was|were)\s+not\s+",
            r"(?:isn't|aren't|wasn't|weren't)\s+",
            r"(?:don't|doesn't|didn't)\s+",
            r"(?:never|no|none)\s+",
        ]
        for pat in negation_patterns:
            m = re.search(pat, text)
            if m:
                after = text[m.end():m.end() + 60]
                overlap = len(set(after.split()) & fact_words)
                if overlap >= 3:
                    return True
        return False


# Backwards-compatible alias
ScienceVerifier = FactDBVerifier


# ---------------------------------------------------------------------------
# English Verifier
# ---------------------------------------------------------------------------

class EnglishVerifier(SubjectVerifier):
    """Grammar, vocabulary, and literary term verification."""

    def __init__(self, facts: Dict):
        self._facts = facts
        self._homophones = {}
        for pair in facts.get("grammar_rules", {}).get("homophones", {}).get("pairs", []):
            for w in pair.get("words", []):
                self._homophones[w.lower()] = pair

    def verify(self, item, fmt, age, difficulty, skill_name, lesson_name):
        t0 = time.time()
        checks, failures = [], []
        q_text = item.get("question", {}).get("content", "")
        correct_text = self._extract_correct_answer_text(item, fmt)

        # Check 1: Vocabulary level appropriateness
        checks.append("vocabulary_level")
        grade_band = self._age_to_grade_band(age)
        rules = self._facts.get("vocabulary_by_grade", {}).get(grade_band, {})
        banned = [w.lower() for w in rules.get("banned_words", [])]
        max_syl = rules.get("syllable_max", 99)

        words = re.findall(r'[a-zA-Z]+', q_text)
        for word in words:
            wl = word.lower()
            if wl in banned:
                failures.append(
                    f"Word '{word}' is too advanced for grade band {grade_band}. "
                    f"Use simpler vocabulary appropriate for ages {self._band_ages(grade_band)}."
                )
                break  # One failure is enough
            if self._count_syllables(word) > max_syl and len(word) > 8:
                failures.append(
                    f"Word '{word}' ({self._count_syllables(word)} syllables) exceeds the "
                    f"maximum of {max_syl} syllables for {grade_band}. Use a simpler word."
                )
                break

        # Check 2: Parts of speech accuracy
        q_lower = q_text.lower()
        checks.append("parts_of_speech_check")
        pos_data = self._facts.get("parts_of_speech", {})
        for pos_name, pos_info in pos_data.items():
            if pos_name in q_lower and ("which" in q_lower or "identify" in q_lower or "what type" in q_lower):
                # Question asks about this part of speech — verify correct answer
                correct_lower = correct_text.lower().strip()
                examples = [e.lower() for e in pos_info.get("examples", [])]
                # If the correct answer IS a POS name but the WRONG one, flag it
                if correct_lower in pos_data and correct_lower != pos_name:
                    # E.g., question asks "What part of speech is 'run'?" and answer is "adjective" — wrong
                    failures.append(
                        f"Question asks about '{pos_name}' but the correct answer is "
                        f"'{correct_lower}', which is a different part of speech. "
                        f"Ensure the answer matches the POS type being asked about."
                    )
                # If the correct answer is a word, check it's in the examples for the expected POS
                elif correct_lower and correct_lower not in pos_data and examples:
                    if correct_lower in examples:
                        pass  # Correct: answer is a known example of this POS
                    else:
                        # Check if the answer appears in ANY other POS examples
                        found_in_other = False
                        for other_pos, other_info in pos_data.items():
                            if other_pos == pos_name:
                                continue
                            other_examples = [e.lower() for e in other_info.get("examples", [])]
                            if correct_lower in other_examples:
                                failures.append(
                                    f"The word '{correct_text.strip()}' is listed as a "
                                    f"'{other_pos}', not a '{pos_name}'. Fix the correct "
                                    f"answer to be a valid {pos_name}."
                                )
                                found_in_other = True
                                break
                break

        # Check 3: Literary term accuracy
        checks.append("literary_term_check")
        lit_terms = self._facts.get("literary_terms", {})
        for term_name, term_data in lit_terms.items():
            if term_name in q_lower:
                definition = term_data.get("definition", "").lower()
                # If correct answer is supposed to be the definition, check it
                if correct_text and len(correct_text) > 20:
                    # It's likely a definition answer — check for key concept overlap
                    def_words = set(definition.split())
                    ans_words = set(correct_text.lower().split())
                    overlap = len(def_words & ans_words)
                    if overlap < 2 and len(def_words) > 3:
                        failures.append(
                            f"The answer for '{term_name}' doesn't match the expected definition: "
                            f"'{term_data['definition']}'. Ensure the correct answer accurately "
                            f"defines this literary term."
                        )
                break

        elapsed = (time.time() - t0) * 1000
        return VerificationResult(
            passed=len(failures) == 0,
            subject="english",
            checks_run=checks,
            failures=failures,
            confidence=0.65,
            elapsed_ms=elapsed,
        )

    @staticmethod
    def _age_to_grade_band(age: int) -> str:
        if age <= 7:
            return "K-2"
        elif age <= 10:
            return "3-5"
        elif age <= 13:
            return "6-8"
        return "9-12"

    @staticmethod
    def _band_ages(band: str) -> str:
        return {"K-2": "5-7", "3-5": "8-10", "6-8": "11-13", "9-12": "14-18"}.get(band, "5-18")

    @staticmethod
    def _count_syllables(word: str) -> int:
        word = word.lower().rstrip('e')
        count = len(re.findall(r'[aeiouy]+', word))
        return max(1, count)


# ---------------------------------------------------------------------------
# History Verifier
# ---------------------------------------------------------------------------

class HistoryVerifier(SubjectVerifier):
    """Date, figure, and fact verification for history questions."""

    def __init__(self, facts: Dict):
        self._facts = facts
        self._events = facts.get("events", [])
        self._figures = {f["name"].lower(): f for f in facts.get("figures", [])}
        self._common_errors = facts.get("common_errors", [])

    def verify(self, item, fmt, age, difficulty, skill_name, lesson_name):
        t0 = time.time()
        checks, failures = [], []
        q_text = item.get("question", {}).get("content", "")
        correct_text = self._extract_correct_answer_text(item, fmt)
        combined = f"{q_text} {correct_text}".lower()

        # Check 1: Date verification
        checks.append("date_verification")
        date_errs = self._verify_dates(combined)
        failures.extend(date_errs)

        # Check 2: Chronological ordering (for orderer/sorter)
        if fmt in ("orderer", "sorter"):
            checks.append("chronological_ordering")
            order_errs = self._verify_order(item, fmt)
            failures.extend(order_errs)

        # Check 3: Historical figure accuracy
        checks.append("figure_fact_check")
        for fig_name, fig_data in self._figures.items():
            if fig_name in combined:
                # Check if any claims about this figure are wrong
                if "born" in combined or "birth" in combined:
                    years = re.findall(r'\b(1[0-9]{3}|20[0-2][0-9])\b', combined)
                    for y_str in years:
                        y = int(y_str)
                        if fig_data.get("born") and abs(y - fig_data["born"]) > 0 and abs(y - fig_data["born"]) < 100:
                            if abs(y - fig_data["born"]) > 5:
                                failures.append(
                                    f"Date for {fig_data['name']}'s birth appears incorrect: "
                                    f"text says {y}, but they were born in {fig_data['born']}."
                                )
                break  # Only check the first matching figure

        # Check 4: Common historical misconceptions
        checks.append("common_error_check")
        for err in self._common_errors:
            if self._fuzzy_contains(correct_text.lower(), err["wrong"]):
                failures.append(
                    f"Answer may repeat a common misconception: '{err['wrong']}'. "
                    f"Correction: {err['correct']}"
                )

        elapsed = (time.time() - t0) * 1000
        return VerificationResult(
            passed=len(failures) == 0,
            subject="history",
            checks_run=checks,
            failures=failures,
            confidence=0.7,
            elapsed_ms=elapsed,
        )

    def _verify_dates(self, text: str) -> List[str]:
        errors = []
        years_found = re.findall(r'\b(1[0-9]{3}|20[0-2][0-9])\b', text)
        for y_str in years_found:
            y = int(y_str)
            for event in self._events:
                # Count keyword matches between text and event name
                event_words = [w for w in event["event"].lower().split() if len(w) > 3]
                matches = sum(1 for w in event_words if w in text)
                if matches >= 3:
                    # Event is likely mentioned — check the year
                    event_year = event["year"]
                    event_end = event.get("end_year", event_year)
                    if y != event_year and y != event_end:
                        # Allow range (event spans multiple years)
                        if not (event_year <= y <= event_end):
                            # Only flag if the year is close but wrong (not just a random number)
                            if abs(y - event_year) < 10 and abs(y - event_year) > 5:
                                errors.append(
                                    f"Date mismatch: text says {y} in context of "
                                    f"'{event['event']}', but the actual year is "
                                    f"{event_year}{f'-{event_end}' if event_end != event_year else ''}."
                                )
        return errors

    def _verify_order(self, item: Dict, fmt: str) -> List[str]:
        """For orderer/sorter, check if items can be verified chronologically."""
        errors = []
        widgets = item.get("question", {}).get("widgets", {})
        for w in widgets.values():
            wtype = w.get("type", "")
            if wtype in ("orderer", "sorter"):
                opts = w.get("options", {})
                correct = opts.get("correctOptions", opts.get("correct", []))
                if not correct:
                    continue
                # Extract years for each item
                dated_items = []
                for entry in correct:
                    text = entry.get("content", entry) if isinstance(entry, dict) else str(entry)
                    years = re.findall(r'\b(1[0-9]{3}|20[0-2][0-9])\b', text)
                    if years:
                        dated_items.append((int(years[0]), text))
                # Verify chronological order
                if len(dated_items) >= 2:
                    for i in range(len(dated_items) - 1):
                        if dated_items[i][0] > dated_items[i + 1][0]:
                            errors.append(
                                f"Chronological order error: '{dated_items[i][1]}' "
                                f"({dated_items[i][0]}) is listed before "
                                f"'{dated_items[i + 1][1]}' ({dated_items[i + 1][0]}), "
                                f"but it happened later."
                            )
                            break
        return errors


# ---------------------------------------------------------------------------
# Main Verifier (dispatcher)
# ---------------------------------------------------------------------------

class DeterministicVerifier:
    """
    Unified question verifier. Detects subject, runs universal + subject checks.

    Usage:
        v = DeterministicVerifier()
        r = v.verify(item, "Fractions", "Adding fractions", "numeric_input", 10, 0.5)
        if not r.passed:
            print(r.failures)  # Feed back into prompt
    """

    def __init__(self, fact_db_dir: Optional[str] = None):
        db_dir = fact_db_dir or os.path.join(os.path.dirname(__file__), "fact_databases")

        # --- Load and merge fact databases per subject ---
        # Science: main + biology, chemistry, physics, earth, astronomy, ecology
        science_facts = self._load_and_merge(db_dir, [
            "science_facts.json",
            "science_biology.json",
            "science_chemistry.json",
            "science_physics.json",
            "science_earth.json",
            "science_astronomy.json",
            "science_ecology.json",
        ])

        # English: main + grammar, vocabulary, literature, writing, phonics
        english_facts = self._load_and_merge(db_dir, [
            "english_facts.json",
            "english_grammar.json",
            "english_vocabulary.json",
            "english_literature.json",
            "english_writing.json",
            "english_phonics.json",
        ])

        # History: main file (uses events/figures format, loaded separately)
        # Additional history fact files use facts_by_topic format
        history_main = self._load_facts(db_dir, "history_facts.json")

        # Geography: main + historical geography
        geography_facts = self._load_and_merge(db_dir, [
            "geography_facts.json",
            "history_geography.json",
        ])

        # Economics + Civics: main + separate civics + economics supplements
        econ_civics = self._load_and_merge(db_dir, [
            "economics_civics_facts.json",
            "history_civics.json",
            "history_economics.json",
        ])

        # CS: main + fundamentals
        cs_facts = self._load_and_merge(db_dir, [
            "cs_facts.json",
            "cs_fundamentals.json",
        ])

        # Art: main + art/music supplement
        art_facts = self._load_and_merge(db_dir, [
            "art_history_facts.json",
            "art_music.json",
        ])

        # Music: main file
        music_facts = self._load_facts(db_dir, "music_facts.json")

        # Math fact databases (5 files)
        math_facts = self._load_and_merge(db_dir, [
            "math_arithmetic.json",
            "math_fractions_decimals.json",
            "math_algebra.json",
            "math_geometry.json",
            "math_statistics.json",
        ])

        # Health & PE
        health_facts = self._load_facts(db_dir, "health_pe.json")

        # Social Studies
        social_facts = self._load_and_merge(db_dir, [
            "social_studies.json",
            "history_us.json",
            "history_world.json",
        ])

        # --- Build verifiers ---
        self._math_fact_verifier = FactDBVerifier("math", math_facts, 0.6)
        self._verifiers: Dict[str, SubjectVerifier] = {
            "math": MathVerifier(),
            "science": FactDBVerifier("science", science_facts, 0.6),
            "english": EnglishVerifier(english_facts),
            "history": HistoryVerifier(history_main),
            "geography": FactDBVerifier("geography", geography_facts, 0.6),
            "computer_science": FactDBVerifier("computer_science", cs_facts, 0.55),
            "economics": FactDBVerifier("economics", econ_civics, 0.6),
            "civics": FactDBVerifier("civics", econ_civics, 0.6),
            "art_history": FactDBVerifier("art_history", art_facts, 0.55),
            "music": FactDBVerifier("music", music_facts, 0.55),
            "health": FactDBVerifier("health", health_facts, 0.55),
            "social_studies": FactDBVerifier("social_studies", social_facts, 0.55),
        }
        total_files = 33  # 8 original + 25 new
        logger.info(f"[VERIFIER] Initialized with {len(self._verifiers)} subject verifiers from {total_files} fact databases in {db_dir}")

    @staticmethod
    def _load_facts(db_dir: str, filename: str) -> Dict:
        path = os.path.join(db_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[VERIFIER] Failed to load {filename}: {e} — verification for this subject will be degraded")
            return {}

    @classmethod
    def _load_and_merge(cls, db_dir: str, filenames: list) -> Dict:
        """Load multiple fact database files and merge their facts_by_topic dicts."""
        merged: Dict = {"meta": {"version": 1, "merged": True}, "facts_by_topic": {}}
        for fname in filenames:
            data = cls._load_facts(db_dir, fname)
            topics = data.get("facts_by_topic", {})
            for topic_key, topic_data in topics.items():
                if topic_key in merged["facts_by_topic"]:
                    # Merge facts and common_errors into existing topic
                    existing = merged["facts_by_topic"][topic_key]
                    existing.setdefault("facts", []).extend(topic_data.get("facts", []))
                    existing.setdefault("common_errors", []).extend(topic_data.get("common_errors", []))
                    # Merge keywords (deduplicate)
                    existing_kws = set(existing.get("keywords", []))
                    existing_kws.update(topic_data.get("keywords", []))
                    existing["keywords"] = list(existing_kws)
                else:
                    merged["facts_by_topic"][topic_key] = topic_data
        return merged

    def detect_subject(self, skill_name: str, lesson_name: str, fmt: str, subject_hint: str = "") -> str:
        """Determine subject from skill/lesson names via keyword matching.
        
        Args:
            subject_hint: Optional known subject (e.g. from curriculum). If provided,
                          it's included in keyword matching to improve detection accuracy.
        """
        # numeric_input and expression are always math
        if fmt in ("numeric_input", "expression"):
            return "math"
        combined = f"{skill_name} {lesson_name} {subject_hint}".lower()
        best_subject, best_score = "unknown", 0
        for subject, keywords in _SUBJECT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_subject = subject
        return best_subject if best_score >= 1 else "unknown"

    def verify(
        self,
        item: Dict[str, Any],
        skill_name: str,
        lesson_name: str,
        fmt: str,
        age: int,
        difficulty: float,
        subject_hint: str = "",
    ) -> VerificationResult:
        """
        Main entry point. Detects subject, runs universal + subject-specific checks.
        Returns VerificationResult with pass/fail and failure reasons for prompt feedback.
        """
        t0 = time.time()
        subject = self.detect_subject(skill_name, lesson_name, fmt, subject_hint=subject_hint)

        # Universal checks first
        universal_failures = self._universal_checks(item, skill_name, lesson_name)

        # Subject-specific checks
        verifier = self._verifiers.get(subject)
        if verifier:
            result = verifier.verify(item, fmt, age, difficulty, skill_name, lesson_name)
            result.failures = universal_failures + result.failures
            result.checks_run = ["topic_relevance", "answer_presence"] + result.checks_run
            # For math, also run fact-database checks (common errors, number facts)
            if subject == "math" and self._math_fact_verifier:
                fact_result = self._math_fact_verifier.verify(item, fmt, age, difficulty, skill_name, lesson_name)
                result.checks_run.extend(fact_result.checks_run)
                result.failures.extend(fact_result.failures)
            result.passed = len(result.failures) == 0
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        # Unknown subject — only universal checks
        elapsed = (time.time() - t0) * 1000
        return VerificationResult(
            passed=len(universal_failures) == 0,
            subject=subject,
            checks_run=["topic_relevance", "answer_presence"],
            failures=universal_failures,
            confidence=0.4,
            elapsed_ms=elapsed,
        )

    def _universal_checks(self, item: Dict, skill_name: str, lesson_name: str) -> List[str]:
        """Checks that apply to ALL subjects."""
        failures = []
        q_text = item.get("question", {}).get("content", "").lower()
        widgets = item.get("question", {}).get("widgets", {})

        # Topic relevance: at least one skill keyword (or synonym) should appear
        skill_words = set(re.findall(r'[a-z]+', f"{skill_name} {lesson_name}".lower()))
        skill_words -= SubjectVerifier._STOP_WORDS

        if skill_words:
            # Expand skill keywords with synonyms from _TOPIC_SYNONYMS
            expanded = set(skill_words)
            for kw in list(skill_words):
                if kw in SubjectVerifier._TOPIC_SYNONYMS:
                    expanded.update(SubjectVerifier._TOPIC_SYNONYMS[kw])
            # Also expand plural forms of skill words (e.g. "fractions" → check "fraction" synonyms)
            for kw in list(skill_words):
                singular = kw.rstrip("s")
                if singular in SubjectVerifier._TOPIC_SYNONYMS:
                    expanded.update(SubjectVerifier._TOPIC_SYNONYMS[singular])

            q_words = set(re.findall(r'[a-z]+', q_text))
            overlap = 0

            # Check math symbols in question text (proves math content)
            for sym in SubjectVerifier._MATH_SYMBOLS:
                if sym in q_text:
                    overlap += 1
                    break  # One symbol match is enough

            # Check word overlap with stemming
            for w in expanded:
                if len(w) <= 2:
                    continue
                stem = w.rstrip("s").rstrip("e")
                if w in q_text or any(qw.startswith(stem) or w.startswith(qw.rstrip("s").rstrip("e"))
                                       for qw in q_words if len(qw) > 2):
                    overlap += 1

            # Only fail if zero overlap AND original skill had 2+ meaningful words
            orig_meaningful = [w for w in skill_words if len(w) > 2]
            if overlap == 0 and len(orig_meaningful) >= 2:
                failures.append(
                    f"Question appears off-topic. It should test '{skill_name}' / "
                    f"'{lesson_name}' but none of the skill keywords or synonyms appear "
                    f"in the question text."
                )

        # Answer presence: at least one interactive widget must exist
        interactive_types = {"radio", "numeric-input", "dropdown", "expression",
                            "orderer", "matcher", "sorter"}
        has_interactive = any(
            w.get("type") in interactive_types for w in widgets.values()
        )
        if not has_interactive:
            failures.append(
                "Question has no interactive answer widget. Ensure the question includes "
                "a radio, numeric-input, dropdown, expression, orderer, matcher, or sorter widget."
            )

        # Multi-correct radio detection
        multi_err = SubjectVerifier._check_multi_correct_radio(item)
        if multi_err:
            failures.append(multi_err)

        return failures
