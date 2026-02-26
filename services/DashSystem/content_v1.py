import atexit
import hashlib
import json
import logging
import os
import random
import re
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.genai as genai
from google.genai import types as genai_types
from pymongo.errors import DuplicateKeyError

from managers.mongodb_manager import mongo_db
from services.DashSystem.deterministic_verifier import DeterministicVerifier

logger = logging.getLogger(__name__)

# Shared bounded executor for Gemini calls.
# Avoids creating unbounded short-lived threads under load.
try:
    _GEMINI_EXECUTOR_MAX_WORKERS = max(4, int(os.getenv("CONTENT_V1_GEMINI_MAX_WORKERS", "12")))
except (TypeError, ValueError):
    _GEMINI_EXECUTOR_MAX_WORKERS = 12
_GEMINI_EXECUTOR = ThreadPoolExecutor(
    max_workers=_GEMINI_EXECUTOR_MAX_WORKERS,
    thread_name_prefix="content-v1-gemini",
)


def _shutdown_gemini_executor() -> None:
    _GEMINI_EXECUTOR.shutdown(wait=False, cancel_futures=True)


atexit.register(_shutdown_gemini_executor)


def _run_with_timeout(fn: Any, timeout_s: float) -> Any:
    """Run a callable on the shared Gemini executor with timeout."""
    future = _GEMINI_EXECUTOR.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FutureTimeoutError:
        future.cancel()
        raise


# Image generation settings
STATIC_IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "images")
os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)
try:
    IMAGE_PROBABILITY = float(os.getenv("IMAGE_PROBABILITY", "0.10"))
except (ValueError, TypeError):
    IMAGE_PROBABILITY = 0.10
IMAGE_ELIGIBLE_FORMATS = {"radio_single", "radio_multi", "numeric_input", "dropdown"}
# Base URL for serving images (frontend needs absolute URL since it's on a different port)
IMAGE_BASE_URL = os.getenv("DASH_API_BASE_URL", "http://localhost:8000")

# Topic-aware image probability — first match wins, fallback is IMAGE_PROBABILITY
IMAGE_TOPIC_KEYWORDS: List[Tuple[Tuple[str, ...], float]] = [
    (("geometry", "shape", "triangle", "rectangle", "circle", "polygon",
      "angle", "area", "perimeter", "volume", "coordinate", "graph",
      "plot", "chart", "diagram", "map", "symmetry", "congruent"), 0.80),
    (("science", "biology", "physics", "chemistry", "experiment",
      "organism", "cell", "ecosystem", "force", "energy", "circuit",
      "planet", "solar system", "weather"), 0.60),
    (("fraction", "number line", "measurement", "ruler", "scale",
      "clock", "money", "bar graph", "pie chart", "histogram",
      "place value", "decimal", "percent"), 0.40),
    (("arithmetic", "addition", "subtraction", "multiplication", "division",
      "algebra", "equation", "variable", "exponent", "polynomial",
      "ratio", "proportion", "probability", "statistics"), 0.15),
    (("vocabulary", "grammar", "writing", "reading", "comprehension",
      "spelling", "punctuation", "literature", "poetry"), 0.05),
]


SUPPORTED_FORMATS = [
    "radio_single", "radio_multi", "orderer", "numeric_input", "dropdown",
    "expression", "matcher", "sorter", "definition",
]


