"""
Newsletter Parser - Extracts newsletter subscriptions and infers interests
"""
import re
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.gmail_client import RawEmail

logger = get_logger(__name__)


@dataclass
class ParsedNewsletter:
    """Parsed newsletter information"""
    name: str
    domain: str
    sender_email: str
    topics: List[str]
    content_type: str  # technical, business, general, educational
    frequency: str  # daily, weekly, monthly, unknown
    email_count: int
    first_seen: datetime
    last_seen: datetime
    confidence: float


# Known newsletters with their topics
KNOWN_NEWSLETTERS = {
    # Tech/Programming
    "morningbrew.com": {
        "name": "Morning Brew",
        "topics": ["business", "tech", "finance"],
        "content_type": "business"
    },
    "themorningbrew.com": {
        "name": "Morning Brew",
        "topics": ["business", "tech", "finance"],
        "content_type": "business"
    },
    "tldr.tech": {
        "name": "TLDR",
        "topics": ["tech", "programming", "startups"],
        "content_type": "technical"
    },
    "hackernewsletter.com": {
        "name": "Hacker Newsletter",
        "topics": ["programming", "tech", "startups"],
        "content_type": "technical"
    },
    "javascriptweekly.com": {
        "name": "JavaScript Weekly",
        "topics": ["javascript", "web_development", "programming"],
        "content_type": "technical"
    },
    "pythonweekly.com": {
        "name": "Python Weekly",
        "topics": ["python", "programming", "data_science"],
        "content_type": "technical"
    },
    "rubyweekly.com": {
        "name": "Ruby Weekly",
        "topics": ["ruby", "programming", "web_development"],
        "content_type": "technical"
    },
    "golangweekly.com": {
        "name": "Golang Weekly",
        "topics": ["go", "programming", "backend"],
        "content_type": "technical"
    },
    "react.statuscode.com": {
        "name": "React Status",
        "topics": ["react", "javascript", "frontend"],
        "content_type": "technical"
    },
    "nodeweekly.com": {
        "name": "Node Weekly",
        "topics": ["nodejs", "javascript", "backend"],
        "content_type": "technical"
    },
    "css-weekly.com": {
        "name": "CSS Weekly",
        "topics": ["css", "frontend", "web_development"],
        "content_type": "technical"
    },
    "androidweekly.net": {
        "name": "Android Weekly",
        "topics": ["android", "mobile", "kotlin"],
        "content_type": "technical"
    },
    "iosdevweekly.com": {
        "name": "iOS Dev Weekly",
        "topics": ["ios", "swift", "mobile"],
        "content_type": "technical"
    },
    "dataelixir.com": {
        "name": "Data Elixir",
        "topics": ["data_science", "machine_learning", "analytics"],
        "content_type": "technical"
    },
    "datascienceweekly.org": {
        "name": "Data Science Weekly",
        "topics": ["data_science", "machine_learning", "statistics"],
        "content_type": "technical"
    },
    "aiweekly.co": {
        "name": "AI Weekly",
        "topics": ["artificial_intelligence", "machine_learning", "deep_learning"],
        "content_type": "technical"
    },
    "deeplearning.ai": {
        "name": "DeepLearning.AI",
        "topics": ["deep_learning", "machine_learning", "artificial_intelligence"],
        "content_type": "technical"
    },
    "devopsweekly.com": {
        "name": "DevOps Weekly",
        "topics": ["devops", "cloud", "infrastructure"],
        "content_type": "technical"
    },
    "kubeweekly.io": {
        "name": "KubeWeekly",
        "topics": ["kubernetes", "cloud", "devops"],
        "content_type": "technical"
    },
    "softwareleadweekly.com": {
        "name": "Software Lead Weekly",
        "topics": ["leadership", "management", "software_engineering"],
        "content_type": "business"
    },
    "techlead.software": {
        "name": "Tech Lead Digest",
        "topics": ["leadership", "software_engineering", "management"],
        "content_type": "business"
    },

    # Business/Finance
    "cbinsights.com": {
        "name": "CB Insights",
        "topics": ["startups", "finance", "business"],
        "content_type": "business"
    },
    "stratechery.com": {
        "name": "Stratechery",
        "topics": ["tech", "business", "strategy"],
        "content_type": "business"
    },
    "lennyrachitsky.com": {
        "name": "Lenny's Newsletter",
        "topics": ["product_management", "growth", "startups"],
        "content_type": "business"
    },
    "productify.substack.com": {
        "name": "Productify",
        "topics": ["product_management", "tech", "startups"],
        "content_type": "business"
    },

    # General/Educational
    "medium.com": {
        "name": "Medium",
        "topics": ["general"],  # Topics determined by content
        "content_type": "general"
    },
    "substack.com": {
        "name": "Substack",
        "topics": ["general"],
        "content_type": "general"
    },
    "mailchimp.com": {
        "name": "Mailchimp Newsletter",
        "topics": ["general"],
        "content_type": "general"
    },
}

