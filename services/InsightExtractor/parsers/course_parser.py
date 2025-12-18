"""
Course Parser - Extracts course enrollment and progress from learning platform emails
"""
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.gmail_client import RawEmail

logger = get_logger(__name__)


@dataclass
class ParsedCourse:
    """Parsed course information from email"""
    platform: str
    course_name: str
    topic: str
    subtopics: List[str]
    status: str  # enrolled, in_progress, completed
    enrollment_date: Optional[datetime]
    email_date: datetime
    confidence: float
    source_email_id: str


# Platform-specific parsing patterns
PLATFORM_PATTERNS = {
    "coursera.org": {
        "enrollment": [
            r"Welcome to (.+?)(?:\s+on Coursera|\s*$)",
            r"You(?:'ve| have) enrolled in (.+)",
            r"Start learning (.+)",
            r"enrolled in (.+?) specialization",
        ],
        "progress": [
            r"Continue (.+)",
            r"You're (\d+)% through (.+)",
            r"Complete your (.+)",
            r"Week \d+ of (.+)",
        ],
        "completion": [
            r"Congratulations.+completed (.+)",
            r"You(?:'ve| have) completed (.+)",
            r"Certificate for (.+)",
        ],
        "topic_extractor": r"(?:course|specialization) in (\w+(?:\s+\w+){0,3})"
    },
    "udemy.com": {
        "enrollment": [
            r"Welcome to (.+?)(?:\s+on Udemy|\s*!|\s*$)",
            r"You(?:'ve| have) enrolled in (.+)",
            r"Start (.+?) today",
            r"Thank you for purchasing (.+)",
        ],
        "progress": [
            r"Continue learning (.+)",
            r"Don't forget to finish (.+)",
            r"Your progress in (.+)",
        ],
        "completion": [
            r"Congratulations on completing (.+)",
            r"Certificate of Completion.+?(.+)",
        ],
        "topic_extractor": r"(?:course|masterclass|bootcamp) (?:on|in|for) (\w+(?:\s+\w+){0,3})"
    },
    "edx.org": {
        "enrollment": [
            r"Welcome to (.+?)(?:\s+on edX|\s*$)",
            r"You(?:'re| are) enrolled in (.+)",
            r"enrolled in (.+?) from",
        ],
        "progress": [
            r"Continue (.+)",
            r"Reminder: (.+?) starts",
        ],
        "completion": [
            r"You(?:'ve| have) earned.+?(.+)",
            r"Verified Certificate.+?(.+)",
        ],
        "topic_extractor": r"(?:course|program|certificate) in (\w+(?:\s+\w+){0,3})"
    },
    "linkedin.com": {
        "enrollment": [
            r"started watching (.+)",
            r"added (.+?) to your",
            r"New course: (.+)",
        ],
        "progress": [
            r"Continue watching (.+)",
            r"Finish (.+?) to earn",
        ],
        "completion": [
            r"completed (.+?) on LinkedIn Learning",
            r"You earned a certificate.+?(.+)",
        ],
        "topic_extractor": r"(?:course|learning path) (?:on|in|for|about) (\w+(?:\s+\w+){0,3})"
    },
    "pluralsight.com": {
        "enrollment": [
            r"started (.+?) on Pluralsight",
            r"Added to your queue: (.+)",
        ],
        "progress": [
            r"Continue (.+)",
            r"You're (\d+)% through (.+)",
        ],
        "completion": [
            r"completed (.+?) on Pluralsight",
            r"You finished (.+)",
        ],
        "topic_extractor": r"(?:course|path) (?:on|in|for) (\w+(?:\s+\w+){0,3})"
    },
    "khanacademy.org": {
        "enrollment": [
            r"started learning (.+)",
            r"began (.+?) course",
        ],
        "progress": [
            r"Keep practicing (.+)",
            r"You're making progress in (.+)",
            r"mastery progress.+?(.+)",
        ],
        "completion": [
            r"mastered (.+)",
            r"completed (.+?) unit",
        ],
        "topic_extractor": r"(?:unit|course|subject) (?:on|in|for) (\w+(?:\s+\w+){0,3})"
    },
    "codecademy.com": {
        "enrollment": [
            r"Welcome to (.+)",
            r"started (.+?) course",
            r"enrolled in (.+)",
        ],
        "progress": [
            r"Continue (.+)",
            r"(\d+)% complete.+?(.+)",
        ],
        "completion": [
            r"completed (.+?) course",
            r"Certificate.+?(.+)",
        ],
        "topic_extractor": r"(?:learn|course) (\w+(?:\s+\w+){0,2})"
    },
    "datacamp.com": {
        "enrollment": [
            r"started (.+?) on DataCamp",
            r"enrolled in (.+)",
        ],
        "progress": [
            r"Continue (.+)",
            r"Chapter \d+ of (.+)",
        ],
        "completion": [
            r"completed (.+?) on DataCamp",
            r"Statement of Accomplishment.+?(.+)",
        ],
        "topic_extractor": r"(?:course|track|skill) (?:on|in|for) (\w+(?:\s+\w+){0,3})"
    },
    "udacity.com": {
        "enrollment": [
            r"Welcome to (.+?) Nanodegree",
            r"enrolled in (.+)",
        ],
        "progress": [
            r"Continue (.+)",
            r"Project \d+.+?(.+)",
        ],
        "completion": [
            r"graduated from (.+)",
            r"completed (.+?) Nanodegree",
        ],
        "topic_extractor": r"(?:nanodegree|course) (?:on|in|for) (\w+(?:\s+\w+){0,3})"
    }
}

