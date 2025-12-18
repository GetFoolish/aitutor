"""
Persona Builder - Builds a comprehensive user persona from all extracted signals

Creates a rich user profile including:
- Interests & passions
- Skills & expertise
- Learning preferences
- Lifestyle & behavior patterns
- Financial indicators
- Career & professional signals
- Personality traits
- Content preferences
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.extractors.signal_extractor import (
    ExtractedSignal,
    SignalCategory
)

logger = get_logger(__name__)


class EngagementLevel(str, Enum):
    """User engagement level"""
    CASUAL = "casual"
    MODERATE = "moderate"
    ACTIVE = "active"
    POWER_USER = "power_user"


class SpendingTier(str, Enum):
    """Spending behavior tier"""
    BUDGET = "budget"
    MODERATE = "moderate"
    PREMIUM = "premium"
    LUXURY = "luxury"


class LearningStyle(str, Enum):
    """Preferred learning style"""
    VISUAL = "visual"  # Videos, courses
    READING = "reading"  # Articles, books
    INTERACTIVE = "interactive"  # Hands-on, coding
    AUDIO = "audio"  # Podcasts, audiobooks
    MIXED = "mixed"


class TechSavviness(str, Enum):
    """Technology proficiency level"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class InterestProfile:
    """User's interest profile"""
    primary_interests: List[str] = field(default_factory=list)
    secondary_interests: List[str] = field(default_factory=list)
    interest_scores: Dict[str, float] = field(default_factory=dict)
    interest_categories: Dict[str, List[str]] = field(default_factory=dict)
    emerging_interests: List[str] = field(default_factory=list)  # Recent new interests
    declining_interests: List[str] = field(default_factory=list)  # Fading interests


@dataclass
class SkillProfile:
    """User's skill profile"""
    verified_skills: List[str] = field(default_factory=list)  # From certificates
    inferred_skills: List[str] = field(default_factory=list)  # From activity
    skill_levels: Dict[str, str] = field(default_factory=dict)  # skill -> level
    learning_skills: List[str] = field(default_factory=list)  # Currently learning
    skill_gaps: List[str] = field(default_factory=list)  # Potential gaps to fill


@dataclass
class LearningProfile:
    """User's learning profile"""
    learning_style: LearningStyle = LearningStyle.MIXED
    preferred_platforms: List[str] = field(default_factory=list)
    topics_studied: List[str] = field(default_factory=list)
    certificates_earned: int = 0
    courses_completed: int = 0
    courses_in_progress: int = 0
    learning_frequency: str = "unknown"  # daily, weekly, monthly
    preferred_content_length: str = "medium"  # short, medium, long
    best_learning_times: List[str] = field(default_factory=list)


@dataclass
class LifestyleProfile:
    """User's lifestyle profile"""
    lifestyle_indicators: List[str] = field(default_factory=list)
    activity_level: str = "moderate"  # sedentary, moderate, active, very_active
    health_conscious: bool = False
    travel_frequency: str = "occasional"  # rare, occasional, frequent, very_frequent
    urban_suburban: str = "unknown"
    family_indicators: List[str] = field(default_factory=list)
    hobbies: List[str] = field(default_factory=list)


@dataclass
class ProfessionalProfile:
    """User's professional profile"""
    career_stage: str = "unknown"  # student, early_career, mid_career, senior, executive
    job_search_active: bool = False
    industry_signals: List[str] = field(default_factory=list)
    professional_interests: List[str] = field(default_factory=list)
    freelance_signals: bool = False
    entrepreneurial_signals: bool = False
    leadership_signals: bool = False


