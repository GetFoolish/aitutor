"""
Certificate Parser - Extracts completed certifications and credentials from emails
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
class ParsedCertificate:
    """Parsed certificate/completion information"""
    platform: str
    course_name: str
    credential_type: str  # certificate, badge, degree, nanodegree, specialization
    topic: str
    skills_demonstrated: List[str]
    completion_date: datetime
    credential_id: Optional[str]
    credential_url: Optional[str]
    issuer: str
    confidence: float
    source_email_id: str


# Platform-specific certificate patterns
CERTIFICATE_PATTERNS = {
    "coursera.org": {
        "completion": [
            r"[Cc]ongratulations.+?completed\s+(.+?)(?:\s+on Coursera|\s*\.|\s*!)",
            r"[Yy]ou(?:'ve| have) (?:successfully )?completed\s+(.+?)(?:\s+on|\s*\.|\s*!)",
            r"[Cc]ertificate (?:for|of completion).+?(.+?)(?:\s+on|\s*\.)",
            r"earned.+?[Cc]ertificate.+?(.+?)(?:\s+on|\s*\.)",
        ],
        "specialization": [
            r"completed.+?[Ss]pecialization.+?(.+?)(?:\s+on|\s*\.|\s*!)",
            r"[Ss]pecialization [Cc]ertificate.+?(.+)",
        ],
        "credential_id": r"[Cc]redential ID[:\s]+([A-Z0-9]+)",
        "credential_url": r"(?:verify|credential|certificate)[^\s]*(?:coursera\.org[^\s]+)",
    },
    "udemy.com": {
        "completion": [
            r"[Cc]ongratulations.+?completing\s+(.+?)(?:\s+on|\s*\.|\s*!)",
            r"[Cc]ertificate of [Cc]ompletion.+?(.+?)(?:\s+on|\s*\.)",
            r"completed.+?course.+?(.+?)(?:\s+on|\s*\.)",
        ],
        "credential_id": r"[Cc]ertificate (?:ID|Number)[:\s]+([A-Z0-9-]+)",
        "credential_url": r"(?:certificate|ude\.my)[^\s]+",
    },
    "edx.org": {
        "completion": [
            r"earned.+?[Vv]erified [Cc]ertificate.+?(.+?)(?:\s+from|\s*\.)",
            r"completed.+?(.+?)(?:\s+from|\s+on edX|\s*\.)",
            r"[Cc]ertificate for.+?(.+?)(?:\s+from|\s*\.)",
        ],
        "credential_id": r"[Cc]redential ID[:\s]+([a-f0-9-]+)",
        "credential_url": r"credentials\.edx\.org[^\s]+",
    },
    "linkedin.com": {
        "completion": [
            r"completed\s+(.+?)\s+on LinkedIn Learning",
            r"earned.+?certificate.+?(.+?)(?:\s+on|\s*\.)",
            r"[Ll]earning [Pp]ath.+?completed.+?(.+)",
        ],
        "badge": [
            r"earned.+?badge.+?(.+?)(?:\s+on|\s*\.)",
            r"[Ss]kill [Bb]adge.+?(.+)",
        ],
        "credential_url": r"linkedin\.com/learning/certificates/[^\s]+",
    },
    "udacity.com": {
        "completion": [
            r"graduated from.+?(.+?)[Nn]anodegree",
            r"completed.+?(.+?)[Nn]anodegree",
            r"[Nn]anodegree [Cc]ertificate.+?(.+)",
        ],
        "credential_id": r"[Cc]ertificate ID[:\s]+([A-Z0-9]+)",
        "credential_url": r"confirm\.udacity\.com[^\s]+",
    },
    "pluralsight.com": {
        "completion": [
            r"completed.+?(.+?)\s+on Pluralsight",
            r"earned.+?certificate.+?(.+?)(?:\s+on|\s*\.)",
        ],
        "credential_url": r"pluralsight\.com/profile/[^\s]+",
    },
    "datacamp.com": {
        "completion": [
            r"completed.+?(.+?)\s+on DataCamp",
            r"[Ss]tatement of [Aa]ccomplishment.+?(.+)",
            r"earned.+?certificate.+?(.+?)(?:\s+on|\s*\.)",
        ],
        "credential_url": r"datacamp\.com/statement-of-accomplishment/[^\s]+",
    },
    "codecademy.com": {
        "completion": [
            r"completed.+?(.+?)\s+(?:course|path)",
            r"earned.+?certificate.+?(.+?)(?:\s+on|\s*\.)",
        ],
    },
    "google.com": {
        "completion": [
            r"[Gg]oogle [Cc]ertificate.+?(.+)",
            r"completed.+?[Gg]oogle.+?(.+?)(?:\s+certificate|\s*\.)",
            r"[Pp]rofessional [Cc]ertificate.+?(.+)",
        ],
        "credential_id": r"[Cc]redential ID[:\s]+([A-Z0-9]+)",
        "credential_url": r"credly\.com/badges/[^\s]+",
    },
    "aws.amazon.com": {
        "completion": [
            r"AWS [Cc]ertified.+?(.+)",
            r"passed.+?AWS.+?(.+?)(?:\s+exam|\s*\.)",
            r"earned.+?AWS.+?certification.+?(.+)",
        ],
        "credential_id": r"[Vv]alidation [Nn]umber[:\s]+([A-Z0-9]+)",
        "credential_url": r"aws\.amazon\.com/verification",
    },
    "microsoft.com": {
        "completion": [
            r"[Mm]icrosoft [Cc]ertified.+?(.+)",
            r"passed.+?[Mm]icrosoft.+?(.+?)(?:\s+exam|\s*\.)",
            r"earned.+?[Mm]icrosoft.+?certification.+?(.+)",
        ],
        "credential_id": r"[Cc]ertification [Nn]umber[:\s]+([A-Z0-9-]+)",
        "credential_url": r"learn\.microsoft\.com/[^\s]+certifications",
    },
}

# Topic extraction patterns
TOPIC_PATTERNS = {
    "python": ["python", "django", "flask"],
    "javascript": ["javascript", "js", "node", "react", "angular", "vue"],
    "java": ["java", "spring", "jvm"],
    "data_science": ["data science", "data analysis", "analytics", "pandas"],
    "machine_learning": ["machine learning", "ml", "deep learning", "neural", "tensorflow", "pytorch"],
    "cloud": ["cloud", "aws", "azure", "gcp", "google cloud"],
    "devops": ["devops", "ci/cd", "kubernetes", "docker", "infrastructure"],
    "web_development": ["web development", "full stack", "frontend", "backend"],
    "mobile": ["mobile", "ios", "android", "swift", "kotlin"],
    "security": ["security", "cybersecurity", "ethical hacking", "penetration"],
    "database": ["sql", "database", "mongodb", "postgresql", "mysql"],
    "business": ["business", "management", "leadership", "product"],
}


class CertificateParser:
    """
    Parses emails to extract completed certifications and credentials.

    Features:
    - Platform-specific certificate detection
    - Credential ID and URL extraction
    - Skill inference from certificate names
    - Deduplication of certificates
    """

    def __init__(self):
        self.patterns = CERTIFICATE_PATTERNS
        self.topic_patterns = TOPIC_PATTERNS

    def parse_email(self, email: RawEmail) -> Optional[ParsedCertificate]:
        """
        Parse a single email for certificate information.

        Args:
            email: Raw email from Gmail

        Returns:
            ParsedCertificate if certificate found, None otherwise
        """
        domain = email.sender_domain

        # Check if this looks like a certificate email
        text = f"{email.subject} {email.snippet} {email.body_text[:2000]}"
        if not self._is_certificate_email(text):
            return None

        # Find matching platform
        platform_key = None
        for key in self.patterns:
            if key in domain:
                platform_key = key
                break

        if platform_key:
            return self._parse_platform_certificate(email, platform_key, text)
        else:
            return self._parse_generic_certificate(email, text)

    def _is_certificate_email(self, text: str) -> bool:
        """Check if email is likely about a certificate"""
        certificate_indicators = [
            r"[Cc]ongratulations.+?(?:complet|earn|pass|graduate)",
            r"[Cc]ertificate (?:of|for)",
            r"[Yy]ou(?:'ve| have) (?:completed|earned|passed)",
            r"[Ss]tatement of [Aa]ccomplishment",
            r"[Vv]erified [Cc]ertificate",
            r"[Cc]redential ID",
            r"[Bb]adge earned",
            r"[Nn]anodegree.+?(?:complet|graduate)",
        ]

        for pattern in certificate_indicators:
            if re.search(pattern, text):
                return True
        return False

    def _parse_platform_certificate(
        self,
        email: RawEmail,
        platform_key: str,
        text: str
    ) -> Optional[ParsedCertificate]:
        """Parse certificate from known platform"""
        patterns = self.patterns[platform_key]
        course_name = None
        credential_type = "certificate"

        # Try specialization patterns first (more specific)
        for pattern in patterns.get("specialization", []):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                course_name = match.group(1).strip()
                credential_type = "specialization"
                break

        # Try badge patterns
        if not course_name:
            for pattern in patterns.get("badge", []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    course_name = match.group(1).strip()
                    credential_type = "badge"
                    break

        # Try completion patterns
        if not course_name:
            for pattern in patterns.get("completion", []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    course_name = match.group(1).strip()
                    credential_type = "certificate"
                    break

        if not course_name:
            return None

        # Clean course name
        course_name = self._clean_course_name(course_name)
        if not course_name or len(course_name) < 3:
            return None

        # Extract credential ID
        credential_id = None
        if "credential_id" in patterns:
            match = re.search(patterns["credential_id"], text, re.IGNORECASE)
            if match:
                credential_id = match.group(1)

        # Extract credential URL
        credential_url = None
        if "credential_url" in patterns:
            match = re.search(patterns["credential_url"], text)
            if match:
                credential_url = match.group(0)

        # Infer topic and skills
        topic = self._infer_topic(course_name, text)
        skills = self._extract_skills(course_name, text)

        # Determine issuer
        issuer = self._get_issuer_name(platform_key)

        return ParsedCertificate(
            platform=platform_key.split('.')[0],
            course_name=course_name,
            credential_type=credential_type,
            topic=topic,
            skills_demonstrated=skills,
            completion_date=email.date,
            credential_id=credential_id,
            credential_url=credential_url,
            issuer=issuer,
            confidence=0.9,
            source_email_id=email.message_id
        )

    def _parse_generic_certificate(
        self,
        email: RawEmail,
        text: str
    ) -> Optional[ParsedCertificate]:
        """Parse certificate from unknown platform"""
        generic_patterns = [
            r"[Cc]ongratulations.+?(?:completed|earned|passed)\s+(.+?)(?:\.|!|$)",
            r"[Cc]ertificate (?:of completion|for)\s+(.+?)(?:\.|!|$)",
            r"[Yy]ou(?:'ve| have) (?:successfully )?(?:completed|earned)\s+(.+?)(?:\.|!|$)",
        ]

        course_name = None
        for pattern in generic_patterns:
            match = re.search(pattern, text)
            if match:
                course_name = self._clean_course_name(match.group(1))
                if course_name and len(course_name) > 3:
                    break

        if not course_name:
            return None

        topic = self._infer_topic(course_name, text)
        skills = self._extract_skills(course_name, text)

        return ParsedCertificate(
            platform="unknown",
            course_name=course_name,
            credential_type="certificate",
            topic=topic,
            skills_demonstrated=skills,
            completion_date=email.date,
            credential_id=None,
            credential_url=None,
            issuer=email.sender_domain,
            confidence=0.6,
            source_email_id=email.message_id
        )

    def _clean_course_name(self, name: str) -> str:
        """Clean and normalize course/certificate name"""
        if not name:
            return ""

        # Remove common suffixes/prefixes
        removals = [
            r"\s+on Coursera", r"\s+on Udemy", r"\s+on edX",
            r"\s+on LinkedIn Learning", r"\s+on Pluralsight",
            r"\s+on DataCamp", r"\s+on Codecademy",
            r"\s+Nanodegree$", r"\s+Specialization$",
            r"\s+Certificate$", r"\s+Certification$",
            r"^The\s+", r"\s*[!?.]+$",
            r"\s+course$", r"\s+program$",
        ]

        for pattern in removals:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)

        # Clean whitespace
        name = ' '.join(name.split())

        # Truncate if too long
        if len(name) > 100:
            name = name[:100].rsplit(' ', 1)[0]

        return name.strip()

    def _infer_topic(self, course_name: str, text: str) -> str:
        """Infer main topic from certificate"""
        combined_text = f"{course_name} {text}".lower()

        for topic, keywords in self.topic_patterns.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    return topic

        return "general"

    def _extract_skills(self, course_name: str, text: str) -> List[str]:
        """Extract demonstrated skills from certificate"""
        skills = []
        combined_text = f"{course_name} {text}".lower()

        # Common skill keywords
        skill_keywords = [
            "python", "javascript", "java", "sql", "html", "css",
            "react", "angular", "vue", "node", "django", "flask",
            "machine learning", "deep learning", "data analysis",
            "aws", "azure", "gcp", "docker", "kubernetes",
            "agile", "scrum", "project management", "leadership",
            "data visualization", "statistics", "excel", "tableau",
        ]

        for skill in skill_keywords:
            if skill.lower() in combined_text:
                skills.append(skill)

        return skills[:10]  # Limit to 10 skills

    def _get_issuer_name(self, platform_key: str) -> str:
        """Get human-readable issuer name from platform key"""
        issuers = {
            "coursera.org": "Coursera",
            "udemy.com": "Udemy",
            "edx.org": "edX",
            "linkedin.com": "LinkedIn Learning",
            "udacity.com": "Udacity",
            "pluralsight.com": "Pluralsight",
            "datacamp.com": "DataCamp",
            "codecademy.com": "Codecademy",
            "google.com": "Google",
            "aws.amazon.com": "Amazon Web Services",
            "microsoft.com": "Microsoft",
        }
        return issuers.get(platform_key, platform_key)

    def parse_emails(self, emails: List[RawEmail]) -> List[ParsedCertificate]:
        """
        Parse multiple emails for certificate information.

        Args:
            emails: List of raw emails

        Returns:
            List of parsed certificates (deduplicated)
        """
        certificates = []
        seen = set()

        for email in emails:
            try:
                cert = self.parse_email(email)
                if cert:
                    # Deduplicate by course name and platform
                    key = f"{cert.platform}:{cert.course_name.lower()}"
                    if key not in seen:
                        seen.add(key)
                        certificates.append(cert)
            except Exception as e:
                logger.warning(f"[CERT_PARSER] Error parsing email {email.message_id}: {e}")
                continue

        logger.info(f"[CERT_PARSER] Extracted {len(certificates)} certificates from {len(emails)} emails")
        return certificates

    def get_verified_skills(
        self,
        certificates: List[ParsedCertificate]
    ) -> Dict[str, float]:
        """
        Aggregate verified skills from certificates with confidence scores.

        Skills from certificates are more reliable indicators than course enrollments.

        Returns:
            Dict of skill -> confidence score
        """
        skill_scores = {}

        for cert in certificates:
            # Base confidence from certificate
            base_confidence = cert.confidence

            # Higher weight for professional certifications
            cert_weight = {
                "certificate": 1.0,
                "specialization": 1.2,
                "nanodegree": 1.3,
                "badge": 0.8,
                "degree": 1.5,
            }.get(cert.credential_type, 1.0)

            # Add topic as a skill
            if cert.topic != "general":
                if cert.topic not in skill_scores:
                    skill_scores[cert.topic] = 0
                skill_scores[cert.topic] += base_confidence * cert_weight

            # Add demonstrated skills
            for skill in cert.skills_demonstrated:
                skill_lower = skill.lower()
                if skill_lower not in skill_scores:
                    skill_scores[skill_lower] = 0
                skill_scores[skill_lower] += base_confidence * cert_weight * 0.8

        # Normalize to 0-1
        if skill_scores:
            max_score = max(skill_scores.values())
            if max_score > 0:
                skill_scores = {
                    k: min(v / max_score, 1.0)
                    for k, v in skill_scores.items()
                }

        return dict(sorted(skill_scores.items(), key=lambda x: x[1], reverse=True))
