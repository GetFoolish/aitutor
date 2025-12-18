"""
LLM Classifier - Uses Gemini to classify emails and extract learning insights
"""
import os
import json
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.gmail_client import RawEmail

logger = get_logger(__name__)


@dataclass
class ClassifiedEmail:
    """Email with LLM-derived classification"""
    message_id: str
    category: str  # course_enrollment, course_progress, newsletter, certificate, receipt, other
    platform: Optional[str]
    course_name: Optional[str]
    topics: List[str]
    skill_level: str  # beginner, intermediate, advanced, unknown
    confidence: float
    extracted_entities: Dict[str, Any]
    raw_email: RawEmail


@dataclass
class LearningProfile:
    """LLM-inferred learning profile from email batch"""
    interests: List[str]
    skill_levels: Dict[str, str]
    learning_goals: List[str]
    preferred_platforms: List[str]
    learning_style: str
    time_commitment: str
    career_signals: List[str]
    confidence: float


class LLMClassifier:
    """
    Uses Gemini to intelligently classify and extract insights from emails.

    Features:
    - Batch email classification
    - Deep topic extraction
    - Skill level inference
    - Learning pattern analysis
    - Career goal detection
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=self.api_key)

        # Use Gemini Flash for cost-effective batch processing
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Rate limiting
        self.requests_per_minute = 60
        self._last_request_time = 0

    async def _rate_limit(self):
        """Simple rate limiting"""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        min_interval = 60 / self.requests_per_minute

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self._last_request_time = time.time()

    def _prepare_email_for_llm(self, email: RawEmail) -> str:
        """Prepare email content for LLM analysis"""
        return f"""
From: {email.sender}
Subject: {email.subject}
Date: {email.date.isoformat()}
Preview: {email.snippet[:300]}
"""

    async def classify_email_batch(
        self,
        emails: List[RawEmail],
        batch_size: int = 10
    ) -> List[ClassifiedEmail]:
        """
        Classify a batch of emails using LLM.

        Args:
            emails: List of raw emails to classify
            batch_size: Number of emails per LLM call

        Returns:
            List of classified emails
        """
        classified = []

        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]

            try:
                batch_results = await self._classify_batch(batch)
                classified.extend(batch_results)
            except Exception as e:
                logger.error(f"[LLM_CLASSIFIER] Error classifying batch: {e}")
                # Fall back to rule-based for this batch
                for email in batch:
                    classified.append(self._fallback_classify(email))

            # Rate limiting between batches
            await self._rate_limit()

        logger.info(f"[LLM_CLASSIFIER] Classified {len(classified)} emails")
        return classified

    async def _classify_batch(
        self,
        emails: List[RawEmail]
    ) -> List[ClassifiedEmail]:
        """Classify a single batch of emails"""
        # Prepare batch content
        email_contents = []
        for idx, email in enumerate(emails):
            email_contents.append(f"[EMAIL_{idx}]\n{self._prepare_email_for_llm(email)}")

        batch_text = "\n---\n".join(email_contents)

        prompt = f"""Analyze these emails and classify each one for learning/educational insights.

{batch_text}

For each email, output a JSON object with these fields:
- email_index: The email index (0, 1, 2, etc.)
- category: One of [course_enrollment, course_progress, course_completion, newsletter, certificate, receipt, job_related, other]
- platform: The learning platform if detected (coursera, udemy, edx, linkedin, etc.) or null
- course_name: The course/program name if this is course-related, or null
- topics: Array of 1-5 learning topics (e.g., ["python", "machine_learning", "data_science"])
- skill_level: One of [beginner, intermediate, advanced, unknown]
- confidence: Your confidence in this classification (0.0 to 1.0)
- entities: Object with any extracted entities like credential_id, completion_date, etc.