# Topic normalization mapping
TOPIC_NORMALIZATION = {
    # Programming
    "python": "python",
    "python programming": "python",
    "python 3": "python",
    "javascript": "javascript",
    "js": "javascript",
    "java": "java",
    "java programming": "java",
    "c++": "cpp",
    "c plus plus": "cpp",
    "c#": "csharp",
    "c sharp": "csharp",
    "golang": "go",
    "go programming": "go",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "typescript": "typescript",
    "sql": "sql",
    "html": "html_css",
    "css": "html_css",
    "html css": "html_css",

    # Data Science
    "machine learning": "machine_learning",
    "ml": "machine_learning",
    "deep learning": "deep_learning",
    "dl": "deep_learning",
    "neural networks": "deep_learning",
    "data science": "data_science",
    "data analysis": "data_analysis",
    "data analytics": "data_analysis",
    "statistics": "statistics",
    "probability": "statistics",
    "ai": "artificial_intelligence",
    "artificial intelligence": "artificial_intelligence",
    "nlp": "nlp",
    "natural language": "nlp",
    "computer vision": "computer_vision",

    # Web Development
    "web development": "web_development",
    "web dev": "web_development",
    "frontend": "frontend",
    "front end": "frontend",
    "backend": "backend",
    "back end": "backend",
    "full stack": "fullstack",
    "fullstack": "fullstack",
    "react": "react",
    "reactjs": "react",
    "angular": "angular",
    "vue": "vue",
    "vuejs": "vue",
    "node": "nodejs",
    "nodejs": "nodejs",
    "django": "django",
    "flask": "flask",

    # Cloud & DevOps
    "aws": "aws",
    "amazon web services": "aws",
    "azure": "azure",
    "google cloud": "gcp",
    "gcp": "gcp",
    "cloud computing": "cloud",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "devops": "devops",
    "ci cd": "devops",

    # Business
    "business": "business",
    "marketing": "marketing",
    "digital marketing": "digital_marketing",
    "finance": "finance",
    "accounting": "accounting",
    "product management": "product_management",
    "project management": "project_management",
    "leadership": "leadership",
    "management": "management",

    # Math
    "mathematics": "math",
    "math": "math",
    "algebra": "algebra",
    "calculus": "calculus",
    "linear algebra": "linear_algebra",
    "geometry": "geometry",
}