# Topic inference from subject/content keywords
TOPIC_KEYWORDS = {
    "programming": ["code", "programming", "developer", "software", "coding", "github", "algorithm"],
    "python": ["python", "django", "flask", "pandas", "numpy", "jupyter"],
    "javascript": ["javascript", "js", "typescript", "node", "npm", "react", "vue", "angular"],
    "web_development": ["web", "frontend", "backend", "fullstack", "html", "css", "api"],
    "data_science": ["data science", "analytics", "visualization", "pandas", "statistics"],
    "machine_learning": ["machine learning", "ml", "neural", "tensorflow", "pytorch", "ai", "model"],
    "cloud": ["aws", "azure", "gcp", "cloud", "serverless", "lambda"],
    "devops": ["devops", "ci/cd", "docker", "kubernetes", "infrastructure", "deployment"],
    "mobile": ["mobile", "ios", "android", "swift", "kotlin", "react native", "flutter"],
    "security": ["security", "cybersecurity", "encryption", "vulnerability", "hacking"],
    "business": ["business", "startup", "entrepreneur", "growth", "revenue", "market"],
    "finance": ["finance", "investment", "stock", "crypto", "trading", "money"],
    "product_management": ["product", "roadmap", "user research", "agile", "scrum", "pm"],
    "leadership": ["leadership", "management", "team", "hiring", "culture"],
}