class ContentV1Engine:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        logger.info(f"[GEMINI] Loading API key from env: {api_key[:15] if api_key else 'NONE'}...{api_key[-4:] if api_key else ''}")
        self.client = None
        if api_key and api_key != "dummy_for_local_dev":
            try:
                self.client = genai.Client(api_key=api_key)
                logger.info(f"[GEMINI] Client initialized successfully")
            except Exception as e:
                logger.warning(f"[CONTENT_V1] Failed to initialize Gemini client: {e} — AI generation disabled")
        self.model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
        self.fast_model = os.getenv("GEMINI_FAST_MODEL", "gemini-2.0-flash")
        self.gemini_only = os.getenv("CONTENT_V1_GEMINI_ONLY", "true").lower() in {"1", "true", "yes"}

        # Cooldown prevents "quota storm" when 429 RESOURCE_EXHAUSTED is hit
        self._last_quota_error_time = 0.0
        self._cooldown_duration = 180.0  # 3 minute cooldown for free tier limits
        self._consecutive_errors = 0
        self.verifier = DeterministicVerifier()

    def _is_on_cooldown(self) -> bool:
        """Check if Gemini is currently cooled down due to quota errors."""
        if self._last_quota_error_time == 0.0:
            return False
        elapsed = time.time() - self._last_quota_error_time
        if elapsed < self._cooldown_duration:
            return True
        # Cooldown expired
        return False

    def _record_quota_error(self):
        """Record a 429 error and trigger/extend cooldown."""
        self._last_quota_error_time = time.time()
        self._consecutive_errors += 1
        # Backoff cooldown duration if we keep hitting it
        self._cooldown_duration = min(1800, 180 * (2 ** (self._consecutive_errors - 1)))
        logger.warning(f"[GEMINI] Quota exceeded. Cooldown active for {self._cooldown_duration}s.")

    def _reset_cooldown(self):
        """Reset error count on successful call."""
        if self._consecutive_errors > 0:
            logger.info("[GEMINI] Successful call. Resetting quota error counter.")
        self._consecutive_errors = 0
        self._last_quota_error_time = 0.0
        self._cooldown_duration = 180.0

    def call_gemini(self, model: str, contents: Any, config: Dict[str, Any], timeout: float = 30.0) -> Any:
        """Centralized Gemini call wrapper with cooldown and quota error detection."""
        if not self.client:
            raise Exception("Gemini client not initialized")
        
        if self._is_on_cooldown():
            # Check if it's been long enough to retry anyway (safety valve)
            remaining = self._cooldown_duration - (time.time() - self._last_quota_error_time)
            raise Exception(f"Gemini is on cooldown due to quota limits (RESOURCE_EXHAUSTED). Retry in {int(remaining)}s.")

        def _do_call():
            return self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

        try:
            response = _run_with_timeout(_do_call, timeout_s=timeout)
            self._reset_cooldown()
            return response
        except Exception as e:
            err_str = str(e).upper()
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "QUOTA" in err_str:
                self._record_quota_error()
            raise e
        self.verifier = DeterministicVerifier()

    def _extract_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        # Normalize Unicode smart quotes/dashes that Gemini sometimes returns
        cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"')
        cleaned = cleaned.replace("\u2018", "'").replace("\u2019", "'")
        cleaned = cleaned.replace("\u2014", "--").replace("\u2013", "-")
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"[EXTRACT_JSON] Failed to parse ({len(cleaned)} chars): {cleaned[:120]}")
            return {}

    def _age_band(self, age: int) -> str:
        if age <= 9:
            return "child"
        if age <= 13:
            return "middle"
        return "teen"

    def _memory_context(self, user_id: str) -> Dict[str, Any]:
        user = mongo_db.users.find_one({"user_id": user_id}) or {}
        return {
            "interests": user.get("interests", []),
            "biography": user.get("biography", ""),
            "preferred_language": user.get("preferred_language", "English"),
            "learning_style": user.get("learning_style", {}),
        }

    def _build_fallback_plan(self, learning_goal: str) -> Dict[str, Any]:
        goal = learning_goal.strip() or "General learning"
        base = goal.split(",")[0].strip().title()
        return {
            "title": f"{base} Journey",
            "steps": [
                {
                    "id": "step_1",
                    "topic": base,
                    "title": f"{base} Foundations",
                    "description": f"Start with core ideas in {base}.",
                },
                {
                    "id": "step_2",
                    "topic": base,
                    "title": f"{base} Practice",
                    "description": f"Apply {base} ideas with mixed question formats.",
                },
                {
                    "id": "step_3",
                    "topic": base,
                    "title": f"{base} Real-World Use",
                    "description": f"Use {base} in practical scenarios.",
                },
            ],
        }

    def generate_learning_plan(self, age: int, learning_goal: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        if self.gemini_only and not self.client:
            raise RuntimeError("Content V1 requires Gemini but no API key/client is configured")
        if not self.client:
            return self._build_fallback_plan(learning_goal)

        prompt = (
            "Create a concise personalized learning plan as strict JSON. "
            "Do not mention any brand names. "
            "Tone is playful, witty, and age-appropriate. "
            "Return keys: title, steps. steps must be 4-6 items, each with id, topic, title, description. "
            f"Age: {age}. Learning goal: {learning_goal}. "
            f"Memory context: {json.dumps(memory, ensure_ascii=True)}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"temperature": 0.4},
            )
            parsed = self._extract_json(response.text or "")
            if isinstance(parsed.get("steps"), list) and parsed["steps"]:
                return parsed
        except Exception as e:
            logger.warning(f"[LEARNING_PLAN] Gemini learning plan failed for goal='{learning_goal[:50]}...': {e}")
        return self._build_fallback_plan(learning_goal)

    # ── Fallback helpers ────────────────────────────────────────────
    _MATH_KEYWORDS = {"math", "algebra", "geometry", "arithmetic", "calculus",
                      "trigonometry", "statistics", "number", "fraction", "decimal",
                      "multiplication", "addition", "subtraction", "division"}

    @staticmethod
    def _is_math_topic(topic: str) -> bool:
        low = topic.lower()
        return any(kw in low for kw in ContentV1Engine._MATH_KEYWORDS)

    @staticmethod
    def _age_number_range(age: int) -> tuple:
        """Return (max_a, max_b) for arithmetic fallbacks based on age."""
        if age <= 7:
            return (10, 10)       # K-2: sums/products ≤ 100
        if age <= 10:
            return (12, 12)       # 3-5: up to 144
        return (15, 15)           # 6+: up to 225

    def _fallback_question(self, topic: str, age: int, fmt: str, difficulty: float) -> Dict[str, Any]:
        topic_clean = topic.strip().title() or "General Knowledge"
        qid = f"c1_{uuid.uuid4().hex[:10]}"
        is_math = self._is_math_topic(topic_clean)
        max_a, max_b = self._age_number_range(age)

        # ── Non-math subjects: redirect math-only formats to radio_single ─
        if not is_math and fmt in ("numeric_input", "expression", "number_line", "table"):
            fmt = "radio_single"

        # ── Age guard: young kids get simpler formats ─────────────────────
        if age <= 7 and fmt in ("expression", "matcher", "sorter", "definition"):
            fmt = "radio_single"
        elif age <= 9 and fmt == "expression":
            fmt = "numeric_input"

        if fmt == "numeric_input":
            a, b = random.randint(2, max_a), random.randint(2, max_b)
            if age <= 7:
                # Addition for young kids
                a, b = random.randint(1, 10), random.randint(1, 10)
                answer = a + b
                q_text = f"What is {a} + {b}? [[☃ numeric-input 1]]"
                hints = [
                    {"content": f"Start at {a} and count up {b} more."},
                    {"content": f"You can use your fingers: hold up {a}, then add {b} more."},
                    {"content": f"{a} + {b} = {answer}."},
                ]
            else:
                answer = a * b
                q_text = f"What is {a} times {b}? [[☃ numeric-input 1]]"
                hints = [
                    {"content": f"Multiplication means repeated addition: {a} groups of {b}."},
                    {"content": f"Try adding {b} a total of {a} times."},
                    {"content": f"{a} x {b} = {answer}. The answer is {answer}."},
                ]
            item = {
                "question": {
                    "content": q_text,
                    "images": {},
                    "widgets": {
                        "numeric-input 1": {
                            "type": "numeric-input",
                            "graded": True,
                            "options": {
                                "coefficient": False, "static": False,
                                "labelText": "", "size": "normal",
                                "answers": [{"status": "correct", "value": answer,
                                             "maxError": 0.01, "simplify": "optional",
                                             "strict": False, "message": ""}],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": hints,
            }
        elif fmt == "dropdown":
            item = {
                "question": {
                    "content": f"Which statement is most accurate about {topic_clean}? [[☃ dropdown 1]]",
                    "images": {},
                    "widgets": {
                        "dropdown 1": {
                            "type": "dropdown",
                            "graded": True,
                            "options": {
                                "placeholder": "select one",
                                "choices": [
                                    {"content": f"It requires learning specific concepts and skills", "correct": True},
                                    {"content": f"It is the same as studying a completely different subject", "correct": False},
                                    {"content": f"It only involves memorizing dates and names", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Think about what studying {topic_clean} actually involves."},
                    {"content": f"Does {topic_clean} have its own concepts, or is it identical to another subject?"},
                    {"content": f"{topic_clean} has its own specific concepts and skills to master."},
                ],
            }
        elif fmt == "orderer":
            # Concrete process steps — NOT meta-learning stages
            options = [
                f"Learn the basics of {topic_clean}",
                f"Practice simple {topic_clean} problems",
                f"Tackle harder {topic_clean} challenges",
                f"Use {topic_clean} in real situations",
            ]
            item = {
                "question": {
                    "content": f"Put these steps in order from first to last.",
                    "images": {},
                    "widgets": {
                        "orderer 1": {
                            "type": "orderer",
                            "graded": True,
                            "options": {
                                "layout": "horizontal",
                                "options": [{"content": o} for o in random.sample(options, len(options))],
                                "correctOptions": [{"content": o} for o in options],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "What would you do first when starting something new?"},
                    {"content": "Start with basics, then practice, then try harder things."},
                    {"content": f"Order: Learn basics -> Practice simple -> Harder challenges -> Real situations."},
                ],
            }
        elif fmt == "radio_multi":
            item = {
                "question": {
                    "content": f"Select the TWO statements that are true about {topic_clean}.",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": True,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"You need to practice to get better at {topic_clean}", "correct": True},
                                    {"content": f"{topic_clean} can never be improved with study", "correct": False},
                                    {"content": f"{topic_clean} builds on understanding key ideas", "correct": True},
                                    {"content": f"Everyone is born already knowing {topic_clean}", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Think about how people actually learn {topic_clean}."},
                    {"content": "Can you improve at something by studying and practicing?"},
                    {"content": f"Practice helps, and {topic_clean} is built on understanding key ideas."},
                ],
            }
        elif fmt == "expression":
            # Only reached for math subjects with age > 9
            a, b = random.randint(2, min(9, max_a)), random.randint(1, min(9, max_b))
            answer_val = f"{a + b}x"
            item = {
                "question": {
                    "content": f"Simplify: ${a}x + {b}x$ [[☃ expression 1]]",
                    "images": {},
                    "widgets": {
                        "expression 1": {
                            "type": "expression",
                            "graded": True,
                            "options": {
                                "buttonsVisible": "never",
                                "functions": ["f", "g", "h"],
                                "times": False,
                                "answerForms": [{"value": answer_val, "form": True, "simplify": False, "considered": "correct"}],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "When you add like terms, add the coefficients."},
                    {"content": f"${a}x + {b}x$ means {a} groups of $x$ plus {b} groups of $x$."},
                    {"content": f"{a} + {b} = {a + b}, so the answer is ${a + b}x$."},
                ],
            }
        elif fmt == "matcher":
            item = {
                "question": {
                    "content": f"Match each term with the correct description. [[☃ matcher 1]]",
                    "images": {},
                    "widgets": {
                        "matcher 1": {
                            "type": "matcher",
                            "graded": True,
                            "options": {
                                "labels": ["Term", "Meaning"],
                                "left": ["Beginner", "Intermediate", "Advanced", "Expert"],
                                "right": ["Just starting to learn", "Knows the basics well", "Can handle hard problems", "Can teach others"],
                                "orderMatters": True,
                                "padding": True,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "A beginner is someone who is just starting out."},
                    {"content": "An expert knows enough to teach others."},
                    {"content": "Beginner=Just starting, Intermediate=Knows basics, Advanced=Hard problems, Expert=Can teach."},
                ],
            }
        elif fmt == "sorter":
            items_list = ["Smallest", "Small", "Medium", "Large"]
            item = {
                "question": {
                    "content": f"Sort these from smallest to largest. [[☃ sorter 1]]",
                    "images": {},
                    "widgets": {
                        "sorter 1": {
                            "type": "sorter",
                            "graded": True,
                            "options": {
                                "correct": items_list,
                                "layout": "horizontal",
                                "padding": True,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "Which one is the very smallest?"},
                    {"content": "After smallest, what comes next?"},
                    {"content": "Order: Smallest -> Small -> Medium -> Large."},
                ],
            }
        elif fmt == "definition":
            item = {
                "question": {
                    "content": f"Read about [[☃ definition 1]] and answer below.\n\nBased on the definition, what kind of topic is {topic_clean}? [[☃ radio 1]]",
                    "images": {},
                    "widgets": {
                        "definition 1": {
                            "type": "definition",
                            "graded": False,
                            "options": {
                                "togglePrompt": topic_clean,
                                "definition": f"{topic_clean} is a field of study with its own set of ideas, methods, and problems to solve.",
                                "static": False,
                            },
                        },
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": False,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"A field with its own ideas and methods", "correct": True},
                                    {"content": f"A type of sport or physical activity", "correct": False},
                                    {"content": f"A kind of food or recipe", "correct": False},
                                    {"content": f"A musical instrument", "correct": False},
                                ],
                            },
                        },
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "Look at the definition — what does it say this topic is?"},
                    {"content": "The definition mentions ideas, methods, and problems."},
                    {"content": f"It says {topic_clean} is a field of study with its own ideas and methods."},
                ],
            }
        elif fmt == "categorizer":
            item = {
                "question": {
                    "content": f"Put each item in the right group. [[☃ categorizer 1]]",
                    "images": {},
                    "widgets": {
                        "categorizer 1": {
                            "type": "categorizer",
                            "graded": True,
                            "options": {
                                "items": [f"Studying {topic_clean}", f"Practicing {topic_clean} skills", "Cooking dinner", f"Reading about {topic_clean}"],
                                "categories": [f"Related to {topic_clean}", "Not related"],
                                "values": [0, 0, 1, 0],
                                "randomizeItems": False,
                                "static": False,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Which activities involve {topic_clean}?"},
                    {"content": "Cooking dinner is not related to this subject."},
                    {"content": f"Studying, practicing, and reading about {topic_clean} are all related. Cooking is not."},
                ],
            }
        elif fmt == "number_line":
            a = random.randint(1, min(8, max_a))
            b = random.randint(1, min(8, max_b))
            answer = a + b
            item = {
                "question": {
                    "content": f"Place the point at {a} + {b} on the number line. [[☃ number-line 1]]",
                    "images": {},
                    "widgets": {
                        "number-line 1": {
                            "type": "number-line",
                            "graded": True,
                            "options": {
                                "range": [0, 20],
                                "correctX": answer,
                                "correctRel": "eq",
                                "tickStep": 1,
                                "snapDivisions": 1,
                                "labelStyle": "decimal",
                                "labelTicks": True,
                                "isInequality": False,
                                "numDivisions": None,
                                "divisionRange": [1, 10],
                                "initialX": None,
                                "static": False,
                                "isTickCtrl": False,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"What is {a} + {b}?"},
                    {"content": f"Start at {a} and count up {b} more."},
                    {"content": f"{a} + {b} = {answer}. Place the dot at {answer}."},
                ],
            }
        elif fmt == "table":
            mult = random.choice([2, 3, 4, 5]) if age <= 9 else random.choice([3, 4, 5, 6])
            pairs = [(i, i * mult) for i in range(1, 5)]
            item = {
                "question": {
                    "content": f"Complete the table: multiply each input by {mult}. [[☃ table 1]]",
                    "images": {},
                    "widgets": {
                        "table 1": {
                            "type": "table",
                            "graded": True,
                            "options": {
                                "headers": ["Input", "Output"],
                                "rows": 4,
                                "columns": 2,
                                "answers": [[str(a), str(b)] for a, b in pairs],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Each output is the input times {mult}. What is 1 x {mult}?"},
                    {"content": f"Row 1: 1 x {mult} = {mult}. Row 2: 2 x {mult} = {2*mult}."},
                    {"content": f"Answers: {', '.join(f'{a}->{b}' for a,b in pairs)}."},
                ],
            }
        else:
            # radio_single (default) - specific skill-based question, not meta
            item = {
                "question": {
                    "content": f"What happens when you use {topic_clean} in a real problem?",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": False,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"{topic_clean} involves learning and practicing specific skills", "correct": True},
                                    {"content": f"{topic_clean} can only be learned by watching TV", "correct": False},
                                    {"content": f"{topic_clean} has nothing to do with thinking or problem solving", "correct": False},
                                    {"content": f"Nobody studies {topic_clean} in school", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Think about what studying {topic_clean} actually involves."},
                    {"content": f"Does {topic_clean} require learning specific skills?"},
                    {"content": f"{topic_clean} involves learning and practicing — that's how all subjects work."},
                ],
            }

        return {
            "question_id": qid,
            "topic": topic_clean,
            "format": fmt,
            "difficulty": difficulty,
            "age": age,
            "item": item,
        }

    def _repair_item(self, item: Dict[str, Any], fmt: str = None) -> Dict[str, Any]:
        """Fix common Gemini JSON format mistakes and ensure Perseus format compliance."""
        try:
            widgets = item.get("question", {}).get("widgets", {})
            for wname, widget in widgets.items():
                wtype = widget.get("type", "")
                opts = widget.get("options", {})

                # Fix 1: radio/dropdown — options is a list instead of {"choices": [...]}
                if wtype == "radio" and isinstance(opts, list):
                    multi = fmt in ("radio_multi",)
                    widget["options"] = {"choices": opts, "multipleSelect": multi}
                    logger.info(f"[REPAIR] Fixed radio options: list → dict with choices")

                if wtype == "dropdown" and isinstance(opts, list):
                    widget["options"] = {"choices": opts, "placeholder": "select one"}
                    logger.info(f"[REPAIR] Fixed dropdown options: list → dict with choices")

                # Fix 2: radio choices — ensure 'correct' key exists and is boolean
                if wtype == "radio" and isinstance(widget.get("options"), dict):
                    choices = widget["options"].get("choices", [])
                    for c in choices:
                        c["correct"] = bool(c.get("correct", False))

                # Fix 3: numeric-input answers as single dict instead of list
                if wtype == "numeric-input":
                    answers = opts.get("answers", [])
                    if isinstance(answers, dict):
                        widget["options"]["answers"] = [answers]
                        logger.info(f"[REPAIR] Fixed numeric-input answers: dict → list")

                # Fix 4: expression answerForms as single dict instead of list
                if wtype == "expression":
                    forms = opts.get("answerForms", [])
                    if isinstance(forms, dict):
                        widget["options"]["answerForms"] = [forms]
                        logger.info(f"[REPAIR] Fixed expression answerForms: dict → list")
                    # Ensure required fields that Perseus MathInput needs
                    # Use explicit falsy checks — setdefault won't override empty lists/strings
                    if not opts.get("buttonSets"):
                        opts["buttonSets"] = ["basic"]
                    if not opts.get("functions"):
                        opts["functions"] = ["f", "g", "h"]
                    opts.setdefault("times", False)
                    if not opts.get("buttonsVisible"):
                        opts["buttonsVisible"] = "never"

                # Fix 5: orderer — normalize options and correctOptions to {content: str} objects
                if wtype == "orderer":
                    for key in ("options", "correctOptions"):
                        arr = opts.get(key, [])
                        if arr and isinstance(arr[0], str):
                            opts[key] = [{"content": s} for s in arr]
                    if not opts.get("correctOptions") and opts.get("options"):
                        pass  # can't reliably infer correct order

                # Fix 6: add missing 'graded' field
                if "graded" not in widget:
                    widget["graded"] = True

                # --- Perseus format compliance (match reference format) ---
                # Every widget needs version, alignment, static
                if "version" not in widget:
                    # Type-specific versions matching Perseus widget schemas
                    version_map = {
                        "radio": {"major": 2, "minor": 0},
                        "numeric-input": {"major": 0, "minor": 0},
                        "expression": {"major": 2, "minor": 0},
                        "dropdown": {"major": 0, "minor": 0},
                        "orderer": {"major": 0, "minor": 0},
                        "sorter": {"major": 0, "minor": 0},
                        "matcher": {"major": 0, "minor": 0},
                        "categorizer": {"major": 0, "minor": 0},
                        "definition": {"major": 0, "minor": 0},
                        "image": {"major": 0, "minor": 0},
                        "number-line": {"major": 0, "minor": 0},
                        "table": {"major": 0, "minor": 0},
                    }
                    widget["version"] = version_map.get(wtype, {"major": 0, "minor": 0})
                if "alignment" not in widget:
                    widget["alignment"] = "block" if wtype == "image" else "default"
                if "static" not in widget:
                    widget["static"] = False

                # Radio widgets: ensure all required options fields exist
                if wtype == "radio":
                    radio_opts = widget.get("options", {})
                    radio_opts.setdefault("countChoices", False)
                    radio_opts.setdefault("deselectEnabled", False)
                    radio_opts.setdefault("displayCount", None)
                    radio_opts.setdefault("hasNoneOfTheAbove", False)
                    radio_opts.setdefault("multipleSelect", False)
                    radio_opts.setdefault("randomize", False)
                    # Normalize choices: ensure all items are dicts
                    choices = radio_opts.get("choices", [])
                    choices = [c if isinstance(c, dict) else {"content": str(c), "correct": False} for c in choices]
                    radio_opts["choices"] = choices
                    radio_opts["numCorrect"] = sum(1 for c in choices if c.get("correct"))
                    # Backfill misconception field on distractors for responsive hints
                    for c in choices:
                        if not c.get("correct", False):
                            c.setdefault("misconception", "Common student error")
                        else:
                            c.setdefault("misconception", None)

                # Numeric-input: ensure all required options fields
                if wtype == "numeric-input":
                    ni_opts = widget.get("options", {})
                    ni_opts.setdefault("coefficient", False)
                    ni_opts.setdefault("labelText", "")
                    ni_opts.setdefault("size", "normal")
                    ni_opts.setdefault("static", False)
                    for ans in ni_opts.get("answers", []):
                        ans.setdefault("maxError", 0.01)
                        ans.setdefault("message", "")
                        ans.setdefault("simplify", "required")
                        ans.setdefault("strict", False)

                # Dropdown: ensure placeholder, static, and boolean correct flags
                if wtype == "dropdown":
                    dd_opts = widget.get("options", {})
                    dd_opts.setdefault("placeholder", "Select an answer")
                    dd_opts.setdefault("static", False)
                    # Coerce correct field to boolean (Gemini may return "true"/1/etc)
                    for c in dd_opts.get("choices", []):
                        if "correct" in c:
                            c["correct"] = bool(c["correct"])
                        else:
                            c["correct"] = False
                    # Backfill misconception field on dropdown distractors
                    for c in dd_opts.get("choices", []):
                        if not c.get("correct", False):
                            c.setdefault("misconception", "Common student error")
                        else:
                            c.setdefault("misconception", None)

                # Matcher: ensure labels and padding
                if wtype == "matcher":
                    m_opts = widget.get("options", {})
                    m_opts.setdefault("labels", ["Left", "Right"])
                    m_opts.setdefault("orderMatters", False)
                    m_opts.setdefault("padding", True)

                # Sorter: ensure layout
                if wtype == "sorter":
                    s_opts = widget.get("options", {})
                    s_opts.setdefault("layout", "horizontal")
                    s_opts.setdefault("padding", True)

                # Categorizer: ensure required fields
                if wtype == "categorizer":
                    cat_opts = widget.get("options", {})
                    cat_opts.setdefault("randomizeItems", False)
                    cat_opts.setdefault("static", False)
                    cat_opts.setdefault("highlightLint", False)
                    # Ensure values are integers
                    vals = cat_opts.get("values", [])
                    cat_opts["values"] = [int(v) if isinstance(v, (int, float)) else 0 for v in vals]

                # Number-line: ensure required fields
                if wtype == "number-line":
                    nl_opts = widget.get("options", {})
                    nl_opts.setdefault("labelRange", [None, None])
                    nl_opts.setdefault("initialX", None)
                    nl_opts.setdefault("tickStep", 1)
                    nl_opts.setdefault("labelStyle", "decimal")
                    nl_opts.setdefault("labelTicks", True)
                    nl_opts.setdefault("isInequality", False)
                    nl_opts.setdefault("snapDivisions", 2)
                    nl_opts.setdefault("correctRel", "eq")
                    nl_opts.setdefault("numDivisions", None)
                    nl_opts.setdefault("divisionRange", [1, 10])
                    nl_opts.setdefault("isTickCtrl", False)
                    nl_opts.setdefault("static", False)

                # Table: ensure required fields and stringify answers
                if wtype == "table":
                    t_opts = widget.get("options", {})
                    t_opts.setdefault("headers", [""])
                    t_opts.setdefault("rows", 4)
                    t_opts.setdefault("columns", 2)
                    # Ensure all answer values are strings
                    answers = t_opts.get("answers", [])
                    t_opts["answers"] = [[str(cell) for cell in row] for row in answers]

            # Fix 7: ensure every non-image widget has a [[☃ name]] placeholder in content
            content = item.get("question", {}).get("content", "")
            for wname, widget in widgets.items():
                wtype = widget.get("type", "")
                if wtype == "image":
                    continue
                if wname not in content:
                    content = content.rstrip() + f"\n\n[[☃ {wname}]]"
                    logger.info(f"[REPAIR] Added missing placeholder for {wname}")
            item.setdefault("question", {})["content"] = content

            # Fix 8: hints as list of strings instead of list of dicts
            hints = item.get("hints", [])
            for i, h in enumerate(hints):
                if isinstance(h, str):
                    hints[i] = {"content": h, "images": {}, "replace": False, "widgets": {}}
                    logger.info(f"[REPAIR] Fixed hint {i}: string → dict")
                else:
                    # Ensure all hint fields exist per reference format
                    h.setdefault("images", {})
                    h.setdefault("replace", False)
                    h.setdefault("widgets", {})

            # Ensure question has images field
            q = item.get("question", {})
            q.setdefault("images", {})

            # Ensure answer_area / answerArea exists with proper structure
            if "answerArea" not in item and "answer_area" not in item:
                item["answerArea"] = {
                    "calculator": False,
                    "options": {"content": "", "images": {}, "widgets": {}},
                    "type": "multiple",
                }
            # Normalize: if answerArea exists, ensure it has full structure
            aa = item.get("answerArea") or item.get("answer_area", {})
            aa.setdefault("calculator", False)
            aa.setdefault("type", "multiple")

        except Exception as e:
            logger.error(f"[REPAIR] Repair failed for fmt={fmt}: {e}", exc_info=True)
        return item

    def _validate_item(self, item: Dict[str, Any], fmt: str = None) -> bool:
        try:
            q = item["question"]
            content = q["content"]
            widgets = q["widgets"]
            if not isinstance(widgets, dict) or not widgets:
                return False
            if not content or len(content.strip()) < 10:
                return False
            # Ensure widget placeholder exists in content
            if "[[☃" not in content:
                return False

            # Format-specific validation
            # For definition format, jump directly to definition branch
            # (avoids picking the companion radio as the first widget)
            widget = next(iter(widgets.values()))
            wtype = widget.get("type", "")
            if fmt == "definition":
                wtype = "definition"

            if wtype == "radio":
                choices = widget.get("options", {}).get("choices", [])
                if len(choices) < 3:
                    return False
                correct_count = sum(1 for c in choices if c.get("correct"))
                multi = widget.get("options", {}).get("multipleSelect", False)
                if multi and correct_count < 2:
                    return False
                if not multi and correct_count != 1:
                    return False
                # Soft check: warn if distractors lack misconception metadata
                missing_misc = sum(
                    1 for c in choices
                    if not c.get("correct", False) and not c.get("misconception")
                )
                if missing_misc:
                    logger.info(f"[VALIDATE] {missing_misc} distractor(s) missing misconception field")

            elif wtype == "orderer":
                opts = widget.get("options", {})
                if not opts.get("correctOptions") or len(opts["correctOptions"]) < 3:
                    return False

            elif wtype == "numeric-input":
                answers = widget.get("options", {}).get("answers", [])
                if not answers or not any(a.get("status") == "correct" for a in answers):
                    return False
                # Ensure the correct answer has a numeric value
                correct_ans = next((a for a in answers if a.get("status") == "correct"), None)
                if correct_ans and not isinstance(correct_ans.get("value"), (int, float)):
                    return False

            elif wtype == "dropdown":
                choices = widget.get("options", {}).get("choices", [])
                correct_count = sum(1 for c in choices if c.get("correct"))
                if correct_count != 1 or len(choices) < 3:
                    return False

            elif wtype == "expression":
                expr_opts = widget.get("options", {})
                forms = expr_opts.get("answerForms", [])
                if not forms or not any(f.get("considered") == "correct" and f.get("value") is not None for f in forms):
                    return False
                # Ensure required rendering fields exist (Perseus crashes without these)
                if not expr_opts.get("buttonSets"):
                    return False

            elif wtype == "matcher":
                opts = widget.get("options", {})
                left = opts.get("left", [])
                right = opts.get("right", [])
                if len(left) < 3 or len(right) < 3 or len(left) != len(right):
                    return False
                # Ensure a correct answer mapping exists (otherwise unanswerable)
                if not opts.get("correct") and not opts.get("orderMatters"):
                    # If no explicit correct array and order doesn't matter,
                    # the right array as-is IS the answer key — that's fine
                    pass
                elif opts.get("correct"):
                    correct = opts["correct"]
                    if len(correct) != len(left):
                        return False

            elif wtype == "sorter":
                correct = widget.get("options", {}).get("correct", [])
                if len(correct) < 3:
                    return False

            elif wtype == "definition":
                # Definition widget is display-only; must have a companion radio widget
                if len(widgets) < 2:
                    return False
                # Find and validate the companion radio widget
                radio_widget = None
                for w in widgets.values():
                    if w.get("type") == "radio":
                        radio_widget = w
                        break
                if not radio_widget:
                    return False
                # Validate radio choices have exactly 1 correct answer
                radio_choices = radio_widget.get("options", {}).get("choices", [])
                if len(radio_choices) < 3:
                    return False
                radio_correct = sum(1 for c in radio_choices if c.get("correct"))
                if radio_correct != 1:
                    return False

            elif wtype == "categorizer":
                opts = widget.get("options", {})
                items = opts.get("items", [])
                categories = opts.get("categories", [])
                values = opts.get("values", [])
                if len(items) < 3 or len(categories) < 2:
                    return False
                if len(values) != len(items):
                    return False
                # Each value must be a valid category index
                if not all(isinstance(v, int) and 0 <= v < len(categories) for v in values):
                    return False

            elif wtype == "number-line":
                opts = widget.get("options", {})
                rng = opts.get("range", [])
                if not isinstance(rng, list) or len(rng) != 2:
                    return False
                correct_x = opts.get("correctX")
                if correct_x is None:
                    return False
                if not (rng[0] <= correct_x <= rng[1]):
                    return False

            elif wtype == "table":
                opts = widget.get("options", {})
                headers = opts.get("headers", [])
                rows = opts.get("rows", 0)
                columns = opts.get("columns", 0)
                answers = opts.get("answers", [])
                if len(headers) < 2 or rows < 2 or columns < 2:
                    return False
                if columns != len(headers):
                    return False
                if len(answers) != rows:
                    return False
                if not all(len(row) == columns for row in answers):
                    return False

            # Check hints: require at least 2 with substantive content
            hints = item.get("hints", [])
            valid_hints = [h for h in hints if isinstance(h, dict)]
            if len(valid_hints) < 2 or not all(
                h.get("content") and len(h["content"]) >= 10 for h in valid_hints[:2]
            ):
                return False

            # Reject questions that reference pictures/images without having an image widget
            import re
            content_text = item.get("question", {}).get("content", "")
            has_image_widget = any(
                w.get("type") == "image" for w in widgets.values()
            )
            if not has_image_widget and re.search(
                r'\b(?:look at|examine|see|observe|study)\s+(?:the\s+)?(?:picture|image|diagram|illustration|photo|figure)',
                content_text, re.IGNORECASE
            ):
                return False

            return True
        except Exception as e:
            logger.warning(f"[VALIDATE_ITEM] Validation exception for fmt={fmt}: {e}")
            return False

    # ---- Subject-content cross-validation --------------------------------
    # Widget types that are only valid for STEM subjects (math, science, python)
    _MATH_ONLY_WIDGETS = {"expression", "numeric-input"}
    # Subjects where math-only widgets are acceptable
    _STEM_SUBJECTS = {"math", "science", "python", "physics", "chemistry",
                      "astronomy", "astrophysics", "statistics", "economics"}
    # Content patterns that indicate off-topic phonics/counting in non-English subjects
    _PHONICS_PATTERNS = re.compile(
        r"how many (?:letters|syllables)|count the letters|spell the word|"
        r"what letter does.*start with|clap.*syllables|rhymes with|"
        r"what sound does.*make|what color is",
        re.IGNORECASE,
    )

    def _validate_subject_content(self, item: Dict[str, Any], subject: str = "",
                                   fmt: str = None) -> bool:
        """Reject questions whose widget type or content doesn't match the subject.

        Returns True if the question is acceptable, False if it should be rejected.
        """
        if not subject:
            return True  # No subject info — can't validate

        subj_lower = subject.lower().strip()
        try:
            widgets = item.get("question", {}).get("widgets", {})
            content = item.get("question", {}).get("content", "")

            # Rule 1: expression / numeric-input only allowed in STEM subjects
            for _wname, wval in widgets.items():
                if not isinstance(wval, dict):
                    continue
                wtype = wval.get("type", "")
                if wtype in self._MATH_ONLY_WIDGETS and subj_lower not in self._STEM_SUBJECTS:
                    logger.info(f"[SUBJECT_VALIDATE] Rejected: {wtype} widget in {subject}")
                    return False

            # Rule 2: phonics/letter-counting content only valid for English/Phonics
            if subj_lower not in ("english", "phonics", "spelling"):
                if self._PHONICS_PATTERNS.search(content):
                    logger.info(f"[SUBJECT_VALIDATE] Rejected: phonics content in {subject}")
                    return False

            # Rule 3: pure arithmetic (e.g. "What is 5+3?") not valid for History/English/Art
            non_math = {"history", "english", "art", "music theory", "philosophy",
                        "cooking", "spanish", "greek", "korean", "russian",
                        "thai", "hindi", "french", "german"}
            if subj_lower in non_math:
                import re as _re
                # Detect pure arithmetic: "What is <number> <op> <number>"
                if _re.search(r"what is \d+\s*[+\-×÷*/]\s*\d+", content, _re.IGNORECASE):
                    logger.info(f"[SUBJECT_VALIDATE] Rejected: arithmetic in {subject}")
                    return False

            return True
        except Exception as e:
            logger.warning(f"[SUBJECT_VALIDATE] Subject validation exception for subject={subject}: {e}")
            return True  # Don't block on validation errors

    def _gemini_question(self, topic: str, age: int, fmt: str, difficulty: float, memory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None

        band = self._age_band(age)
        prompt = (
            "Generate ONE Perseus question as strict JSON with keys: question, answerArea, hints. "
            "No markdown, no prose outside JSON. "
            "Question must be clearly about the topic and age-appropriate. "
            "Tone: playful and light sarcasm, never rude. "
            f"Topic: {topic}. Age: {age} ({band}). Difficulty 0-1: {difficulty}. Format: {fmt}. "
            "Allowed formats: radio_single, radio_multi, orderer, numeric_input, dropdown, expression, matcher, sorter, definition. "
            "For radio widgets, include options.choices with explicit boolean 'correct' per choice. "
            "For orderer widgets, include options.correctOptions with ordered content list. "
            "For numeric-input widgets, include options.answers with value, status='correct', maxError, simplify, strict. "
            "For dropdown widgets, include options.choices with exactly 1 correct choice. "
            "For expression widgets, include options.answerForms with value (LaTeX), considered='correct'. "
            "For matcher widgets, include options.left and options.right arrays of equal length (3+). "
            "For sorter widgets, include options.correct array of items in correct order (3+). "
            "For definition widgets, include a definition widget and a companion radio widget. "
            f"Memory context for personalization/examples only: {json.dumps(memory, ensure_ascii=True)}"
        )

        try:
            def _call_gemini() -> Any:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"temperature": 0.6},
                )

            response = _run_with_timeout(_call_gemini, timeout_s=20)
            parsed = self._extract_json(response.text or "")
            if not isinstance(parsed, dict) or not parsed:
                logger.warning("[GENERATE] _extract_json returned non-dict or empty, falling through to fallback")
            else:
                parsed = self._repair_item(parsed, fmt=fmt)
                if self._validate_item(parsed, fmt=fmt):
                    return parsed
        except FutureTimeoutError:
            logger.warning(f"[GENERATE] Gemini timeout (20s) for topic='{topic[:50]}...', age={age}, fmt={fmt}")
            return None
        except Exception as e:
            logger.warning(f"[GENERATE] Gemini generation failed for topic='{topic[:50]}...', age={age}, fmt={fmt}: {e}")

        # Fallback path that is still Gemini-driven: get a short seed text, then
        # build a guaranteed-valid Perseus item structure in code.
        seed = self._gemini_seed_text(topic, age, memory)
        if not seed:
            return None
        item = self._build_seeded_item(topic, fmt, seed)
        return self._repair_item(item, fmt=fmt)

    def _gemini_seed_text(self, topic: str, age: int, memory: Dict[str, Any]) -> Optional[str]:
        if not self.client:
            return None
        prompt = (
            "Write one short, age-appropriate teaching prompt (max 18 words) for this topic. "
            "No markdown. No lists. Return plain text only. "
            f"Topic: {topic}. Age: {age}. Memory context: {json.dumps(memory, ensure_ascii=True)}"
        )
        try:
            def _call_gemini() -> Any:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"temperature": 0.4},
                )
            response = _run_with_timeout(_call_gemini, timeout_s=20)
            text = (response.text or "").strip()
            if text:
                return re.sub(r"\s+", " ", text)[:240]
        except Exception as e:
            logger.warning(f"[SEED_TEXT] Gemini seed text failed for topic='{topic[:50]}...', age={age}: {e}")
            return None
        return None

    def _build_seeded_item(self, topic: str, fmt: str, seed: str) -> Dict[str, Any]:
        topic_title = topic.strip().title() or "General Knowledge"
        if fmt == "numeric_input":
            a, b = random.randint(2, 12), random.randint(2, 12)
            answer = a * b
            item = {
                "question": {
                    "content": f"{seed} What is {a} times {b}? [[☃ numeric-input 1]]",
                    "images": {},
                    "widgets": {
                        "numeric-input 1": {
                            "type": "numeric-input",
                            "graded": True,
                            "options": {
                                "coefficient": False,
                                "static": False,
                                "labelText": "",
                                "size": "normal",
                                "answers": [{"status": "correct", "value": answer, "maxError": 0.01, "simplify": "optional", "strict": False, "message": ""}],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"What operation do you need to find {a} times {b}?"},
                    {"content": f"Multiplication means repeated addition: {a} groups of {b}."},
                    {"content": f"Calculate: {a} x {b} = {answer}. The answer is {answer}."},
                ],
            }
        elif fmt == "dropdown":
            item = {
                "question": {
                    "content": f"{seed} Which answer is correct? [[☃ dropdown 1]]",
                    "images": {},
                    "widgets": {
                        "dropdown 1": {
                            "type": "dropdown",
                            "graded": True,
                            "options": {
                                "placeholder": "select one",
                                "choices": [
                                    {"content": f"A key concept in {topic_title}", "correct": True},
                                    {"content": "An unrelated idea from a different subject", "correct": False},
                                    {"content": "A common misconception about this topic", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"What is {topic_title} actually about? Focus on its core ideas."},
                    {"content": f"{topic_title} has specific principles that distinguish it from other subjects."},
                    {"content": f"The answer that describes a key concept in {topic_title} is correct."},
                ],
            }
        elif fmt == "orderer":
            order = [f"Introduction to {topic_title}", f"Core {topic_title} concepts", f"Practice {topic_title}", f"Apply {topic_title}"]
            shuffled = order[:]
            random.shuffle(shuffled)
            item = {
                "question": {
                    "content": f"{seed} Arrange these from foundational to advanced.",
                    "images": {},
                    "widgets": {
                        "orderer 1": {
                            "type": "orderer",
                            "graded": True,
                            "options": {
                                "layout": "horizontal",
                                "options": [{"content": v} for v in shuffled],
                                "correctOptions": [{"content": v} for v in order],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Which {topic_title} topic would you learn first?"},
                    {"content": "Start with introductions, then learn core concepts, then practice, then apply."},
                    {"content": f"Order: Introduction -> Core concepts -> Practice -> Apply {topic_title}."},
                ],
            }
        elif fmt == "radio_multi":
            item = {
                "question": {
                    "content": f"{seed} Which TWO are directly related to {topic_title}? Select all that apply.",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": True,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"Understanding the principles of {topic_title}", "correct": True},
                                    {"content": "A concept from a completely different subject", "correct": False},
                                    {"content": f"Applying {topic_title} to solve real problems", "correct": True},
                                    {"content": "Something unrelated to this field entirely", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Which options are actually about {topic_title}?"},
                    {"content": f"{topic_title} involves both understanding and application of concepts."},
                    {"content": f"The two options about understanding and applying {topic_title} are both correct."},
                ],
            }
        elif fmt == "expression":
            a, b = random.randint(2, 9), random.randint(1, 9)
            answer_val = f"{a + b}x"
            item = {
                "question": {
                    "content": f"{seed} Simplify: ${a}x + {b}x$ [[☃ expression 1]]",
                    "images": {},
                    "widgets": {
                        "expression 1": {
                            "type": "expression",
                            "graded": True,
                            "options": {
                                "buttonsVisible": "never",
                                "functions": ["f", "g", "h"],
                                "times": False,
                                "answerForms": [{"value": answer_val, "form": True, "simplify": False, "considered": "correct"}],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": "When you add like terms, what do you do with the coefficients?"},
                    {"content": f"${a}x + {b}x$ means {a} groups of $x$ plus {b} groups of $x$."},
                    {"content": f"Add the coefficients: {a} + {b} = {a + b}, so the answer is ${a + b}x$."},
                ],
            }
        elif fmt == "matcher":
            item = {
                "question": {
                    "content": f"{seed} Match each concept with its description. [[☃ matcher 1]]",
                    "images": {},
                    "widgets": {
                        "matcher 1": {
                            "type": "matcher",
                            "graded": True,
                            "options": {
                                "labels": ["Concept", "Description"],
                                "left": [f"{topic_title} fundamentals", f"{topic_title} methods", f"{topic_title} applications", f"{topic_title} analysis"],
                                "right": ["Core principles and definitions", "Techniques and procedures", "Real-world problem solving", "Critical evaluation of results"],
                                "orderMatters": True,
                                "padding": True,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Think about what each aspect of {topic_title} involves."},
                    {"content": "Fundamentals = basics, Methods = techniques, Applications = real-world use."},
                    {"content": "'Fundamentals' matches 'Core principles', 'Methods' matches 'Techniques', etc."},
                ],
            }
        elif fmt == "sorter":
            items_list = [f"Define {topic_title}", f"Explore examples", f"Practice problems", f"Master {topic_title}"]
            item = {
                "question": {
                    "content": f"{seed} Sort these milestones from first to last. [[☃ sorter 1]]",
                    "images": {},
                    "widgets": {
                        "sorter 1": {
                            "type": "sorter",
                            "graded": True,
                            "options": {
                                "correct": items_list,
                                "layout": "horizontal",
                                "padding": True,
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"What would be the very first step when learning {topic_title}?"},
                    {"content": "Start by defining the concept, then explore, practice, and finally master."},
                    {"content": f"Order: Define -> Explore examples -> Practice problems -> Master {topic_title}."},
                ],
            }
        elif fmt == "definition":
            item = {
                "question": {
                    "content": f"{seed}\n\nRead about [[☃ definition 1]] and answer below. What does this term refer to? [[☃ radio 1]]",
                    "images": {},
                    "widgets": {
                        "definition 1": {
                            "type": "definition",
                            "graded": False,
                            "options": {
                                "togglePrompt": topic_title,
                                "definition": f"A fundamental concept in {topic_title} that forms the basis of understanding this subject.",
                                "static": False,
                            },
                        },
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": False,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"A core concept essential to {topic_title}", "correct": True},
                                    {"content": "An advanced topic from a different subject", "correct": False},
                                    {"content": "Something unrelated to this field", "correct": False},
                                    {"content": "A historical figure from another discipline", "correct": False},
                                ],
                            },
                        },
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Re-read the definition. What does it say about {topic_title}?"},
                    {"content": f"The definition describes {topic_title} as a fundamental concept in this subject."},
                    {"content": f"Since it is fundamental to {topic_title}, the answer about a core concept is correct."},
                ],
            }
        else:
            # radio_single — skill-specific, not meta-question
            item = {
                "question": {
                    "content": f"{seed} How would you apply {topic_title} to solve this?",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": False,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"{topic_title} involves understanding concepts and applying them", "correct": True},
                                    {"content": f"{topic_title} is only about memorizing random facts", "correct": False},
                                    {"content": f"{topic_title} requires no practice at all", "correct": False},
                                    {"content": f"{topic_title} cannot be learned through examples", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False, "type": "multiple", "options": {"content": "", "images": {}, "widgets": {}}},
                "hints": [
                    {"content": f"Think about what you know about {topic_title} as a subject."},
                    {"content": f"Most subjects, including {topic_title}, involve both understanding and practice."},
                    {"content": f"The correct answer describes {topic_title} as involving concepts and application."},
                ],
            }
        # Always run repair to ensure Perseus compliance for all widget types
        item = self._repair_item(item, fmt=fmt)
        return item

    def _simple_fallback_question(self, skill_name: str, lesson_name: str, age: int, subject: str = "") -> Optional[Dict[str, Any]]:
        """Last-resort fallback: very simple prompt that generates a basic radio question."""
        if not self.client:
            return None
        subject_line = f"SUBJECT: {subject}\n" if subject else ""
        prompt = (
            f"{subject_line}"
            f"Create a simple multiple-choice question about: {skill_name} — {lesson_name}\n"
            f"Student age: {age}\n"
            f"The question MUST be specifically about {subject or skill_name}. Do NOT generate math/arithmetic problems unless the subject is math.\n\n"
            "Return ONLY this JSON (no markdown, no extra text):\n"
            "{\n"
            '  "question": {"content": "<question text> [[☃ radio 1]]", "images": {}, "widgets": {\n'
            '    "radio 1": {"type": "radio", "graded": true, "options": {"multipleSelect": false, "choices": [\n'
            '      {"content": "<choice A>", "correct": false},\n'
            '      {"content": "<choice B>", "correct": true},\n'
            '      {"content": "<choice C>", "correct": false},\n'
            '      {"content": "<choice D>", "correct": false}\n'
            "    ]}}\n"
            "  }},\n"
            '  "answerArea": {"calculator": false},\n'
            '  "hints": [\n'
            '    {"content": "<hint 1: guiding question>"},\n'
            '    {"content": "<hint 2: explain the concept>"},\n'
            '    {"content": "<hint 3: walk through solution>"}\n'
            "  ]\n"
            "}\n"
            "RULES: Exactly ONE choice must be correct. Question must test real knowledge of the topic."
        )
        try:
            def _call() -> Any:
                return self.client.models.generate_content(
                    model=self.fast_model, contents=prompt, config={"temperature": 0.5},
                )
            response = _run_with_timeout(_call, timeout_s=15)
            parsed = self._extract_json(response.text or "")
            if isinstance(parsed, dict) and parsed:
                parsed = self._repair_item(parsed, fmt="radio_single")
                if self._validate_item(parsed, fmt="radio_single"):
                    logger.info(f"[GENERATE] Simple fallback succeeded for {skill_name}")
                    return parsed
        except Exception as e:
            logger.warning(f"[GENERATE] Simple fallback also failed: {e}")
        fb = self._fallback_question(skill_name, 8, "radio_single", 0.5)
        return self._repair_item(fb["item"], fmt="radio_single") if fb else None

    def _get_image_probability(self, skill_name: str, lesson_name: str) -> float:
        """Determine image probability based on topic keywords. First match wins."""
        if IMAGE_PROBABILITY <= 0.0:
            return 0.0
        combined = f"{skill_name} {lesson_name}".lower()
        for keywords, prob in IMAGE_TOPIC_KEYWORDS:
            if any(kw in combined for kw in keywords):
                # Scale by global multiplier (default 0.20 = no scaling)
                return min(1.0, prob * (IMAGE_PROBABILITY / 0.20))
        return IMAGE_PROBABILITY  # Fallback: global default

    def _generate_image(self, question_text: str, skill_name: str, lesson_name: str, age: int) -> Optional[str]:
        """Generate an educational image via Gemini, save to disk, return URL path."""
        if not self.client:
            return None
        image_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

        from services.DashSystem.ai_question_prompts import build_image_prompt
        prompt = build_image_prompt(skill_name, lesson_name, age, question_text)

        try:
            def _call_image() -> Any:
                return self.client.models.generate_content(
                    model=image_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

            response = _run_with_timeout(_call_image, timeout_s=60)

            candidates = getattr(response, "candidates", None)
            if not isinstance(candidates, list) or len(candidates) == 0 or not candidates[0]:
                logger.warning("[IMAGE] Gemini returned empty candidates")
                return None
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) if content else None
            if not parts:
                logger.warning("[IMAGE] Gemini response has no content parts")
                return None
            for part in parts:
                if getattr(part, 'inline_data', None) is not None:
                    img_data = part.inline_data.data
                    if not img_data:
                        logger.warning("[IMAGE] Gemini returned inline_data with empty data")
                        continue
                    img_hash = hashlib.sha256(img_data).hexdigest()[:16]
                    filename = f"{img_hash}.png"
                    filepath = os.path.join(STATIC_IMAGES_DIR, filename)
                    if not os.path.exists(filepath):
                        try:
                            with open(filepath, "wb") as f:
                                f.write(part.inline_data.data)
                        except (IOError, OSError) as write_err:
                            logger.warning(f"[IMAGE] Failed to write image file: {write_err}")
                            return None
                    logger.info(f"[IMAGE] Generated image: {filename} for skill={skill_name}")
                    return f"{IMAGE_BASE_URL}/static/images/{filename}"
        except FutureTimeoutError:
            logger.warning("[IMAGE] Image generation timed out")
        except Exception as e:
            logger.warning(f"[IMAGE] Image generation failed: {e}")
        return None

    def _inject_image(self, item: Dict[str, Any], image_url: str, skill_name: str) -> Dict[str, Any]:
        """Add an image widget to an existing Perseus question."""
        item["question"]["widgets"]["image 1"] = {
            "type": "image",
            "graded": False,
            "version": {"major": 0, "minor": 0},
            "alignment": "block",
            "static": False,
            "options": {
                "backgroundImage": {"url": image_url, "width": 400, "height": 300},
                "alt": f"Illustration for {skill_name}",
                "caption": "",
            },
        }
        item["question"]["content"] = "[[☃ image 1]]\n\n" + item["question"]["content"]
        return item

    # ------------------------------------------------------------------
    # Math answer verification (SymPy)
    # ------------------------------------------------------------------

    # Math/science/english/history verification is now handled by DeterministicVerifier
    # (see deterministic_verifier.py) — called from generate_for_skill()

    def generate_responsive_hint(
        self,
        skill_name: str,
        question_text: str,
        selected_answer: str,
        correct_answer: str,
        age: int = 10,
        misconception: str = "",
    ) -> Optional[str]:
        """Call Gemini to generate a targeted Socratic hint for a wrong answer."""
        if not self.client:
            return None
        try:
            from services.DashSystem.ai_question_prompts import build_responsive_hint_prompt
            prompt = build_responsive_hint_prompt(
                skill_name=skill_name,
                question_text=question_text,
                selected_answer=selected_answer,
                correct_answer=correct_answer,
                age=age,
                misconception=misconception,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            hint_text = response.text.strip() if response.text else None
            if hint_text:
                logger.info(f"[RESPONSIVE_HINT] Generated hint for skill={skill_name} ({len(hint_text)} chars)")
            else:
                logger.warning(f"[RESPONSIVE_HINT] Gemini returned empty response for skill={skill_name}")
            return hint_text
        except Exception as e:
            logger.warning(f"[RESPONSIVE_HINT] Generation failed: {e}")
            return None

    def generate_for_skill(
        self,
        skill_name: str,
        lesson_name: str,
        difficulty: float,
        age: int,
        fmt: str,
        memory: Dict[str, Any],
        khan_example: str = "",
        fast_mode: bool = False,
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a question for a specific DASH skill using curriculum-aligned prompting.

        Uses Axiom-inspired 3-stage pipeline: Generate → Verify → Refine.
        On verification failure, specific error feedback is injected into the next prompt.

        When fast_mode=True (assessment JIT), uses 1 attempt with a shorter timeout
        and accepts the question even if verification fails (logs a warning).

        Returns a Perseus JSON dict (question + answerArea + hints) or None on failure.
        """
        if not self.client:
            return None

        from services.DashSystem.ai_question_prompts import build_skill_question_prompt

        item = None
        verification_feedback = ""  # Accumulates failure reasons across retries
        last_verification = None

        max_attempts = 1 if fast_mode else 3
        # Try up to max_attempts: generate → verify → refine with feedback
        for attempt in range(max_attempts):
            try:
                prompt = build_skill_question_prompt(
                    skill_name=skill_name,
                    lesson_name=lesson_name,
                    difficulty=difficulty,
                    age=age,
                    fmt=fmt,
                    memory=memory,
                    khan_example=khan_example,
                    subject=subject,
                )
                # Inject verification feedback from previous failed attempt
                if verification_feedback:
                    prompt += (
                        "\n\nCRITICAL CORRECTIONS (your previous attempt had errors):\n"
                        f"{verification_feedback}\n"
                        "Fix these specific issues in your new question."
                    )

                active_model = self.fast_model if fast_mode else self.model

                def _call_gemini() -> Any:
                    return self.client.models.generate_content(
                        model=active_model,
                        contents=prompt,
                        config={"temperature": 0.6 + (attempt * 0.1)},
                    )

                timeout_s = 15 if fast_mode else 45
                response = _run_with_timeout(_call_gemini, timeout_s=timeout_s)

                raw = response.text or ""
                if not raw.strip():
                    logger.warning(f"[GENERATE] Attempt {attempt+1}: empty response, retrying")
                    continue

                parsed = self._extract_json(raw)
                if not isinstance(parsed, dict) or not parsed:
                    logger.warning(f"[GENERATE] Attempt {attempt+1}: _extract_json returned non-dict/empty, retrying")
                    continue
                parsed = self._repair_item(parsed, fmt=fmt)
                if not self._validate_item(parsed, fmt=fmt):
                    logger.warning(f"[GENERATE] Attempt {attempt+1}: validation failed, retrying")
                    continue

                # Subject-content cross-validation
                if not self._validate_subject_content(parsed, subject=subject, fmt=fmt):
                    logger.warning(f"[GENERATE] Attempt {attempt+1}: subject mismatch for {subject}, retrying")
                    verification_feedback += f"\n- Question content does not match the subject '{subject}'. Do NOT use math expressions or letter-counting for non-STEM subjects."
                    continue

                # Deterministic verification (all subjects)
                vr = self.verifier.verify(parsed, skill_name, lesson_name, fmt, age, difficulty)
                last_verification = vr
                if not vr.passed:
                    if fast_mode:
                        # In fast mode (assessment JIT), accept unverified questions
                        # rather than burning time on retries
                        logger.warning(
                            f"[GENERATE] Fast-mode: accepting unverified question "
                            f"(failures={len(vr.failures)}, {vr.elapsed_ms:.0f}ms)"
                        )
                        item = parsed
                        item["_verification"] = {
                            "passed": False,
                            "subject": vr.subject,
                            "checks_run": vr.checks_run,
                            "confidence": vr.confidence,
                            "fast_mode": True,
                        }
                        break
                    verification_feedback = "\n".join(f"- {f}" for f in vr.failures)
                    logger.warning(
                        f"[GENERATE] Attempt {attempt+1}: verification failed "
                        f"(subject={vr.subject}, checks={vr.checks_run}, "
                        f"failures={len(vr.failures)}, {vr.elapsed_ms:.0f}ms), refining..."
                    )
                    continue

                # Passed all checks
                logger.info(
                    f"[GENERATE] Verified (subject={vr.subject}, "
                    f"checks={vr.checks_run}, conf={vr.confidence:.2f}, "
                    f"{vr.elapsed_ms:.0f}ms)"
                )
                item = parsed
                item["_verification"] = {
                    "passed": True,
                    "subject": vr.subject,
                    "checks_run": vr.checks_run,
                    "confidence": vr.confidence,
                }
                break
            except FutureTimeoutError:
                logger.warning(f"[GENERATE] Attempt {attempt+1}: timeout")
            except Exception as e:
                logger.warning(f"[GENERATE] Attempt {attempt+1}: error: {e}")

        # Fallback: try a simplified radio_single prompt as last resort
        if item is None:
            logger.warning(f"[GENERATE] All attempts failed for {skill_name}/{fmt}, trying simple fallback")
            item = self._simple_fallback_question(skill_name, lesson_name, age, subject=subject)

        if item is None:
            return None

        # Add images even in fast_mode but with reduced probability and shorter timeout
        # Images are important for visual learning questions
        topic_image_prob = self._get_image_probability(skill_name, lesson_name)
        # In fast mode, reduce probability by 50% to balance speed vs quality
        effective_prob = topic_image_prob * (0.5 if fast_mode else 1.0)
        if fmt in IMAGE_ELIGIBLE_FORMATS and random.random() < effective_prob:
            q_text = item.get("question", {}).get("content", "")
            image_url = self._generate_image(q_text, skill_name, lesson_name, age)
            if image_url:
                item = self._inject_image(item, image_url, skill_name)
            else:
                # Image generation failed - strip any image references from question text
                logger.warning(f"[IMAGE] Generation failed but question may reference image - cleaning text")
                item["question"]["content"] = item["question"]["content"].replace("shown in the image", "shown").replace("in the picture", "").replace("in the diagram", "")

        return item

    def _reuse_question(self, topic: str, age: int, fmt: str, difficulty: float) -> Optional[Dict[str, Any]]:
        age_band = self._age_band(age)
        reuse_filter: Dict[str, Any] = {
            "topic_norm": topic.lower(),
            "age_band": age_band,
            "format": fmt,
            "quality.topic_grounding_ok": True,
            "difficulty": {"$gte": max(0, difficulty - 0.2), "$lte": min(1, difficulty + 0.2)},
        }
        if self.gemini_only:
            reuse_filter["source"] = {"$in": ["gemini", "gemini_derived"]}
        doc = mongo_db.db["content_v1_questions"].find_one(
            reuse_filter,
            sort=[("used_count", 1), ("created_at", -1)],
        )
        return doc

    def _seed_from_existing_gemini(self, topic: str, age: int) -> Optional[str]:
        age_band = self._age_band(age)
        # Prefer same topic + age band, then broaden search.
        candidates = [
            {"topic_norm": topic.lower(), "age_band": age_band, "source": {"$in": ["gemini", "gemini_derived"]}},
            {"topic_norm": topic.lower(), "source": {"$in": ["gemini", "gemini_derived"]}},
            {"age_band": age_band, "source": {"$in": ["gemini", "gemini_derived"]}},
            {"source": {"$in": ["gemini", "gemini_derived"]}},
        ]
        for query in candidates:
            doc = mongo_db.db["content_v1_questions"].find_one(query, sort=[("created_at", -1)])
            if not doc:
                continue
            seed = (((doc.get("item") or {}).get("question") or {}).get("content") or "").strip()
            if seed:
                return re.sub(r"\s+", " ", seed)[:240]
        return None

    def create_or_reuse_question(
        self,
        *,
        user_id: str,
        profile_id: str,
        learning_goal: str,
        topic: str,
        age: int,
        difficulty: float,
        fmt: str,
        memory: Dict[str, Any],
        allow_reuse: bool = True,
    ) -> Dict[str, Any]:
        if allow_reuse:
            reused = self._reuse_question(topic, age, fmt, difficulty)
            if reused:
                mongo_db.db["content_v1_questions"].update_one({"_id": reused["_id"]}, {"$inc": {"used_count": 1}})
                reused.pop("_id", None)
                return reused

        generated = self._gemini_question(topic, age, fmt, difficulty, memory)
        source = "gemini"
        if generated is None:
            if self.gemini_only:
                # Derive a valid question from previously Gemini-generated content.
                seed = self._seed_from_existing_gemini(topic, age)
                if seed:
                    generated = self._build_seeded_item(topic, fmt, seed)
                    generated = self._repair_item(generated, fmt=fmt)
                    source = "gemini_derived"
                else:
                    # Reliability fallback: never hard-fail first question creation when Gemini seed is unavailable.
                    # Keep output subject-scoped and schema-valid via deterministic local generator + repair.
                    generated = self._fallback_question(topic, age, fmt, difficulty)["item"]
                    generated = self._repair_item(generated, fmt=fmt)
                    source = "fallback_local"
            else:
                generated = self._fallback_question(topic, age, fmt, difficulty)["item"]
                generated = self._repair_item(generated, fmt=fmt)
                source = "fallback"

        question_id = f"c1_{uuid.uuid4().hex[:10]}"
        doc = {
            "question_id": question_id,
            "profile_id": profile_id,
            "user_id": user_id,
            "learning_goal": learning_goal,
            "topic": topic,
            "topic_norm": topic.lower(),
            "format": fmt,
            "difficulty": difficulty,
            "age": age,
            "age_band": self._age_band(age),
            "item": generated,
            "source": source,
            "quality": {"topic_grounding_ok": True},
            "used_count": 1,
            "created_at": datetime.utcnow(),
        }
        mongo_db.db["content_v1_questions"].insert_one(doc)
        doc.pop("_id", None)  # Strip ObjectId added by insert_one
        return doc

    def _next_topic(self, profile: Dict[str, Any]) -> Tuple[str, int]:
        steps = profile.get("learning_plan", {}).get("steps", [])
        idx = int(profile.get("current_step_index", 0))
        if not steps:
            return (profile.get("learning_goal", "General learning"), 0)
        idx = max(0, min(idx, len(steps) - 1))
        step = steps[idx]
        return (step.get("topic") or step.get("title") or profile.get("learning_goal", "General learning"), idx)

    def prime_queue_from_seed(
        self,
        *,
        profile_id: str,
        user_id: str,
        learning_goal: str,
        topic: str,
        age: int,
        difficulty: float,
        step_index: int,
        seed_text: str,
        count: int = 5,
    ) -> int:
        """
        Fast pre-generation path to keep queue deep while user is on Q1.
        Builds valid, topic-aware variants from a Gemini seed text.
        """
        queue = mongo_db.db["content_v1_queue"]
        ready_now = queue.count_documents({"profile_id": profile_id, "status": "ready"})
        needed = max(0, count - ready_now)
        if needed == 0:
            return ready_now

        for idx in range(needed):
            fmt = SUPPORTED_FORMATS[idx % len(SUPPORTED_FORMATS)]
            item = self._build_seeded_item(topic, fmt, seed_text)
            item = self._repair_item(item, fmt=fmt)
            qid = f"c1_{uuid.uuid4().hex[:10]}"
            doc = {
                "question_id": qid,
                "profile_id": profile_id,
                "user_id": user_id,
                "learning_goal": learning_goal,
                "topic": topic,
                "topic_norm": topic.lower(),
                "format": fmt,
                "difficulty": difficulty,
                "age": age,
                "age_band": self._age_band(age),
                "item": item,
                "source": "gemini_derived",
                "quality": {"topic_grounding_ok": True},
                "used_count": 0,
                "created_at": datetime.utcnow(),
            }
            mongo_db.db["content_v1_questions"].insert_one(doc)
            queue.insert_one(
                {
                    "profile_id": profile_id,
                    "question_id": qid,
                    "step_index": step_index,
                    "topic": topic,
                    "status": "ready",
                    "created_at": datetime.utcnow(),
                }
            )

        return queue.count_documents({"profile_id": profile_id, "status": "ready"})

    def ensure_queue_depth(self, profile_id: str, target_depth: int = 5) -> int:
        profiles = mongo_db.db["content_v1_profiles"]
        queue = mongo_db.db["content_v1_queue"]
        profile = profiles.find_one({"learner_profile_id": profile_id})
        if not profile:
            return 0

        ready_count = queue.count_documents({"profile_id": profile_id, "status": "ready"})
        needed = max(0, target_depth - ready_count)
        memory = self._memory_context(profile["user_id"])
        existing_question_ids = set(
            doc["question_id"]
            for doc in queue.find(
                {"profile_id": profile_id, "status": {"$in": ["ready", "served"]}},
                {"question_id": 1, "_id": 0},
            )
        )

        for _ in range(needed):
            topic, step_index = self._next_topic(profile)
            inserted = False

            # Try reuse first, then force-create new questions to guarantee depth.
            for _attempt in range(30):
                fmt = random.choice(SUPPORTED_FORMATS)
                difficulty = float(profile.get("difficulty_cursor", 0.35))
                qid: Optional[str] = None

                # First half attempts allow reuse, second half force new generation.
                force_new = _attempt >= 6

                if not force_new:
                    reused = self._reuse_question(topic, profile.get("age", 12), fmt, difficulty)
                    if reused:
                        qid = reused["question_id"]
                        mongo_db.db["content_v1_questions"].update_one({"_id": reused["_id"]}, {"$inc": {"used_count": 1}})

                if qid is None:
                    if force_new and self.gemini_only:
                        # Fast queue top-up path: derive from existing Gemini seed to avoid long blocking retries.
                        seed = self._seed_from_existing_gemini(topic, profile.get("age", 12))
                        if seed:
                            generated = self._build_seeded_item(topic, fmt, seed)
                            generated = self._repair_item(generated, fmt=fmt)
                            question_doc = {
                                "question_id": f"c1_{uuid.uuid4().hex[:10]}",
                                "profile_id": profile_id,
                                "user_id": profile["user_id"],
                                "learning_goal": profile.get("learning_goal", "General learning"),
                                "topic": topic,
                                "topic_norm": topic.lower(),
                                "format": fmt,
                                "difficulty": difficulty,
                                "age": profile.get("age", 12),
                                "age_band": self._age_band(profile.get("age", 12)),
                                "item": generated,
                                "source": "gemini_derived",
                                "quality": {"topic_grounding_ok": True},
                                "used_count": 1,
                                "created_at": datetime.utcnow(),
                            }
                            mongo_db.db["content_v1_questions"].insert_one(question_doc)
                            qid = question_doc["question_id"]
                        else:
                            continue
                    else:
                        try:
                            question_doc = self.create_or_reuse_question(
                                user_id=profile["user_id"],
                                profile_id=profile_id,
                                learning_goal=profile.get("learning_goal", "General learning"),
                                topic=topic,
                                age=profile.get("age", 12),
                                difficulty=difficulty,
                                fmt=fmt,
                                memory=memory,
                                allow_reuse=not force_new,
                            )
                        except RuntimeError:
                            # Gemini-only mode can fail transiently; keep trying.
                            continue
                        qid = question_doc["question_id"]

                if qid in existing_question_ids:
                    continue

                try:
                    queue.insert_one(
                        {
                            "profile_id": profile_id,
                            "question_id": qid,
                            "step_index": step_index,
                            "topic": topic,
                            "status": "ready",
                            "created_at": datetime.utcnow(),
                        }
                    )
                    existing_question_ids.add(qid)
                    ready_count += 1
                    inserted = True
                    break
                except DuplicateKeyError:
                    existing_question_ids.add(qid)
                    continue

            if not inserted:
                # Skip silently; caller still gets the queue count we could materialize.
                continue

        return ready_count

    def pop_next_question(self, profile_id: str) -> Optional[Dict[str, Any]]:
        queue = mongo_db.db["content_v1_queue"]
        item = queue.find_one_and_update(
            {"profile_id": profile_id, "status": "ready"},
            {"$set": {"status": "served", "served_at": datetime.utcnow()}},
            sort=[("quality_score", -1), ("created_at", 1)],
        )
        if not item:
            return None

        question_doc = mongo_db.db["content_v1_questions"].find_one({"question_id": item["question_id"]})
        if not question_doc:
            return None

        return self.to_question_payload(question_doc, item.get("topic", "Content V1"), int(item.get("step_index", 0)))

    def to_question_payload(self, question_doc: Dict[str, Any], topic: str, step_index: int) -> Dict[str, Any]:
        payload = dict(question_doc["item"])
        payload["dash_metadata"] = {
            "dash_question_id": question_doc["question_id"],
            "unit_name": topic,
            "lesson_name": f"STEP_{step_index + 1}",
            "exercise_name": "GENERATED PRACTICE",
            "mongodb_id": question_doc["question_id"],
            "content_v1": {
                "topic": question_doc.get("topic"),
                "format": question_doc.get("format"),
                "difficulty": question_doc.get("difficulty"),
                "source": question_doc.get("source", "unknown"),
            },
        }
        return payload

    def submit_result(self, profile_id: str, question_id: str, is_correct: bool, response_time_ms: int, signals: Dict[str, Any]) -> Dict[str, Any]:
        profiles = mongo_db.db["content_v1_profiles"]
        attempts = mongo_db.db["content_v1_attempts"]
        qdoc = mongo_db.db["content_v1_questions"].find_one({"question_id": question_id}) or {}
        topic = qdoc.get("topic_norm", "general")

        profile = profiles.find_one({"learner_profile_id": profile_id})
        if not profile:
            return {"updated_progress": {}, "next_ready_count": 0}

        mastery = dict(profile.get("topic_mastery", {}))
        current = float(mastery.get(topic, 0.0))
        score = 1.0 if is_correct else 0.0
        updated = round((0.7 * current) + (0.3 * score), 4)
        mastery[topic] = updated

        attempts.insert_one(
            {
                "profile_id": profile_id,
                "question_id": question_id,
                "topic": topic,
                "is_correct": is_correct,
                "response_time_ms": response_time_ms,
                "signals": signals,
                "created_at": datetime.utcnow(),
            }
        )

        new_difficulty = float(profile.get("difficulty_cursor", 0.35)) + (0.03 if is_correct else -0.02)
        new_difficulty = max(0.1, min(0.9, new_difficulty))

        step_index = int(profile.get("current_step_index", 0))
        steps = profile.get("learning_plan", {}).get("steps", [])
        step_topic = (steps[step_index].get("topic", "")).lower() if steps and step_index < len(steps) else ""

        # Progression gate: either strong mastery, or enough recent attempts with reasonable accuracy.
        if step_topic:
            recent_attempts = list(
                attempts.find({"profile_id": profile_id, "topic": step_topic}).sort("created_at", -1).limit(5)
            )
            recent_count = len(recent_attempts)
            recent_accuracy = (
                sum(1 for a in recent_attempts if a.get("is_correct")) / recent_count if recent_count else 0.0
            )
            can_advance = mastery.get(step_topic, 0) >= 0.75 or (recent_count >= 3 and recent_accuracy >= 0.67)
            if can_advance and step_index < len(steps) - 1:
                step_index += 1

        profiles.update_one(
            {"learner_profile_id": profile_id},
            {
                "$set": {
                    "topic_mastery": mastery,
                    "difficulty_cursor": new_difficulty,
                    "current_step_index": step_index,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        ready = mongo_db.db["content_v1_queue"].count_documents({"profile_id": profile_id, "status": "ready"})
        return {
            "updated_progress": {
                "topic_mastery": mastery,
                "difficulty_cursor": new_difficulty,
                "current_step_index": step_index,
            },
            "next_ready_count": ready,
        }