@dataclass
class BehaviorProfile:
    """User's behavior patterns"""
    engagement_level: EngagementLevel = EngagementLevel.MODERATE
    spending_tier: SpendingTier = SpendingTier.MODERATE
    tech_savviness: TechSavviness = TechSavviness.INTERMEDIATE
    subscription_count: int = 0
    preferred_shopping_categories: List[str] = field(default_factory=list)
    brand_preferences: List[str] = field(default_factory=list)
    time_patterns: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentPreferences:
    """User's content consumption preferences"""
    preferred_formats: List[str] = field(default_factory=list)  # video, article, podcast
    preferred_lengths: Dict[str, str] = field(default_factory=dict)
    topics_followed: List[str] = field(default_factory=list)
    newsletter_categories: List[str] = field(default_factory=list)
    media_platforms: List[str] = field(default_factory=list)
    content_frequency: str = "moderate"  # light, moderate, heavy


@dataclass
class UserPersona:
    """Complete user persona"""
    user_id: str
    created_at: datetime
    last_updated: datetime

    # Profile components
    interests: InterestProfile = field(default_factory=InterestProfile)
    skills: SkillProfile = field(default_factory=SkillProfile)
    learning: LearningProfile = field(default_factory=LearningProfile)
    lifestyle: LifestyleProfile = field(default_factory=LifestyleProfile)
    professional: ProfessionalProfile = field(default_factory=ProfessionalProfile)
    behavior: BehaviorProfile = field(default_factory=BehaviorProfile)
    content: ContentPreferences = field(default_factory=ContentPreferences)

    # Summary
    persona_tags: List[str] = field(default_factory=list)  # Quick descriptors
    confidence_score: float = 0.5

    # Metadata
    signals_analyzed: int = 0
    date_range_days: int = 0
    categories_found: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "interests": {
                "primary": self.interests.primary_interests,
                "secondary": self.interests.secondary_interests,
                "scores": self.interests.interest_scores,
                "categories": self.interests.interest_categories,
                "emerging": self.interests.emerging_interests,
            },
            "skills": {
                "verified": self.skills.verified_skills,
                "inferred": self.skills.inferred_skills,
                "levels": self.skills.skill_levels,
                "learning": self.skills.learning_skills,
            },
            "learning": {
                "style": self.learning.learning_style.value,
                "platforms": self.learning.preferred_platforms,
                "topics": self.learning.topics_studied,
                "certificates": self.learning.certificates_earned,
                "courses_completed": self.learning.courses_completed,
                "frequency": self.learning.learning_frequency,
            },
            "lifestyle": {
                "indicators": self.lifestyle.lifestyle_indicators,
                "activity_level": self.lifestyle.activity_level,
                "health_conscious": self.lifestyle.health_conscious,
                "travel_frequency": self.lifestyle.travel_frequency,
                "hobbies": self.lifestyle.hobbies,
            },
            "professional": {
                "career_stage": self.professional.career_stage,
                "job_search_active": self.professional.job_search_active,
                "industries": self.professional.industry_signals,
                "interests": self.professional.professional_interests,
                "freelance": self.professional.freelance_signals,
                "entrepreneurial": self.professional.entrepreneurial_signals,
            },
            "behavior": {
                "engagement": self.behavior.engagement_level.value,
                "spending": self.behavior.spending_tier.value,
                "tech_savviness": self.behavior.tech_savviness.value,
                "subscriptions": self.behavior.subscription_count,
                "shopping_categories": self.behavior.preferred_shopping_categories,
            },
            "content": {
                "formats": self.content.preferred_formats,
                "topics": self.content.topics_followed,
                "newsletters": self.content.newsletter_categories,
                "platforms": self.content.media_platforms,
            },
            "persona_tags": self.persona_tags,
            "confidence_score": self.confidence_score,
            "signals_analyzed": self.signals_analyzed,
            "date_range_days": self.date_range_days,
            "categories_found": self.categories_found,
        }