class CourseParser:
    """
    Parses learning platform emails to extract course information.

    Features:
    - Platform-specific pattern matching
    - Course name extraction and normalization
    - Topic classification
    - Status detection (enrolled, in_progress, completed)
    """

    def __init__(self):
        self.platform_patterns = PLATFORM_PATTERNS
        self.topic_normalization = TOPIC_NORMALIZATION

    def parse_email(self, email: RawEmail) -> Optional[ParsedCourse]:
        """
        Parse a single email for course information.

        Args:
            email: Raw email from Gmail

        Returns:
            ParsedCourse if course info found, None otherwise
        """
        domain = email.sender_domain

        # Find matching platform
        platform_key = None
        for key in self.platform_patterns:
            if key in domain:
                platform_key = key
                break

        if not platform_key:
            # Try generic parsing
            return self._parse_generic(email)

        patterns = self.platform_patterns[platform_key]
        text = f"{email.subject} {email.snippet} {email.body_text[:1000]}"

        # Try to detect status and extract course name
        status = "enrolled"
        course_name = None
        confidence = 0.5

        # Check completion patterns first (highest priority)
        for pattern in patterns.get("completion", []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                course_name = match.group(1).strip()
                status = "completed"
                confidence = 0.9
                break

        # Check progress patterns
        if not course_name:
            for pattern in patterns.get("progress", []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    course_name = groups[-1].strip() if groups else None
                    status = "in_progress"
                    confidence = 0.8
                    break

        # Check enrollment patterns
        if not course_name:
            for pattern in patterns.get("enrollment", []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    course_name = match.group(1).strip()
                    status = "enrolled"
                    confidence = 0.85
                    break

        if not course_name:
            return None

        # Clean up course name
        course_name = self._clean_course_name(course_name)
        if not course_name or len(course_name) < 3:
            return None

        # Extract topic
        topic, subtopics = self._extract_topic(course_name, text)

        return ParsedCourse(
            platform=platform_key.replace('.com', '').replace('.org', ''),
            course_name=course_name,
            topic=topic,
            subtopics=subtopics,
            status=status,
            enrollment_date=email.date if status == "enrolled" else None,
            email_date=email.date,
            confidence=confidence,
            source_email_id=email.message_id
        )

    def _parse_generic(self, email: RawEmail) -> Optional[ParsedCourse]:
        """Parse non-platform-specific learning emails"""
        text = f"{email.subject} {email.snippet}"

        # Generic patterns
        generic_patterns = [
            r"(?:enrolled|registered) (?:in|for) (.+?)(?:\.|!|$)",
            r"(?:Welcome to|Started) (.+?) (?:course|class)",
            r"(?:completed|finished) (.+?) (?:course|certification)",
            r"Your (.+?) course (?:begins|starts|is starting)",
        ]

        for pattern in generic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                course_name = self._clean_course_name(match.group(1))
                if course_name and len(course_name) > 3:
                    topic, subtopics = self._extract_topic(course_name, text)
                    return ParsedCourse(
                        platform="unknown",
                        course_name=course_name,
                        topic=topic,
                        subtopics=subtopics,
                        status="enrolled",
                        enrollment_date=email.date,
                        email_date=email.date,
                        confidence=0.6,
                        source_email_id=email.message_id
                    )

        return None

    def _clean_course_name(self, name: str) -> str:
        """Clean and normalize course name"""
        if not name:
            return ""

        # Remove common suffixes/prefixes
        removals = [
            r"\s+on Coursera", r"\s+on Udemy", r"\s+on edX",
            r"\s+on LinkedIn Learning", r"\s+on Pluralsight",
            r"\s+Nanodegree", r"\s+Specialization",
            r"^The\s+", r"\s+Course$", r"\s+Class$",
            r"\s*[!?.]+$"
        ]

        for pattern in removals:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        # Clean whitespace
        name = ' '.join(name.split())

        # Truncate if too long
        if len(name) > 100:
            name = name[:100].rsplit(' ', 1)[0]

        return name.strip()

    def _extract_topic(self, course_name: str, full_text: str) -> tuple:
        """
        Extract main topic and subtopics from course name and context.

        Returns:
            (main_topic, [subtopics])
        """
        text = f"{course_name} {full_text}".lower()
        found_topics = []

        # Check for known topics
        for keyword, normalized in self.topic_normalization.items():
            if keyword in text:
                if normalized not in found_topics:
                    found_topics.append(normalized)

        if not found_topics:
            # Default to first significant words from course name
            words = course_name.lower().split()
            significant_words = [w for w in words if len(w) > 3 and w not in
                               {'the', 'and', 'for', 'with', 'from', 'complete', 'introduction', 'beginner'}]
            if significant_words:
                found_topics = [significant_words[0]]
            else:
                found_topics = ["general"]

        main_topic = found_topics[0] if found_topics else "general"
        subtopics = found_topics[1:5] if len(found_topics) > 1 else []

        return main_topic, subtopics

    def parse_emails(self, emails: List[RawEmail]) -> List[ParsedCourse]:
        """
        Parse multiple emails for course information.

        Args:
            emails: List of raw emails

        Returns:
            List of parsed courses (deduplicated by course name)
        """
        courses = []
        seen_courses = set()

        for email in emails:
            try:
                course = self.parse_email(email)
                if course:
                    # Deduplicate by normalized course name
                    key = f"{course.platform}:{course.course_name.lower()}"
                    if key not in seen_courses:
                        seen_courses.add(key)
                        courses.append(course)
                    else:
                        # Update status if we see a newer email with different status
                        for existing in courses:
                            if f"{existing.platform}:{existing.course_name.lower()}" == key:
                                if course.email_date > existing.email_date:
                                    existing.status = course.status
                                break
            except Exception as e:
                logger.warning(f"[COURSE_PARSER] Error parsing email {email.message_id}: {e}")
                continue

        logger.info(f"[COURSE_PARSER] Parsed {len(courses)} unique courses from {len(emails)} emails")
        return courses

    def aggregate_topics(self, courses: List[ParsedCourse]) -> Dict[str, float]:
        """
        Aggregate topics with confidence scores.

        Returns:
            Dict of topic -> confidence score
        """
        topic_scores = {}

        for course in courses:
            # Main topic gets higher weight
            main_topic = course.topic
            if main_topic not in topic_scores:
                topic_scores[main_topic] = 0

            # Weight by status and confidence
            weight = course.confidence
            if course.status == "completed":
                weight *= 1.5
            elif course.status == "in_progress":
                weight *= 1.2

            topic_scores[main_topic] += weight

            # Subtopics get lower weight
            for subtopic in course.subtopics:
                if subtopic not in topic_scores:
                    topic_scores[subtopic] = 0
                topic_scores[subtopic] += weight * 0.5

        # Normalize scores to 0-1 range
        if topic_scores:
            max_score = max(topic_scores.values())
            topic_scores = {k: min(v / max_score, 1.0) for k, v in topic_scores.items()}

        return dict(sorted(topic_scores.items(), key=lambda x: x[1], reverse=True))
