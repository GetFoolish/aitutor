"""
OpenMAIC Provider — generates questions by calling a running OpenMAIC service.

Integration flow:
  1. POST /api/generate-classroom  → {jobId, pollUrl}
  2. Poll GET /api/generate-classroom/{jobId} until status == "succeeded"
  3. GET /api/classroom?id={classroomId}  → {classroom: {stage, scenes}}
  4. Extract quiz scenes, map QuizQuestion → Perseus JSON
  5. Return list of Perseus dicts, tagged with source="openmaic"

Usage:
    provider = OpenMAICProvider(base_url="http://localhost:3333")
    questions = provider.generate_questions_for_skill(
        skill_name="Addition of fractions",
        age=10,
        subject="math",
        count=5,
    )
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Maximum seconds to wait for a generation job to complete
GENERATION_TIMEOUT_S = 120
# How often to poll (seconds)
POLL_INTERVAL_S = 5


class OpenMAICProvider:
    def __init__(self, base_url: str = "http://localhost:3333") -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Quick health check — returns True if the service responds."""
        try:
            r = self.session.get(f"{self.base_url}/api/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def generate_questions_for_skill(
        self,
        skill_name: str,
        age: int,
        subject: str = "",
        count: int = 5,
        difficulty: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Generate Perseus-format questions for a skill via OpenMAIC.

        Returns a list of Perseus JSON dicts (may be fewer than `count` on failure).
        Each dict has an extra 'openmaic_metadata' key with source info.
        """
        requirement = self._build_requirement(skill_name, age, subject, count)

        try:
            job = self._submit_job(requirement)
            job_id = job["jobId"]
            logger.info(f"[OPENMAIC] Job submitted: {job_id} for skill '{skill_name}'")
        except Exception as e:
            logger.warning(f"[OPENMAIC] Failed to submit job: {e}")
            return []

        # Poll for completion
        result = self._poll_until_done(job_id)
        if not result:
            logger.warning(f"[OPENMAIC] Job {job_id} timed out or failed")
            return []

        classroom_id = result.get("classroomId") or result.get("id")
        if not classroom_id:
            logger.warning(f"[OPENMAIC] No classroomId in result: {result}")
            return []

        # Fetch full classroom
        try:
            classroom = self._fetch_classroom(classroom_id)
        except Exception as e:
            logger.warning(f"[OPENMAIC] Failed to fetch classroom {classroom_id}: {e}")
            return []

        # Extract and convert quiz questions
        questions = self._extract_questions(classroom, skill_name, difficulty)
        logger.info(
            f"[OPENMAIC] Extracted {len(questions)} questions from classroom {classroom_id}"
        )
        return questions[:count]

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def _submit_job(self, requirement: str) -> Dict[str, Any]:
        payload = {
            "requirement": requirement,
            "language": "en-US",
            "enableWebSearch": False,
            "enableImageGeneration": False,
            "enableVideoGeneration": False,
            "enableTTS": False,
        }
        r = self.session.post(
            f"{self.base_url}/api/generate-classroom",
            json=payload,
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", r.json())

    def _poll_until_done(self, job_id: str) -> Optional[Dict[str, Any]]:
        deadline = time.monotonic() + GENERATION_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                r = self.session.get(
                    f"{self.base_url}/api/generate-classroom/{job_id}",
                    timeout=10,
                )
                r.raise_for_status()
                body = r.json().get("data", r.json())
                status = body.get("status")
                step = body.get("step", "")
                logger.debug(f"[OPENMAIC] Job {job_id}: status={status} step={step}")

                if status == "succeeded":
                    return body.get("result", body)
                if status == "failed":
                    logger.warning(
                        f"[OPENMAIC] Job {job_id} failed: {body.get('error')}"
                    )
                    return None
            except Exception as e:
                logger.debug(f"[OPENMAIC] Poll error for {job_id}: {e}")

            time.sleep(POLL_INTERVAL_S)

        return None

    def _fetch_classroom(self, classroom_id: str) -> Dict[str, Any]:
        r = self.session.get(
            f"{self.base_url}/api/classroom",
            params={"id": classroom_id},
            timeout=15,
        )
        r.raise_for_status()
        body = r.json().get("data", r.json())
        return body.get("classroom", body)

    # ------------------------------------------------------------------
    # Conversion: OpenMAIC QuizQuestion → Perseus JSON
    # ------------------------------------------------------------------

    def _build_requirement(
        self, skill_name: str, age: int, subject: str, count: int
    ) -> str:
        subject_str = f" ({subject})" if subject else ""
        return (
            f"Create an educational lesson with {count} quiz questions "
            f"about: {skill_name}{subject_str}. "
            f"Target audience: students around {age} years old. "
            f"Include a mix of single-choice and short-answer questions. "
            f"Focus entirely on quiz questions — minimal slides."
        )

    def _extract_questions(
        self,
        classroom: Dict[str, Any],
        skill_name: str,
        difficulty: float,
    ) -> List[Dict[str, Any]]:
        scenes = classroom.get("scenes", [])
        questions: List[Dict[str, Any]] = []

        for scene in scenes:
            content = scene.get("content", {})
            if content.get("type") != "quiz":
                continue
            for q in content.get("questions", []):
                perseus = self._quiz_question_to_perseus(q, skill_name, difficulty)
                if perseus:
                    questions.append(perseus)

        return questions

    def _quiz_question_to_perseus(
        self,
        q: Dict[str, Any],
        skill_name: str,
        difficulty: float,
    ) -> Optional[Dict[str, Any]]:
        """Convert a single OpenMAIC QuizQuestion to Perseus JSON."""
        q_type = q.get("type", "single")
        question_text = (q.get("question") or "").strip()
        if not question_text:
            return None

        analysis = (q.get("analysis") or "").strip()
        options = q.get("options", [])  # [{label, value}]
        answer = q.get("answer", [])    # ["A"], ["A","C"], or [] for short_answer

        if q_type in ("single", "multiple") and options:
            return self._build_radio_perseus(
                question_text, options, answer, analysis, q_type == "multiple"
            )
        elif q_type == "short_answer":
            return self._build_expression_perseus(question_text, answer, analysis)
        else:
            # Fallback: treat as single-choice if options exist
            if options:
                return self._build_radio_perseus(question_text, options, answer, analysis, False)
            return self._build_expression_perseus(question_text, answer, analysis)

    def _build_radio_perseus(
        self,
        question: str,
        options: List[Dict],
        answer: List[str],
        analysis: str,
        multi: bool,
    ) -> Dict[str, Any]:
        widget_id = "radio 1"
        choices = []
        for opt in options:
            label = (opt.get("label") or "").strip()
            value = (opt.get("value") or "").strip()
            if not label:
                continue
            choices.append({
                "content": label,
                "correct": value in answer,
            })

        if not choices:
            return None

        # Ensure at least one correct answer is marked
        if not any(c.get("correct") for c in choices):
            choices[0]["correct"] = True

        perseus = {
            "question": {
                "content": f"{question}\n\n[[☃ {widget_id}]]",
                "images": {},
                "widgets": {
                    widget_id: {
                        "type": "radio",
                        "graded": True,
                        "options": {
                            "choices": choices,
                            "randomize": False,
                            "multipleSelect": multi,
                            "displayCount": None,
                            "hasNoneOfTheAbove": False,
                            "countChoices": False,
                        },
                        "version": {"major": 1, "minor": 0},
                    }
                },
            },
            "answerArea": {
                "calculator": False,
                "chi2Table": False,
                "periodicTable": False,
                "tTable": False,
                "zTable": False,
            },
            "hints": (
                [{"replace": False, "content": analysis, "images": {}, "widgets": {}}]
                if analysis
                else []
            ),
            "_version": 0,
            "_source": "openmaic",
        }
        return perseus

    def _build_expression_perseus(
        self,
        question: str,
        answer: List[str],
        analysis: str,
    ) -> Dict[str, Any]:
        """Short-answer question → expression widget."""
        widget_id = "expression 1"
        correct_val = answer[0] if answer else ""

        perseus = {
            "question": {
                "content": f"{question}\n\n[[☃ {widget_id}]]",
                "images": {},
                "widgets": {
                    widget_id: {
                        "type": "expression",
                        "graded": True,
                        "options": {
                            "answerForms": [
                                {
                                    "value": correct_val,
                                    "form": False,
                                    "simplify": False,
                                    "considered": "correct",
                                }
                            ],
                            "times": False,
                            "buttonSets": ["basic"],
                            "functions": [],
                        },
                        "version": {"major": 1, "minor": 0},
                    }
                },
            },
            "answerArea": {
                "calculator": False,
                "chi2Table": False,
                "periodicTable": False,
                "tTable": False,
                "zTable": False,
            },
            "hints": (
                [{"replace": False, "content": analysis, "images": {}, "widgets": {}}]
                if analysis
                else []
            ),
            "_version": 0,
            "_source": "openmaic",
        }
        return perseus
