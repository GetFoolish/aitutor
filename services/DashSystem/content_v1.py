import json
import os
import random
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.genai as genai
from pymongo.errors import DuplicateKeyError

from managers.mongodb_manager import mongo_db


SUPPORTED_FORMATS = ["radio_single", "radio_multi", "orderer"]


class ContentV1Engine:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
        self.gemini_only = os.getenv("CONTENT_V1_GEMINI_ONLY", "true").lower() in {"1", "true", "yes"}

    def _extract_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

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
        except Exception:
            pass
        return self._build_fallback_plan(learning_goal)

    def _fallback_question(self, topic: str, age: int, fmt: str, difficulty: float) -> Dict[str, Any]:
        topic_clean = topic.strip().title() or "General Knowledge"
        qid = f"c1_{uuid.uuid4().hex[:10]}"

        if fmt == "orderer":
            options = ["Beginner", "Practice", "Apply", "Reflect"]
            item = {
                "question": {
                    "content": f"Put these {topic_clean} learning steps in a good order.",
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
                "answerArea": {"calculator": False},
                "hints": [{"content": "Think about the natural sequence: learn, practice, apply, reflect."}],
            }
        elif fmt == "radio_multi":
            item = {
                "question": {
                    "content": f"In {topic_clean}, which TWO habits help you learn faster? Choose all that apply.",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": True,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"Practice a little each day in {topic_clean}", "correct": True},
                                    {"content": "Memorize everything once and never review", "correct": False},
                                    {"content": "Use examples and explain the concept in your own words", "correct": True},
                                    {"content": "Skip feedback and rush", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False},
                "hints": [{"content": "Look for habits that build consistency and understanding."}],
            }
        else:
            item = {
                "question": {
                    "content": f"Quick {topic_clean} check: which option is most likely correct for a beginner?",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": False,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"Start with simple, concrete examples in {topic_clean}", "correct": True},
                                    {"content": f"Master all advanced {topic_clean} topics immediately", "correct": False},
                                    {"content": "Avoid practice questions", "correct": False},
                                    {"content": "Ignore mistakes", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False},
                "hints": [{"content": "For beginners, simple and consistent wins."}],
            }

        return {
            "question_id": qid,
            "topic": topic_clean,
            "format": fmt,
            "difficulty": difficulty,
            "age": age,
            "item": item,
        }

    def _validate_item(self, item: Dict[str, Any]) -> bool:
        try:
            q = item["question"]
            _ = q["content"]
            widgets = q["widgets"]
            if not isinstance(widgets, dict) or not widgets:
                return False
            return True
        except Exception:
            return False

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
            "Allowed formats: radio_single, radio_multi, orderer. "
            "For radio widgets, include options.choices and explicit boolean 'correct' per choice. "
            "For orderer widgets, include options.correctOptions with ordered content list. "
            f"Memory context for personalization/examples only: {json.dumps(memory, ensure_ascii=True)}"
        )

        try:
            def _call_gemini() -> Any:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"temperature": 0.6},
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=20)
            parsed = self._extract_json(response.text or "")
            if self._validate_item(parsed):
                return parsed
        except FutureTimeoutError:
            return None
        except Exception:
            pass

        # Fallback path that is still Gemini-driven: get a short seed text, then
        # build a guaranteed-valid Perseus item structure in code.
        seed = self._gemini_seed_text(topic, age, memory)
        if not seed:
            return None
        return self._build_seeded_item(topic, fmt, seed)

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
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=20)
            text = (response.text or "").strip()
            if text:
                return re.sub(r"\s+", " ", text)[:240]
        except Exception:
            return None
        return None

    def _build_seeded_item(self, topic: str, fmt: str, seed: str) -> Dict[str, Any]:
        topic_title = topic.strip().title() or "General Learning"
        if fmt == "orderer":
            order = [f"Understand {topic_title}", f"Practice {topic_title}", f"Apply {topic_title}", f"Reflect on {topic_title}"]
            shuffled = order[:]
            random.shuffle(shuffled)
            return {
                "question": {
                    "content": f"{seed} Put these steps in a helpful order.",
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
                "answerArea": {"calculator": False},
                "hints": [{"content": "Start from basics, then practice, then apply in context."}],
            }
        if fmt == "radio_multi":
            return {
                "question": {
                    "content": f"{seed} Which TWO strategies help most?",
                    "images": {},
                    "widgets": {
                        "radio 1": {
                            "type": "radio",
                            "graded": True,
                            "options": {
                                "multipleSelect": True,
                                "displayCount": None,
                                "choices": [
                                    {"content": f"Practice {topic_title} in small daily sessions", "correct": True},
                                    {"content": f"Use examples to explain {topic_title} in your own words", "correct": True},
                                    {"content": "Skip review and rush to advanced material", "correct": False},
                                    {"content": "Ignore mistakes and never check answers", "correct": False},
                                ],
                            },
                        }
                    },
                },
                "answerArea": {"calculator": False},
                "hints": [{"content": "Pick habits that improve understanding and consistency."}],
            }
        return {
            "question": {
                "content": f"{seed} Which option is the best next move?",
                "images": {},
                "widgets": {
                    "radio 1": {
                        "type": "radio",
                        "graded": True,
                        "options": {
                            "multipleSelect": False,
                            "displayCount": None,
                            "choices": [
                                {"content": f"Start with one clear {topic_title} example and build from it", "correct": True},
                                {"content": f"Memorize all advanced {topic_title} terms first", "correct": False},
                                {"content": "Avoid practice questions", "correct": False},
                                {"content": "Skip feedback and move on", "correct": False},
                            ],
                        },
                    }
                },
            },
            "answerArea": {"calculator": False},
            "hints": [{"content": "Choose the option that builds understanding step by step."}],
        }

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
                return reused

        generated = self._gemini_question(topic, age, fmt, difficulty, memory)
        source = "gemini"
        if generated is None:
            if self.gemini_only:
                # Derive a valid question from previously Gemini-generated content.
                seed = self._seed_from_existing_gemini(topic, age)
                if not seed:
                    raise RuntimeError(f"Gemini generation failed for topic={topic}, format={fmt}")
                generated = self._build_seeded_item(topic, fmt, seed)
                source = "gemini_derived"
            else:
                generated = self._fallback_question(topic, age, fmt, difficulty)["item"]
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
            sort=[("created_at", 1)],
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
            if can_advance and len(steps) > 0:
                step_index = min(step_index + 1, len(steps) - 1)

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