class PersonaBuilder:
    """
    Builds a comprehensive user persona from extracted signals.
    """

    def __init__(self):
        pass

    def build_persona(
        self,
        user_id: str,
        signals: List[ExtractedSignal],
        llm_insights: Optional[Dict] = None
    ) -> UserPersona:
        """
        Build a complete user persona from signals.

        Args:
            user_id: User identifier
            signals: List of extracted signals
            llm_insights: Optional LLM-derived insights

        Returns:
            Complete UserPersona
        """
        now = datetime.now(timezone.utc)

        persona = UserPersona(
            user_id=user_id,
            created_at=now,
            last_updated=now,
            signals_analyzed=len(signals)
        )

        if not signals:
            return persona

        # Calculate date range
        dates = [s.date for s in signals if s.date]
        if dates:
            persona.date_range_days = (max(dates) - min(dates)).days

        # Build each profile component
        persona.interests = self._build_interest_profile(signals)
        persona.skills = self._build_skill_profile(signals)
        persona.learning = self._build_learning_profile(signals)
        persona.lifestyle = self._build_lifestyle_profile(signals)
        persona.professional = self._build_professional_profile(signals)
        persona.behavior = self._build_behavior_profile(signals)
        persona.content = self._build_content_preferences(signals)

        # Generate persona tags
        persona.persona_tags = self._generate_persona_tags(persona)

        # Get categories found
        persona.categories_found = list(set(s.category.value for s in signals))

        # Calculate confidence
        persona.confidence_score = self._calculate_confidence(signals, persona)

        # Integrate LLM insights if available
        if llm_insights:
            self._integrate_llm_insights(persona, llm_insights)

        logger.info(f"[PERSONA_BUILDER] Built persona for {user_id}: "
                   f"{len(persona.interests.primary_interests)} interests, "
                   f"{len(persona.skills.verified_skills)} skills, "
                   f"confidence={persona.confidence_score:.2f}")

        return persona

    def _build_interest_profile(self, signals: List[ExtractedSignal]) -> InterestProfile:
        """Build interest profile from signals"""
        profile = InterestProfile()

        # Aggregate interests
        interest_scores = defaultdict(float)

        for signal in signals:
            weight = signal.confidence

            # Category-based interests
            category_interests = {
                SignalCategory.EDUCATION: ["learning", "education", "self_improvement"],
                SignalCategory.TECHNOLOGY: ["technology", "software", "gadgets"],
                SignalCategory.CREATIVE: ["creativity", "design", "art"],
                SignalCategory.HEALTH_FITNESS: ["health", "fitness", "wellness"],
                SignalCategory.TRAVEL: ["travel", "adventure", "exploration"],
                SignalCategory.GAMING: ["gaming", "esports", "entertainment"],
                SignalCategory.FINANCE: ["finance", "investing", "personal_finance"],
                SignalCategory.FOOD_LIFESTYLE: ["food", "cooking", "lifestyle"],
                SignalCategory.ENTERTAINMENT: ["entertainment", "media", "streaming"],
                SignalCategory.NEWS_MEDIA: ["news", "current_events", "reading"],
            }

            if signal.category in category_interests:
                for interest in category_interests[signal.category]:
                    interest_scores[interest] += weight

            # Direct interests from signal
            for interest in signal.interest_indicators:
                interest_scores[interest] += weight * 1.5

            # Topics
            for topic in signal.topics:
                interest_scores[topic] += weight * 1.2

        # Normalize and sort
        if interest_scores:
            max_score = max(interest_scores.values())
            interest_scores = {k: v / max_score for k, v in interest_scores.items()}

        sorted_interests = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)

        # Split into primary and secondary
        profile.primary_interests = [i[0] for i in sorted_interests[:10]]
        profile.secondary_interests = [i[0] for i in sorted_interests[10:20]]
        profile.interest_scores = dict(sorted_interests[:30])

        # Categorize interests
        profile.interest_categories = self._categorize_interests(sorted_interests[:30])

        # Detect emerging interests (last 30 days)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_interests = set()
        for signal in signals:
            if signal.date and signal.date > recent_cutoff:
                recent_interests.update(signal.interest_indicators)
                recent_interests.update(signal.topics)

        older_interests = set()
        for signal in signals:
            if signal.date and signal.date <= recent_cutoff:
                older_interests.update(signal.interest_indicators)

        profile.emerging_interests = list(recent_interests - older_interests)[:5]

        return profile

    def _build_skill_profile(self, signals: List[ExtractedSignal]) -> SkillProfile:
        """Build skill profile from signals"""
        profile = SkillProfile()

        verified_skills = set()
        inferred_skills = set()
        learning_skills = set()

        for signal in signals:
            # Certificates = verified skills
            if signal.signal_type == "certificate":
                verified_skills.update(signal.skill_indicators)

            # Course enrollments = learning skills
            elif signal.signal_type == "course_enrollment":
                learning_skills.update(signal.skill_indicators)

            # Course completion = inferred skills
            elif signal.signal_type == "course_progress":
                inferred_skills.update(signal.skill_indicators)

            # Tech signals = inferred skills
            elif signal.category == SignalCategory.TECHNOLOGY:
                inferred_skills.update(signal.skill_indicators)

            # General skill indicators
            inferred_skills.update(signal.skill_indicators)

        profile.verified_skills = list(verified_skills)[:20]
        profile.inferred_skills = list(inferred_skills - verified_skills)[:20]
        profile.learning_skills = list(learning_skills)[:10]

        # Infer skill levels
        for skill in profile.verified_skills:
            profile.skill_levels[skill] = "intermediate"  # Has certificate

        for skill in profile.inferred_skills:
            if skill not in profile.skill_levels:
                profile.skill_levels[skill] = "beginner"

        return profile

    def _build_learning_profile(self, signals: List[ExtractedSignal]) -> LearningProfile:
        """Build learning profile from signals"""
        profile = LearningProfile()

        education_signals = [s for s in signals if s.category == SignalCategory.EDUCATION]

        if not education_signals:
            return profile

        # Preferred platforms
        platform_counts = defaultdict(int)
        for signal in education_signals:
            platform_counts[signal.source] += 1

        sorted_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
        profile.preferred_platforms = [p[0] for p in sorted_platforms[:5]]

        # Topics studied
        topics = set()
        for signal in education_signals:
            topics.update(signal.topics)
        profile.topics_studied = list(topics)[:20]

        # Counts
        profile.certificates_earned = sum(1 for s in signals if s.signal_type == "certificate")
        profile.courses_completed = sum(1 for s in signals if s.signal_type in ["certificate", "course_progress"])
        profile.courses_in_progress = sum(1 for s in signals if s.signal_type == "course_enrollment")

        # Determine learning style
        profile.learning_style = self._determine_learning_style(signals)

        # Learning frequency
        if len(education_signals) > 20:
            profile.learning_frequency = "daily"
        elif len(education_signals) > 10:
            profile.learning_frequency = "weekly"
        elif len(education_signals) > 3:
            profile.learning_frequency = "monthly"
        else:
            profile.learning_frequency = "occasional"

        return profile

    def _build_lifestyle_profile(self, signals: List[ExtractedSignal]) -> LifestyleProfile:
        """Build lifestyle profile from signals"""
        profile = LifestyleProfile()

        # Collect lifestyle indicators
        lifestyle_indicators = set()
        for signal in signals:
            lifestyle_indicators.update(signal.lifestyle_indicators)

        profile.lifestyle_indicators = list(lifestyle_indicators)[:20]

        # Health conscious
        health_signals = [s for s in signals if s.category == SignalCategory.HEALTH_FITNESS]
        profile.health_conscious = len(health_signals) > 3

        # Activity level
        fitness_signals = sum(1 for s in signals if s.subcategory in ["fitness_tracking", "fitness_classes", "sports"])
        if fitness_signals > 10:
            profile.activity_level = "very_active"
        elif fitness_signals > 5:
            profile.activity_level = "active"
        elif fitness_signals > 0:
            profile.activity_level = "moderate"
        else:
            profile.activity_level = "unknown"

        # Travel frequency
        travel_signals = [s for s in signals if s.category == SignalCategory.TRAVEL]
        if len(travel_signals) > 10:
            profile.travel_frequency = "very_frequent"
        elif len(travel_signals) > 5:
            profile.travel_frequency = "frequent"
        elif len(travel_signals) > 0:
            profile.travel_frequency = "occasional"
        else:
            profile.travel_frequency = "rare"

        # Hobbies
        hobby_categories = [SignalCategory.GAMING, SignalCategory.CREATIVE, SignalCategory.HEALTH_FITNESS]
        hobbies = set()
        for signal in signals:
            if signal.category in hobby_categories:
                hobbies.add(signal.subcategory)
                hobbies.update(signal.topics[:2])

        profile.hobbies = list(hobbies)[:10]

        return profile

    def _build_professional_profile(self, signals: List[ExtractedSignal]) -> ProfessionalProfile:
        """Build professional profile from signals"""
        profile = ProfessionalProfile()

        prof_signals = [s for s in signals if s.category == SignalCategory.PROFESSIONAL]

        # Job search active
        job_alerts = sum(1 for s in signals if s.signal_type == "job_alert")
        profile.job_search_active = job_alerts > 3

        # Freelance signals
        freelance_platforms = ["upwork", "fiverr", "toptal", "freelancer"]
        profile.freelance_signals = any(
            any(fp in s.source.lower() for fp in freelance_platforms)
            for s in signals
        )

        # Professional interests
        prof_interests = set()
        for signal in prof_signals:
            prof_interests.update(signal.topics)
            prof_interests.update(signal.interest_indicators)

        profile.professional_interests = list(prof_interests)[:10]

        # Career stage inference
        if profile.job_search_active and len(prof_signals) < 5:
            profile.career_stage = "early_career"
        elif profile.freelance_signals:
            profile.career_stage = "mid_career"
        else:
            profile.career_stage = "unknown"

        # Leadership signals
        leadership_keywords = ["leadership", "management", "executive", "director", "lead"]
        profile.leadership_signals = any(
            any(kw in s.title.lower() if s.title else False for kw in leadership_keywords)
            for s in signals
        )

        return profile

    def _build_behavior_profile(self, signals: List[ExtractedSignal]) -> BehaviorProfile:
        """Build behavior profile from signals"""
        profile = BehaviorProfile()

        # Engagement level
        if len(signals) > 200:
            profile.engagement_level = EngagementLevel.POWER_USER
        elif len(signals) > 100:
            profile.engagement_level = EngagementLevel.ACTIVE
        elif len(signals) > 30:
            profile.engagement_level = EngagementLevel.MODERATE
        else:
            profile.engagement_level = EngagementLevel.CASUAL

        # Spending tier
        amounts = [s.amount for s in signals if s.amount]
        if amounts:
            avg_amount = sum(amounts) / len(amounts)
            if avg_amount > 200:
                profile.spending_tier = SpendingTier.LUXURY
            elif avg_amount > 50:
                profile.spending_tier = SpendingTier.PREMIUM
            elif avg_amount > 20:
                profile.spending_tier = SpendingTier.MODERATE
            else:
                profile.spending_tier = SpendingTier.BUDGET

        # Tech savviness
        tech_signals = [s for s in signals if s.category == SignalCategory.TECHNOLOGY]
        dev_signals = sum(1 for s in tech_signals if s.subcategory in ["development", "devops", "cloud"])

        if dev_signals > 10:
            profile.tech_savviness = TechSavviness.EXPERT
        elif dev_signals > 5 or len(tech_signals) > 20:
            profile.tech_savviness = TechSavviness.ADVANCED
        elif len(tech_signals) > 5:
            profile.tech_savviness = TechSavviness.INTERMEDIATE
        else:
            profile.tech_savviness = TechSavviness.BASIC

        # Subscription count
        profile.subscription_count = sum(1 for s in signals if s.signal_type == "subscription")

        # Shopping categories
        shopping_signals = [s for s in signals if s.category == SignalCategory.SHOPPING]
        shopping_cats = defaultdict(int)
        for s in shopping_signals:
            shopping_cats[s.subcategory] += 1

        sorted_cats = sorted(shopping_cats.items(), key=lambda x: x[1], reverse=True)
        profile.preferred_shopping_categories = [c[0] for c in sorted_cats[:5]]

        # Brand preferences
        brand_counts = defaultdict(int)
        for s in signals:
            brand_counts[s.source] += 1

        sorted_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)
        profile.brand_preferences = [b[0] for b in sorted_brands[:10]]

        return profile

    def _build_content_preferences(self, signals: List[ExtractedSignal]) -> ContentPreferences:
        """Build content preferences from signals"""
        profile = ContentPreferences()

        # Preferred formats
        format_signals = {
            "video": ["streaming_video", "video", "youtube"],
            "article": ["blogging", "newsletters", "news"],
            "podcast": ["streaming_music", "audio"],
            "interactive": ["interactive", "coding"],
        }

        format_counts = defaultdict(int)
        for signal in signals:
            for format_type, subcats in format_signals.items():
                if signal.subcategory in subcats:
                    format_counts[format_type] += 1

        if format_counts:
            profile.preferred_formats = sorted(format_counts.keys(), key=lambda x: format_counts[x], reverse=True)[:3]

        # Topics followed
        topics = set()
        for signal in signals:
            topics.update(signal.topics)
        profile.topics_followed = list(topics)[:15]

        # Newsletter categories
        newsletter_signals = [s for s in signals if s.signal_type == "newsletter"]
        newsletter_cats = set()
        for s in newsletter_signals:
            newsletter_cats.add(s.subcategory)
            newsletter_cats.update(s.topics[:2])
        profile.newsletter_categories = list(newsletter_cats)[:10]

        # Media platforms
        media_signals = [s for s in signals if s.category in [SignalCategory.NEWS_MEDIA, SignalCategory.ENTERTAINMENT]]
        platforms = set(s.source for s in media_signals)
        profile.media_platforms = list(platforms)[:10]

        # Content frequency
        news_count = sum(1 for s in signals if s.category == SignalCategory.NEWS_MEDIA)
        if news_count > 50:
            profile.content_frequency = "heavy"
        elif news_count > 20:
            profile.content_frequency = "moderate"
        else:
            profile.content_frequency = "light"

        return profile

    def _determine_learning_style(self, signals: List[ExtractedSignal]) -> LearningStyle:
        """Determine preferred learning style"""
        style_scores = defaultdict(int)

        video_platforms = ["coursera", "udemy", "youtube", "skillshare", "masterclass", "linkedin"]
        reading_platforms = ["medium", "substack", "kindle", "scribd"]
        interactive_platforms = ["codecademy", "datacamp", "brilliant", "duolingo"]
        audio_platforms = ["audible", "spotify", "podcast"]

        for signal in signals:
            source_lower = signal.source.lower()

            if any(p in source_lower for p in video_platforms):
                style_scores[LearningStyle.VISUAL] += 1
            if any(p in source_lower for p in reading_platforms):
                style_scores[LearningStyle.READING] += 1
            if any(p in source_lower for p in interactive_platforms):
                style_scores[LearningStyle.INTERACTIVE] += 1
            if any(p in source_lower for p in audio_platforms):
                style_scores[LearningStyle.AUDIO] += 1

        if not style_scores:
            return LearningStyle.MIXED

        max_style = max(style_scores.items(), key=lambda x: x[1])

        # If no clear winner, return mixed
        if max_style[1] < 3:
            return LearningStyle.MIXED

        return max_style[0]

    def _categorize_interests(self, interests: List[tuple]) -> Dict[str, List[str]]:
        """Categorize interests into groups"""
        categories = {
            "technology": ["programming", "technology", "software", "coding", "data", "ai", "machine_learning"],
            "creative": ["design", "art", "photography", "music", "writing", "creative"],
            "business": ["business", "marketing", "finance", "investing", "management"],
            "health": ["fitness", "health", "wellness", "meditation", "nutrition"],
            "lifestyle": ["travel", "food", "cooking", "gaming", "entertainment"],
            "learning": ["education", "learning", "self_improvement", "career_development"],
        }

        result = defaultdict(list)

        for interest, score in interests:
            for category, keywords in categories.items():
                if any(kw in interest.lower() for kw in keywords):
                    result[category].append(interest)
                    break
            else:
                result["other"].append(interest)

        return dict(result)

    def _generate_persona_tags(self, persona: UserPersona) -> List[str]:
        """Generate quick descriptor tags for the persona"""
        tags = []

        # Learning tags
        if persona.learning.certificates_earned > 5:
            tags.append("certified_learner")
        if persona.learning.learning_frequency == "daily":
            tags.append("daily_learner")
        if "programming" in persona.interests.primary_interests:
            tags.append("coder")

        # Tech tags
        if persona.behavior.tech_savviness == TechSavviness.EXPERT:
            tags.append("tech_expert")
        elif persona.behavior.tech_savviness == TechSavviness.ADVANCED:
            tags.append("tech_savvy")

        # Lifestyle tags
        if persona.lifestyle.health_conscious:
            tags.append("health_conscious")
        if persona.lifestyle.travel_frequency in ["frequent", "very_frequent"]:
            tags.append("traveler")

        # Professional tags
        if persona.professional.job_search_active:
            tags.append("job_seeker")
        if persona.professional.freelance_signals:
            tags.append("freelancer")
        if persona.professional.leadership_signals:
            tags.append("leader")

        # Behavior tags
        if persona.behavior.engagement_level == EngagementLevel.POWER_USER:
            tags.append("power_user")
        if persona.behavior.spending_tier == SpendingTier.PREMIUM:
            tags.append("premium_customer")

        # Interest tags
        for interest in persona.interests.primary_interests[:3]:
            tags.append(f"{interest}_enthusiast")

        return tags[:15]

    def _calculate_confidence(self, signals: List[ExtractedSignal], persona: UserPersona) -> float:
        """Calculate confidence score for the persona"""
        # Base confidence on signal count
        signal_confidence = min(len(signals) / 100, 0.4)

        # Confidence from diversity of categories
        category_confidence = min(len(persona.categories_found) / 10, 0.2)

        # Confidence from date range
        date_confidence = min(persona.date_range_days / 180, 0.2)

        # Confidence from verified data
        verified_confidence = 0.0
        if persona.skills.verified_skills:
            verified_confidence = 0.1
        if persona.learning.certificates_earned > 0:
            verified_confidence += 0.1

        total = signal_confidence + category_confidence + date_confidence + verified_confidence

        return round(min(total, 1.0), 3)

    def _integrate_llm_insights(self, persona: UserPersona, llm_insights: Dict):
        """Integrate LLM-derived insights into persona"""
        # Add LLM-inferred interests
        if "interests" in llm_insights:
            for interest in llm_insights["interests"]:
                if interest not in persona.interests.primary_interests:
                    persona.interests.secondary_interests.append(interest)

        # Add LLM-inferred career signals
        if "career_signals" in llm_insights:
            persona.professional.professional_interests.extend(llm_insights["career_signals"])

        # Add LLM-inferred goals
        if "learning_goals" in llm_insights:
            persona.learning.topics_studied.extend(llm_insights["learning_goals"])

        # Boost confidence if LLM confirms
        if llm_insights.get("confidence", 0) > 0.7:
            persona.confidence_score = min(persona.confidence_score + 0.1, 1.0)
