"""
Profile Builder - Aggregates all extracted insights into a cold start profile
"""
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from collections import defaultdict

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.models.schemas import (
    ColdStartProfile,
    ExtractedCourse,
    ExtractedNewsletter,
    ExtractedCertificate,
    SkillLevel,
    LearningStyle
)
from services.InsightExtractor.parsers.course_parser import ParsedCourse
from services.InsightExtractor.parsers.newsletter_parser import ParsedNewsletter
from services.InsightExtractor.parsers.certificate_parser import ParsedCertificate
from services.InsightExtractor.extractors.llm_classifier import ClassifiedEmail, LearningProfile

logger = get_logger(__name__)


class ProfileBuilder:
    """
    Builds a comprehensive cold start profile by aggregating insights
    from multiple sources: rule-based parsers and LLM classification.

    Features:
    - Multi-source aggregation with confidence weighting
    - Topic normalization and deduplication
    - Skill level inference
    - Learning style detection
    - Career goal extraction
    """

    # Topic category mapping for DASH integration
    TOPIC_TO_DASH_CATEGORY = {
        # Math topics
        "algebra": "math",
        "calculus": "math",
        "statistics": "math",
        "linear_algebra": "math",
        "geometry": "math",
        "math": "math",

        # Programming/CS
        "python": "programming",
        "javascript": "programming",
        "java": "programming",
        "programming": "programming",
        "web_development": "programming",
        "data_structures": "programming",
        "algorithms": "programming",

        # Data Science
        "data_science": "data_science",
        "machine_learning": "data_science",
        "deep_learning": "data_science",
        "artificial_intelligence": "data_science",
        "data_analysis": "data_science",

        # Science
        "physics": "science",
        "chemistry": "science",
        "biology": "science",
        "science": "science",
    }

    def __init__(self):
        pass

    def build_profile(
        self,
        user_id: str,
        parsed_courses: List[ParsedCourse],
        parsed_newsletters: List[ParsedNewsletter],
        parsed_certificates: List[ParsedCertificate],
        llm_profile: Optional[LearningProfile] = None,
        classified_emails: Optional[List[ClassifiedEmail]] = None,
        total_emails_scanned: int = 0
    ) -> ColdStartProfile:
        """
        Build a comprehensive cold start profile from all sources.

        Args:
            user_id: User identifier
            parsed_courses: Courses from rule-based parser
            parsed_newsletters: Newsletters from rule-based parser
            parsed_certificates: Certificates from rule-based parser
            llm_profile: Profile inferred by LLM (optional)
            classified_emails: LLM-classified emails (optional)
            total_emails_scanned: Total number of emails processed

        Returns:
            Complete cold start profile
        """
        logger.info(f"[PROFILE_BUILDER] Building profile for user {user_id}")
        logger.info(f"[PROFILE_BUILDER] Inputs: {len(parsed_courses)} courses, "
                   f"{len(parsed_newsletters)} newsletters, {len(parsed_certificates)} certificates")

        # Convert parsed data to schema models
        courses = self._convert_courses(parsed_courses)
        newsletters = self._convert_newsletters(parsed_newsletters)
        certificates = self._convert_certificates(parsed_certificates)

        # Aggregate interests from all sources
        interests, topic_scores = self._aggregate_interests(
            parsed_courses,
            parsed_newsletters,
            parsed_certificates,
            llm_profile
        )

        # Infer overall skill level
        inferred_level = self._infer_skill_level(
            parsed_courses,
            parsed_certificates,
            llm_profile
        )

        # Determine learning style
        learning_style = self._determine_learning_style(
            parsed_courses,
            parsed_newsletters,
            llm_profile
        )

        # Extract career interests
        career_interests = self._extract_career_interests(
            llm_profile,
            parsed_courses,
            classified_emails
        )

        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            parsed_courses,
            parsed_newsletters,
            parsed_certificates,
            llm_profile
        )

        # Count relevant emails
        relevant_emails = (
            len(parsed_courses) +
            sum(n.email_count for n in parsed_newsletters) +
            len(parsed_certificates)
        )

        profile = ColdStartProfile(
            user_id=user_id,
            extraction_timestamp=datetime.utcnow(),
            interests=interests,
            active_courses=courses,
            newsletters=newsletters,
            certificates=certificates,
            inferred_level=inferred_level,
            learning_style=learning_style,
            preferred_topics=topic_scores,
            career_interests=career_interests,
            total_emails_scanned=total_emails_scanned,
            relevant_emails_found=relevant_emails,
            confidence_scores=confidence_scores
        )

        logger.info(f"[PROFILE_BUILDER] Built profile with {len(interests)} interests, "
                   f"level={inferred_level.value}, style={learning_style.value}")

        return profile

    def _convert_courses(self, parsed: List[ParsedCourse]) -> List[ExtractedCourse]:
        """Convert parsed courses to schema model"""
        return [
            ExtractedCourse(
                platform=c.platform,
                course_name=c.course_name,
                topic=c.topic,
                subtopics=c.subtopics,
                enrollment_date=c.enrollment_date,
                status=c.status,
                inferred_level=self._map_skill_level(None),  # Will be set later
                confidence=c.confidence
            )
            for c in parsed
        ]

    def _convert_newsletters(self, parsed: List[ParsedNewsletter]) -> List[ExtractedNewsletter]:
        """Convert parsed newsletters to schema model"""
        return [
            ExtractedNewsletter(
                name=n.name,
                domain=n.domain,
                topics=n.topics,
                frequency=n.frequency,
                content_type=n.content_type,
                first_seen=n.first_seen,
                count=n.email_count
            )
            for n in parsed
        ]

    def _convert_certificates(self, parsed: List[ParsedCertificate]) -> List[ExtractedCertificate]:
        """Convert parsed certificates to schema model"""
        return [
            ExtractedCertificate(
                platform=c.platform,
                course_name=c.course_name,
                topic=c.topic,
                completion_date=c.completion_date,
                credential_id=c.credential_id,
                skills_demonstrated=c.skills_demonstrated
            )
            for c in parsed
        ]

    def _aggregate_interests(
        self,
        courses: List[ParsedCourse],
        newsletters: List[ParsedNewsletter],
        certificates: List[ParsedCertificate],
        llm_profile: Optional[LearningProfile]
    ) -> tuple:
        """
        Aggregate interests from all sources with confidence weighting.

        Returns:
            (list of top interests, dict of topic -> score)
        """
        topic_scores = defaultdict(float)

        # Certificates have highest weight (verified completion)
        for cert in certificates:
            topic = self._normalize_topic(cert.topic)
            topic_scores[topic] += 3.0 * cert.confidence

            for skill in cert.skills_demonstrated:
                skill_topic = self._normalize_topic(skill)
                topic_scores[skill_topic] += 1.5 * cert.confidence

        # Active/completed courses have high weight
        for course in courses:
            topic = self._normalize_topic(course.topic)

            # Weight by status
            status_weight = {
                "completed": 2.5,
                "in_progress": 2.0,
                "enrolled": 1.5
            }.get(course.status, 1.0)

            topic_scores[topic] += status_weight * course.confidence

            for subtopic in course.subtopics:
                sub = self._normalize_topic(subtopic)
                topic_scores[sub] += status_weight * 0.5 * course.confidence

        # Newsletters indicate ongoing interest
        for newsletter in newsletters:
            for topic in newsletter.topics:
                norm_topic = self._normalize_topic(topic)
                # Weight by engagement (email count and frequency)
                engagement_weight = min(newsletter.email_count / 10, 1.5)
                topic_scores[norm_topic] += engagement_weight * newsletter.confidence

        # LLM-inferred interests (if available)
        if llm_profile:
            for i, interest in enumerate(llm_profile.interests):
                norm_interest = self._normalize_topic(interest)
                # Decreasing weight by rank
                weight = llm_profile.confidence * (1.0 - i * 0.1)
                topic_scores[norm_interest] += weight

        # Normalize scores to 0-1
        if topic_scores:
            max_score = max(topic_scores.values())
            if max_score > 0:
                topic_scores = {
                    k: round(min(v / max_score, 1.0), 3)
                    for k, v in topic_scores.items()
                }

        # Sort and get top interests
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        top_interests = [topic for topic, _ in sorted_topics[:15]]

        return top_interests, dict(sorted_topics)

    def _normalize_topic(self, topic: str) -> str:
        """Normalize topic string"""
        if not topic:
            return "general"

        # Lowercase and clean
        normalized = topic.lower().strip()

        # Common normalizations
        normalizations = {
            "machine learning": "machine_learning",
            "deep learning": "deep_learning",
            "data science": "data_science",
            "web development": "web_development",
            "artificial intelligence": "artificial_intelligence",
            "natural language processing": "nlp",
            "computer vision": "computer_vision",
            "full stack": "fullstack",
            "front end": "frontend",
            "back end": "backend",
        }

        for original, normalized_form in normalizations.items():
            if original in normalized:
                return normalized_form

        # Replace spaces with underscores
        return normalized.replace(" ", "_").replace("-", "_")

    def _infer_skill_level(
        self,
        courses: List[ParsedCourse],
        certificates: List[ParsedCertificate],
        llm_profile: Optional[LearningProfile]
    ) -> SkillLevel:
        """
        Infer overall skill level based on learning history.
        """
        signals = []

        # Check certificate count (strong signal)
        if len(certificates) >= 5:
            signals.append("advanced")
        elif len(certificates) >= 2:
            signals.append("intermediate")
        elif len(certificates) >= 1:
            signals.append("intermediate")

        # Check course names for level indicators
        for course in courses:
            name_lower = course.course_name.lower()
            if any(word in name_lower for word in ["advanced", "expert", "master", "professional"]):
                signals.append("advanced")
            elif any(word in name_lower for word in ["intermediate", "practical", "applied"]):
                signals.append("intermediate")
            elif any(word in name_lower for word in ["beginner", "introduction", "fundamentals", "basics", "101"]):
                signals.append("beginner")

        # Check completed vs enrolled ratio
        completed = sum(1 for c in courses if c.status == "completed")
        if completed >= 5:
            signals.append("intermediate")

        # LLM inference
        if llm_profile and llm_profile.skill_levels:
            # Get most common level from LLM
            levels = list(llm_profile.skill_levels.values())
            if levels:
                from collections import Counter
                most_common = Counter(levels).most_common(1)[0][0]
                signals.append(most_common)

        # Aggregate signals
        if not signals:
            return SkillLevel.UNKNOWN

        level_scores = {"beginner": 0, "intermediate": 0, "advanced": 0}
        for signal in signals:
            if signal in level_scores:
                level_scores[signal] += 1

        max_level = max(level_scores.items(), key=lambda x: x[1])

        level_map = {
            "beginner": SkillLevel.BEGINNER,
            "intermediate": SkillLevel.INTERMEDIATE,
            "advanced": SkillLevel.ADVANCED
        }

        return level_map.get(max_level[0], SkillLevel.INTERMEDIATE)

    def _determine_learning_style(
        self,
        courses: List[ParsedCourse],
        newsletters: List[ParsedNewsletter],
        llm_profile: Optional[LearningProfile]
    ) -> LearningStyle:
        """
        Determine preferred learning style.
        """
        signals = defaultdict(float)

        # Video course platforms
        video_platforms = {"coursera", "udemy", "linkedin", "pluralsight", "masterclass"}
        interactive_platforms = {"codecademy", "datacamp", "brilliant", "khanacademy"}
        text_platforms = {"medium", "substack"}

        for course in courses:
            platform = course.platform.lower()
            if platform in video_platforms:
                signals["video_courses"] += 1
            elif platform in interactive_platforms:
                signals["interactive"] += 1

        for newsletter in newsletters:
            if newsletter.content_type == "technical":
                signals["text_articles"] += newsletter.email_count * 0.1
            signals["text_articles"] += 0.5

        # LLM inference
        if llm_profile:
            llm_style = llm_profile.learning_style
            if llm_style != "mixed":
                signals[llm_style] += 2

        if not signals:
            return LearningStyle.MIXED

        max_style = max(signals.items(), key=lambda x: x[1])

        style_map = {
            "video_courses": LearningStyle.VIDEO_COURSES,
            "text_articles": LearningStyle.TEXT_ARTICLES,
            "interactive": LearningStyle.INTERACTIVE,
            "mixed": LearningStyle.MIXED
        }

        # If no clear winner, return mixed
        if max_style[1] < 2:
            return LearningStyle.MIXED

        return style_map.get(max_style[0], LearningStyle.MIXED)

    def _extract_career_interests(
        self,
        llm_profile: Optional[LearningProfile],
        courses: List[ParsedCourse],
        classified_emails: Optional[List[ClassifiedEmail]]
    ) -> List[str]:
        """
        Extract career-related interests and goals.
        """
        career_signals = []

        # From LLM profile
        if llm_profile:
            career_signals.extend(llm_profile.career_signals)
            career_signals.extend(llm_profile.learning_goals)

        # From course names
        career_keywords = [
            "career", "job", "professional", "certification",
            "interview", "resume", "portfolio", "freelance"
        ]

        for course in courses:
            name_lower = course.course_name.lower()
            for keyword in career_keywords:
                if keyword in name_lower:
                    career_signals.append(f"career_focused_{course.topic}")
                    break

        # From classified emails
        if classified_emails:
            job_emails = [e for e in classified_emails if e.category == "job_related"]
            if len(job_emails) > 3:
                career_signals.append("active_job_search")

        # Deduplicate and limit
        unique_signals = list(dict.fromkeys(career_signals))
        return unique_signals[:10]

    def _calculate_confidence_scores(
        self,
        courses: List[ParsedCourse],
        newsletters: List[ParsedNewsletter],
        certificates: List[ParsedCertificate],
        llm_profile: Optional[LearningProfile]
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for different aspects of the profile.
        """
        # Base confidence on data availability
        course_confidence = min(len(courses) / 10, 1.0) if courses else 0
        newsletter_confidence = min(len(newsletters) / 5, 1.0) if newsletters else 0
        certificate_confidence = min(len(certificates) / 3, 1.0) if certificates else 0

        # Overall confidence
        data_sources = sum([
            1 if courses else 0,
            1 if newsletters else 0,
            1 if certificates else 0,
            1 if llm_profile else 0
        ])

        overall = (
            course_confidence * 0.3 +
            newsletter_confidence * 0.2 +
            certificate_confidence * 0.3 +
            (llm_profile.confidence if llm_profile else 0) * 0.2
        )

        # Boost if multiple sources agree
        if data_sources >= 3:
            overall = min(overall * 1.2, 1.0)

        return {
            "overall": round(overall, 3),
            "interests": round((course_confidence + newsletter_confidence) / 2, 3),
            "skill_level": round((certificate_confidence + course_confidence) / 2, 3),
            "learning_style": round(course_confidence, 3),
            "data_sources": data_sources
        }

    def _map_skill_level(self, level: Optional[str]) -> SkillLevel:
        """Map string skill level to enum"""
        if not level:
            return SkillLevel.UNKNOWN

        level_map = {
            "beginner": SkillLevel.BEGINNER,
            "intermediate": SkillLevel.INTERMEDIATE,
            "advanced": SkillLevel.ADVANCED
        }
        return level_map.get(level.lower(), SkillLevel.UNKNOWN)

    def map_to_dash_skills(
        self,
        profile: ColdStartProfile,
        dash_skills: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Map cold start profile interests to DASH skill IDs with initial memory strengths.

        Args:
            profile: Cold start profile
            dash_skills: Dictionary of DASH skills (skill_id -> Skill object)

        Returns:
            Dict of skill_id -> initial memory_strength adjustment
        """
        skill_adjustments = {}

        # Get user's top topics
        top_topics = profile.preferred_topics

        for skill_id, skill in dash_skills.items():
            skill_name_lower = skill.name.lower()

            # Check if any of user's topics match this skill
            for topic, score in top_topics.items():
                topic_lower = topic.lower().replace("_", " ")

                # Direct match
                if topic_lower in skill_name_lower or skill_name_lower in topic_lower:
                    # Positive adjustment based on score and inferred level
                    level_multiplier = {
                        SkillLevel.BEGINNER: 0.5,
                        SkillLevel.INTERMEDIATE: 1.0,
                        SkillLevel.ADVANCED: 1.5,
                        SkillLevel.UNKNOWN: 0.75
                    }.get(profile.inferred_level, 0.75)

                    # Memory strength adjustment (-2 to +2 range)
                    # Higher score = more interest = start with higher memory strength
                    adjustment = (score * 2 - 1) * level_multiplier

                    skill_adjustments[skill_id] = adjustment
                    break

                # Category match
                dash_category = self.TOPIC_TO_DASH_CATEGORY.get(topic_lower)
                if dash_category and dash_category in skill_name_lower:
                    adjustment = (score * 1.5 - 0.5) * 0.7
                    skill_adjustments[skill_id] = adjustment
                    break

        logger.info(f"[PROFILE_BUILDER] Mapped {len(skill_adjustments)} DASH skills from profile")
        return skill_adjustments