Output ONLY a JSON array of objects, one per email. No other text.
"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2000,
                )
            )

            # Parse response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            results = json.loads(response_text)

            classified = []
            for result in results:
                idx = result.get("email_index", 0)
                if idx < len(emails):
                    email = emails[idx]
                    classified.append(ClassifiedEmail(
                        message_id=email.message_id,
                        category=result.get("category", "other"),
                        platform=result.get("platform"),
                        course_name=result.get("course_name"),
                        topics=result.get("topics", []),
                        skill_level=result.get("skill_level", "unknown"),
                        confidence=result.get("confidence", 0.5),
                        extracted_entities=result.get("entities", {}),
                        raw_email=email
                    ))

            return classified

        except json.JSONDecodeError as e:
            logger.error(f"[LLM_CLASSIFIER] JSON parse error: {e}")
            return [self._fallback_classify(email) for email in emails]
        except Exception as e:
            logger.error(f"[LLM_CLASSIFIER] API error: {e}")
            raise

    def _fallback_classify(self, email: RawEmail) -> ClassifiedEmail:
        """Fallback rule-based classification when LLM fails"""
        text = f"{email.subject} {email.snippet}".lower()

        # Simple keyword-based classification
        category = "other"
        platform = None
        topics = []

        if any(word in text for word in ["congratulations", "completed", "certificate", "credential"]):
            category = "certificate"
        elif any(word in text for word in ["enrolled", "welcome to", "started"]):
            category = "course_enrollment"
        elif any(word in text for word in ["continue", "progress", "reminder"]):
            category = "course_progress"
        elif any(word in text for word in ["newsletter", "weekly", "digest"]):
            category = "newsletter"
        elif any(word in text for word in ["receipt", "payment", "invoice"]):
            category = "receipt"

        # Detect platform
        platforms = ["coursera", "udemy", "edx", "linkedin", "pluralsight", "datacamp"]
        for p in platforms:
            if p in email.sender_domain or p in text:
                platform = p
                break

        return ClassifiedEmail(
            message_id=email.message_id,
            category=category,
            platform=platform,
            course_name=None,
            topics=topics,
            skill_level="unknown",
            confidence=0.4,
            extracted_entities={},
            raw_email=email
        )

    async def infer_learning_profile(
        self,
        classified_emails: List[ClassifiedEmail]
    ) -> LearningProfile:
        """
        Use LLM to infer a comprehensive learning profile from classified emails.

        Args:
            classified_emails: Previously classified emails

        Returns:
            Inferred learning profile
        """
        # Prepare summary of classified emails
        course_emails = [e for e in classified_emails if e.category.startswith("course")]
        certificate_emails = [e for e in classified_emails if e.category == "certificate"]
        newsletter_emails = [e for e in classified_emails if e.category == "newsletter"]

        # Aggregate topics
        all_topics = []
        for email in classified_emails:
            all_topics.extend(email.topics)
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        # Aggregate platforms
        platforms = [e.platform for e in classified_emails if e.platform]
        platform_counts = {}
        for p in platforms:
            platform_counts[p] = platform_counts.get(p, 0) + 1
        top_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Aggregate courses
        courses = [e.course_name for e in course_emails if e.course_name]

        summary = f"""
Learning Email Analysis Summary:
- Total learning-related emails: {len(classified_emails)}
- Course emails: {len(course_emails)}
- Certificates earned: {len(certificate_emails)}
- Newsletter subscriptions: {len(newsletter_emails)}

Top Topics (by frequency):
{json.dumps(dict(top_topics), indent=2)}

Platforms used:
{json.dumps(dict(top_platforms), indent=2)}

Courses detected:
{json.dumps(courses[:20], indent=2)}

Certificate courses:
{json.dumps([e.course_name for e in certificate_emails if e.course_name], indent=2)}
"""

        prompt = f"""Based on this analysis of a user's learning-related emails, create a comprehensive learning profile.

{summary}

Output a JSON object with these fields:
- interests: Array of 5-10 main interest areas, ordered by strength
- skill_levels: Object mapping each interest to skill level (beginner/intermediate/advanced)
- learning_goals: Array of 3-5 inferred learning goals
- preferred_platforms: Array of preferred learning platforms
- learning_style: One of [structured_courses, self_paced, video_heavy, reading_heavy, hands_on, mixed]
- time_commitment: One of [casual, moderate, dedicated, intensive] based on email frequency
- career_signals: Array of any career-related signals (job interests, career change, skill building for work)
- confidence: Overall confidence in this profile (0.0 to 1.0)

Output ONLY the JSON object. No other text.
"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1000,
                )
            )

            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            result = json.loads(response_text)

            return LearningProfile(
                interests=result.get("interests", []),
                skill_levels=result.get("skill_levels", {}),
                learning_goals=result.get("learning_goals", []),
                preferred_platforms=result.get("preferred_platforms", []),
                learning_style=result.get("learning_style", "mixed"),
                time_commitment=result.get("time_commitment", "moderate"),
                career_signals=result.get("career_signals", []),
                confidence=result.get("confidence", 0.7)
            )

        except Exception as e:
            logger.error(f"[LLM_CLASSIFIER] Error inferring profile: {e}")
            # Return basic profile from aggregated data
            return LearningProfile(
                interests=[t[0] for t in top_topics],
                skill_levels={},
                learning_goals=[],
                preferred_platforms=[p[0] for p in top_platforms],
                learning_style="mixed",
                time_commitment="moderate",
                career_signals=[],
                confidence=0.4
            )

    async def extract_skill_level(
        self,
        topic: str,
        related_emails: List[ClassifiedEmail]
    ) -> str:
        """
        Infer skill level for a specific topic based on related emails.

        Args:
            topic: The topic to assess
            related_emails: Emails related to this topic

        Returns:
            Skill level: beginner, intermediate, advanced, unknown
        """
        if not related_emails:
            return "unknown"

        # Aggregate signals
        has_certificate = any(e.category == "certificate" for e in related_emails)
        has_advanced_courses = any(
            "advanced" in (e.course_name or "").lower() or
            "expert" in (e.course_name or "").lower()
            for e in related_emails
        )
        has_beginner_courses = any(
            "beginner" in (e.course_name or "").lower() or
            "introduction" in (e.course_name or "").lower() or
            "fundamentals" in (e.course_name or "").lower()
            for e in related_emails
        )
        email_count = len(related_emails)

        # Simple heuristic
        if has_certificate and has_advanced_courses:
            return "advanced"
        elif has_certificate or (email_count > 5 and not has_beginner_courses):
            return "intermediate"
        elif has_beginner_courses or email_count <= 3:
            return "beginner"
        else:
            return "intermediate"

    async def analyze_learning_patterns(
        self,
        classified_emails: List[ClassifiedEmail]
    ) -> Dict[str, Any]:
        """
        Analyze temporal patterns in learning behavior.

        Returns:
            Dict with learning pattern insights
        """
        if not classified_emails:
            return {}

        # Sort by date
        sorted_emails = sorted(
            classified_emails,
            key=lambda x: x.raw_email.date
        )

        # Analyze frequency
        dates = [e.raw_email.date for e in sorted_emails]
        if len(dates) < 2:
            return {"pattern": "insufficient_data"}

        total_days = (dates[-1] - dates[0]).days
        avg_emails_per_week = len(dates) / max(total_days / 7, 1)

        # Analyze topic progression
        topic_timeline = []
        for email in sorted_emails:
            topic_timeline.append({
                "date": email.raw_email.date.isoformat(),
                "topics": email.topics,
                "category": email.category
            })

        # Detect if user is progressing in skill level
        early_emails = sorted_emails[:len(sorted_emails)//3]
        late_emails = sorted_emails[-len(sorted_emails)//3:]

        early_levels = [e.skill_level for e in early_emails if e.skill_level != "unknown"]
        late_levels = [e.skill_level for e in late_emails if e.skill_level != "unknown"]

        progression = "stable"
        if early_levels and late_levels:
            level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
            early_avg = sum(level_map.get(l, 2) for l in early_levels) / len(early_levels)
            late_avg = sum(level_map.get(l, 2) for l in late_levels) / len(late_levels)
            if late_avg > early_avg + 0.3:
                progression = "advancing"
            elif late_avg < early_avg - 0.3:
                progression = "exploring_new_areas"

        return {
            "total_learning_emails": len(classified_emails),
            "date_range_days": total_days,
            "avg_emails_per_week": round(avg_emails_per_week, 2),
            "skill_progression": progression,
            "consistency": "regular" if avg_emails_per_week > 1 else "sporadic",
            "first_activity": dates[0].isoformat(),
            "last_activity": dates[-1].isoformat()
        }