class NewsletterParser:
    """
    Parses emails to identify newsletter subscriptions and infer interests.

    Features:
    - Known newsletter identification
    - Topic inference from content
    - Frequency detection
    - Interest aggregation
    """

    def __init__(self):
        self.known_newsletters = KNOWN_NEWSLETTERS
        self.topic_keywords = TOPIC_KEYWORDS

    def parse_emails(self, emails: List[RawEmail]) -> List[ParsedNewsletter]:
        """
        Parse emails to identify newsletter subscriptions.

        Args:
            emails: List of raw emails

        Returns:
            List of parsed newsletters
        """
        # Group emails by sender domain
        domain_emails = defaultdict(list)
        for email in emails:
            domain_emails[email.sender_domain].append(email)

        newsletters = []

        for domain, domain_mail_list in domain_emails.items():
            if len(domain_mail_list) < 2:
                # Need multiple emails to identify as newsletter
                continue

            newsletter = self._parse_domain_emails(domain, domain_mail_list)
            if newsletter:
                newsletters.append(newsletter)

        logger.info(f"[NEWSLETTER_PARSER] Identified {len(newsletters)} newsletters from {len(emails)} emails")
        return newsletters

    def _parse_domain_emails(
        self,
        domain: str,
        emails: List[RawEmail]
    ) -> Optional[ParsedNewsletter]:
        """Parse emails from a single domain to identify newsletter"""
        # Sort by date
        emails = sorted(emails, key=lambda x: x.date)

        # Check if it's a known newsletter
        known_info = self._get_known_newsletter_info(domain)

        # Infer topics from content
        topics = self._infer_topics(emails)
        if known_info and known_info["topics"] != ["general"]:
            # Combine known topics with inferred ones
            topics = list(set(known_info["topics"] + topics[:3]))

        if not topics:
            topics = ["general"]

        # Detect frequency
        frequency = self._detect_frequency(emails)

        # Get name
        if known_info:
            name = known_info["name"]
            content_type = known_info["content_type"]
            confidence = 0.95
        else:
            name = self._extract_newsletter_name(emails)
            content_type = self._infer_content_type(topics)
            confidence = 0.7 if len(emails) >= 5 else 0.5

        return ParsedNewsletter(
            name=name,
            domain=domain,
            sender_email=emails[0].sender_email,
            topics=topics[:5],  # Limit to 5 topics
            content_type=content_type,
            frequency=frequency,
            email_count=len(emails),
            first_seen=emails[0].date,
            last_seen=emails[-1].date,
            confidence=confidence
        )

    def _get_known_newsletter_info(self, domain: str) -> Optional[Dict]:
        """Look up known newsletter by domain"""
        for known_domain, info in self.known_newsletters.items():
            if known_domain in domain or domain in known_domain:
                return info
        return None

    def _infer_topics(self, emails: List[RawEmail]) -> List[str]:
        """Infer topics from email subjects and snippets"""
        topic_counts = defaultdict(int)

        for email in emails:
            text = f"{email.subject} {email.snippet}".lower()

            for topic, keywords in self.topic_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in text:
                        topic_counts[topic] += 1
                        break  # Count each topic once per email

        # Sort by frequency
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

        return [topic for topic, _ in sorted_topics[:5]]

    def _detect_frequency(self, emails: List[RawEmail]) -> str:
        """Detect newsletter frequency based on email dates"""
        if len(emails) < 2:
            return "unknown"

        # Calculate average days between emails
        dates = sorted([e.date for e in emails])
        total_days = (dates[-1] - dates[0]).days

        if total_days == 0:
            return "unknown"

        avg_days_between = total_days / (len(emails) - 1)

        if avg_days_between <= 1.5:
            return "daily"
        elif avg_days_between <= 8:
            return "weekly"
        elif avg_days_between <= 16:
            return "biweekly"
        elif avg_days_between <= 35:
            return "monthly"
        else:
            return "irregular"

    def _extract_newsletter_name(self, emails: List[RawEmail]) -> str:
        """Extract newsletter name from sender info"""
        # Try to get name from sender field
        sender = emails[0].sender

        # Remove email part
        if '<' in sender:
            name_part = sender.split('<')[0].strip()
            if name_part and len(name_part) > 2:
                return name_part

        # Fall back to domain-based name
        domain = emails[0].sender_domain
        name = domain.split('.')[0].title()

        return name

    def _infer_content_type(self, topics: List[str]) -> str:
        """Infer content type from topics"""
        technical_topics = {
            "programming", "python", "javascript", "web_development",
            "data_science", "machine_learning", "cloud", "devops",
            "mobile", "security"
        }
        business_topics = {
            "business", "finance", "product_management", "leadership"
        }

        tech_count = sum(1 for t in topics if t in technical_topics)
        biz_count = sum(1 for t in topics if t in business_topics)

        if tech_count > biz_count:
            return "technical"
        elif biz_count > 0:
            return "business"
        else:
            return "general"

    def aggregate_interests(
        self,
        newsletters: List[ParsedNewsletter]
    ) -> Dict[str, float]:
        """
        Aggregate interests from newsletters with confidence scores.

        Returns:
            Dict of topic -> confidence score
        """
        interest_scores = defaultdict(float)

        for newsletter in newsletters:
            # Weight by email count and confidence
            base_weight = min(newsletter.email_count / 10, 1.0) * newsletter.confidence

            # Daily newsletters indicate stronger interest
            frequency_multiplier = {
                "daily": 1.5,
                "weekly": 1.2,
                "biweekly": 1.0,
                "monthly": 0.8,
                "irregular": 0.6,
                "unknown": 0.5
            }.get(newsletter.frequency, 0.5)

            weight = base_weight * frequency_multiplier

            for i, topic in enumerate(newsletter.topics):
                # First topic gets full weight, subsequent get less
                topic_weight = weight * (1.0 - i * 0.15)
                interest_scores[topic] += topic_weight

        # Normalize to 0-1
        if interest_scores:
            max_score = max(interest_scores.values())
            if max_score > 0:
                interest_scores = {
                    k: min(v / max_score, 1.0)
                    for k, v in interest_scores.items()
                }

        return dict(sorted(interest_scores.items(), key=lambda x: x[1], reverse=True))

    def get_reading_preferences(
        self,
        newsletters: List[ParsedNewsletter]
    ) -> Dict[str, any]:
        """
        Analyze newsletters to understand reading preferences.

        Returns:
            Dict with reading preference insights
        """
        if not newsletters:
            return {}

        # Content type distribution
        content_types = defaultdict(int)
        for n in newsletters:
            content_types[n.content_type] += n.email_count

        # Frequency preferences
        frequencies = defaultdict(int)
        for n in newsletters:
            frequencies[n.frequency] += 1

        # Calculate total engagement
        total_emails = sum(n.email_count for n in newsletters)

        # Dominant content type
        dominant_type = max(content_types.items(), key=lambda x: x[1])[0] if content_types else "general"

        return {
            "dominant_content_type": dominant_type,
            "content_type_distribution": dict(content_types),
            "frequency_preference": max(frequencies.items(), key=lambda x: x[1])[0] if frequencies else "weekly",
            "total_newsletters": len(newsletters),
            "total_newsletter_emails": total_emails,
            "average_newsletters_per_week": total_emails / max(1, self._weeks_span(newsletters))
        }

    def _weeks_span(self, newsletters: List[ParsedNewsletter]) -> float:
        """Calculate the time span in weeks covered by newsletters"""
        if not newsletters:
            return 1

        first_date = min(n.first_seen for n in newsletters)
        last_date = max(n.last_seen for n in newsletters)

        days = (last_date - first_date).days
        return max(days / 7, 1)
