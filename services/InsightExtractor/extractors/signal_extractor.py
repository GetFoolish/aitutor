"""
Signal Extractor - Comprehensive email analysis for user persona building

Extracts signals from ALL types of emails to build a complete user profile:
- Shopping behavior & purchase history
- Subscriptions & memberships
- Travel & lifestyle patterns
- Professional & career signals
- Social & community engagement
- Entertainment & media consumption
- Health & fitness activities
- Financial behavior
- Technology usage
- Hobbies & interests
"""
import re
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from shared.logging_config import get_logger
from services.InsightExtractor.gmail_client import RawEmail

logger = get_logger(__name__)


class SignalCategory(str, Enum):
    """Broad categories of signals we extract"""
    EDUCATION = "education"
    SHOPPING = "shopping"
    SUBSCRIPTION = "subscription"
    TRAVEL = "travel"
    PROFESSIONAL = "professional"
    SOCIAL = "social"
    ENTERTAINMENT = "entertainment"
    HEALTH_FITNESS = "health_fitness"
    FINANCE = "finance"
    TECHNOLOGY = "technology"
    FOOD_LIFESTYLE = "food_lifestyle"
    CREATIVE = "creative"
    GAMING = "gaming"
    NEWS_MEDIA = "news_media"
    EVENTS = "events"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass
class ExtractedSignal:
    """A single extracted signal from an email"""
    category: SignalCategory
    subcategory: str
    source: str  # sender domain or platform
    signal_type: str  # purchase, subscription, notification, newsletter, etc.

    # Extracted data
    title: Optional[str] = None  # Product name, course name, event name, etc.
    description: Optional[str] = None
    topics: List[str] = field(default_factory=list)

    # Metadata
    amount: Optional[float] = None  # Purchase amount if applicable
    currency: Optional[str] = None
    date: Optional[datetime] = None

    # Inferred attributes
    interest_indicators: List[str] = field(default_factory=list)
    skill_indicators: List[str] = field(default_factory=list)
    lifestyle_indicators: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.5
    source_email_id: str = ""


# Comprehensive domain mapping - maps sender domains to categories and metadata
DOMAIN_MAPPING = {
    # ==================== EDUCATION ====================
    "coursera.org": {"category": SignalCategory.EDUCATION, "subcategory": "online_courses", "platform": "Coursera"},
    "udemy.com": {"category": SignalCategory.EDUCATION, "subcategory": "online_courses", "platform": "Udemy"},
    "edx.org": {"category": SignalCategory.EDUCATION, "subcategory": "online_courses", "platform": "edX"},
    "linkedin.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "networking", "platform": "LinkedIn"},
    "khanacademy.org": {"category": SignalCategory.EDUCATION, "subcategory": "online_courses", "platform": "Khan Academy"},
    "skillshare.com": {"category": SignalCategory.EDUCATION, "subcategory": "creative_courses", "platform": "Skillshare"},
    "pluralsight.com": {"category": SignalCategory.EDUCATION, "subcategory": "tech_courses", "platform": "Pluralsight"},
    "udacity.com": {"category": SignalCategory.EDUCATION, "subcategory": "tech_courses", "platform": "Udacity"},
    "codecademy.com": {"category": SignalCategory.EDUCATION, "subcategory": "coding", "platform": "Codecademy"},
    "datacamp.com": {"category": SignalCategory.EDUCATION, "subcategory": "data_science", "platform": "DataCamp"},
    "brilliant.org": {"category": SignalCategory.EDUCATION, "subcategory": "math_science", "platform": "Brilliant"},
    "masterclass.com": {"category": SignalCategory.EDUCATION, "subcategory": "creative_courses", "platform": "MasterClass"},
    "duolingo.com": {"category": SignalCategory.EDUCATION, "subcategory": "languages", "platform": "Duolingo"},
    "babbel.com": {"category": SignalCategory.EDUCATION, "subcategory": "languages", "platform": "Babbel"},
    "memrise.com": {"category": SignalCategory.EDUCATION, "subcategory": "languages", "platform": "Memrise"},
    "futurelearn.com": {"category": SignalCategory.EDUCATION, "subcategory": "online_courses", "platform": "FutureLearn"},
    "class-central.com": {"category": SignalCategory.EDUCATION, "subcategory": "course_aggregator", "platform": "Class Central"},
    "mit.edu": {"category": SignalCategory.EDUCATION, "subcategory": "university", "platform": "MIT"},
    "stanford.edu": {"category": SignalCategory.EDUCATION, "subcategory": "university", "platform": "Stanford"},
    "harvard.edu": {"category": SignalCategory.EDUCATION, "subcategory": "university", "platform": "Harvard"},

    # ==================== SHOPPING ====================
    "amazon.com": {"category": SignalCategory.SHOPPING, "subcategory": "general", "platform": "Amazon"},
    "amazon.in": {"category": SignalCategory.SHOPPING, "subcategory": "general", "platform": "Amazon India"},
    "amazon.co.uk": {"category": SignalCategory.SHOPPING, "subcategory": "general", "platform": "Amazon UK"},
    "ebay.com": {"category": SignalCategory.SHOPPING, "subcategory": "marketplace", "platform": "eBay"},
    "etsy.com": {"category": SignalCategory.SHOPPING, "subcategory": "handmade", "platform": "Etsy"},
    "walmart.com": {"category": SignalCategory.SHOPPING, "subcategory": "retail", "platform": "Walmart"},
    "target.com": {"category": SignalCategory.SHOPPING, "subcategory": "retail", "platform": "Target"},
    "bestbuy.com": {"category": SignalCategory.SHOPPING, "subcategory": "electronics", "platform": "Best Buy"},
    "newegg.com": {"category": SignalCategory.SHOPPING, "subcategory": "electronics", "platform": "Newegg"},
    "bhphotovideo.com": {"category": SignalCategory.SHOPPING, "subcategory": "photo_video", "platform": "B&H Photo"},
    "adorama.com": {"category": SignalCategory.SHOPPING, "subcategory": "photo_video", "platform": "Adorama"},
    "alibaba.com": {"category": SignalCategory.SHOPPING, "subcategory": "wholesale", "platform": "Alibaba"},
    "aliexpress.com": {"category": SignalCategory.SHOPPING, "subcategory": "marketplace", "platform": "AliExpress"},
    "flipkart.com": {"category": SignalCategory.SHOPPING, "subcategory": "general", "platform": "Flipkart"},
    "shopify.com": {"category": SignalCategory.SHOPPING, "subcategory": "ecommerce", "platform": "Shopify Store"},
    "wayfair.com": {"category": SignalCategory.SHOPPING, "subcategory": "home", "platform": "Wayfair"},
    "ikea.com": {"category": SignalCategory.SHOPPING, "subcategory": "furniture", "platform": "IKEA"},
    "homedepot.com": {"category": SignalCategory.SHOPPING, "subcategory": "home_improvement", "platform": "Home Depot"},
    "lowes.com": {"category": SignalCategory.SHOPPING, "subcategory": "home_improvement", "platform": "Lowe's"},
    "nike.com": {"category": SignalCategory.SHOPPING, "subcategory": "sports_apparel", "platform": "Nike"},
    "adidas.com": {"category": SignalCategory.SHOPPING, "subcategory": "sports_apparel", "platform": "Adidas"},
    "zara.com": {"category": SignalCategory.SHOPPING, "subcategory": "fashion", "platform": "Zara"},
    "hm.com": {"category": SignalCategory.SHOPPING, "subcategory": "fashion", "platform": "H&M"},
    "uniqlo.com": {"category": SignalCategory.SHOPPING, "subcategory": "fashion", "platform": "Uniqlo"},
    "nordstrom.com": {"category": SignalCategory.SHOPPING, "subcategory": "fashion", "platform": "Nordstrom"},
    "macys.com": {"category": SignalCategory.SHOPPING, "subcategory": "department_store", "platform": "Macy's"},
    "sephora.com": {"category": SignalCategory.SHOPPING, "subcategory": "beauty", "platform": "Sephora"},
    "ulta.com": {"category": SignalCategory.SHOPPING, "subcategory": "beauty", "platform": "Ulta"},

    # ==================== SUBSCRIPTIONS ====================
    "netflix.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "Netflix"},
    "spotify.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_music", "platform": "Spotify"},
    "apple.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "apple_services", "platform": "Apple"},
    "hulu.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "Hulu"},
    "disneyplus.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "Disney+"},
    "hbomax.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "HBO Max"},
    "max.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "Max"},
    "primevideo.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_video", "platform": "Prime Video"},
    "youtube.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "video", "platform": "YouTube"},
    "twitch.tv": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "streaming_live", "platform": "Twitch"},
    "audible.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "audiobooks", "platform": "Audible"},
    "kindle.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "ebooks", "platform": "Kindle"},
    "scribd.com": {"category": SignalCategory.ENTERTAINMENT, "subcategory": "ebooks", "platform": "Scribd"},
    "blinkist.com": {"category": SignalCategory.EDUCATION, "subcategory": "book_summaries", "platform": "Blinkist"},

    # ==================== TECHNOLOGY ====================
    "github.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development", "platform": "GitHub"},
    "gitlab.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development", "platform": "GitLab"},
    "bitbucket.org": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development", "platform": "Bitbucket"},
    "stackoverflow.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development", "platform": "Stack Overflow"},
    "digitalocean.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "DigitalOcean"},
    "aws.amazon.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "AWS"},
    "cloud.google.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "Google Cloud"},
    "azure.microsoft.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "Azure"},
    "heroku.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "Heroku"},
    "vercel.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "Vercel"},
    "netlify.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "cloud", "platform": "Netlify"},
    "docker.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "devops", "platform": "Docker"},
    "jetbrains.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development_tools", "platform": "JetBrains"},
    "visualstudio.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "development_tools", "platform": "Visual Studio"},
    "figma.com": {"category": SignalCategory.CREATIVE, "subcategory": "design", "platform": "Figma"},
    "sketch.com": {"category": SignalCategory.CREATIVE, "subcategory": "design", "platform": "Sketch"},
    "adobe.com": {"category": SignalCategory.CREATIVE, "subcategory": "creative_suite", "platform": "Adobe"},
    "canva.com": {"category": SignalCategory.CREATIVE, "subcategory": "design", "platform": "Canva"},
    "notion.so": {"category": SignalCategory.TECHNOLOGY, "subcategory": "productivity", "platform": "Notion"},
    "todoist.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "productivity", "platform": "Todoist"},
    "asana.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "project_management", "platform": "Asana"},
    "trello.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "project_management", "platform": "Trello"},
    "slack.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "communication", "platform": "Slack"},
    "zoom.us": {"category": SignalCategory.TECHNOLOGY, "subcategory": "communication", "platform": "Zoom"},
    "dropbox.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "storage", "platform": "Dropbox"},
    "1password.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "security", "platform": "1Password"},
    "lastpass.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "security", "platform": "LastPass"},
    "grammarly.com": {"category": SignalCategory.TECHNOLOGY, "subcategory": "writing", "platform": "Grammarly"},

    # ==================== PROFESSIONAL ====================
    "indeed.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "job_search", "platform": "Indeed"},
    "glassdoor.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "job_search", "platform": "Glassdoor"},
    "monster.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "job_search", "platform": "Monster"},
    "ziprecruiter.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "job_search", "platform": "ZipRecruiter"},
    "angel.co": {"category": SignalCategory.PROFESSIONAL, "subcategory": "startup_jobs", "platform": "AngelList"},
    "wellfound.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "startup_jobs", "platform": "Wellfound"},
    "upwork.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "freelance", "platform": "Upwork"},
    "fiverr.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "freelance", "platform": "Fiverr"},
    "toptal.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "freelance", "platform": "Toptal"},
    "calendly.com": {"category": SignalCategory.PROFESSIONAL, "subcategory": "scheduling", "platform": "Calendly"},

    # ==================== TRAVEL ====================
    "booking.com": {"category": SignalCategory.TRAVEL, "subcategory": "hotels", "platform": "Booking.com"},
    "airbnb.com": {"category": SignalCategory.TRAVEL, "subcategory": "accommodation", "platform": "Airbnb"},
    "expedia.com": {"category": SignalCategory.TRAVEL, "subcategory": "travel_booking", "platform": "Expedia"},
    "kayak.com": {"category": SignalCategory.TRAVEL, "subcategory": "travel_search", "platform": "Kayak"},
    "tripadvisor.com": {"category": SignalCategory.TRAVEL, "subcategory": "travel_reviews", "platform": "TripAdvisor"},
    "hotels.com": {"category": SignalCategory.TRAVEL, "subcategory": "hotels", "platform": "Hotels.com"},
    "marriott.com": {"category": SignalCategory.TRAVEL, "subcategory": "hotels", "platform": "Marriott"},
    "hilton.com": {"category": SignalCategory.TRAVEL, "subcategory": "hotels", "platform": "Hilton"},
    "delta.com": {"category": SignalCategory.TRAVEL, "subcategory": "airlines", "platform": "Delta"},
    "united.com": {"category": SignalCategory.TRAVEL, "subcategory": "airlines", "platform": "United"},
    "southwest.com": {"category": SignalCategory.TRAVEL, "subcategory": "airlines", "platform": "Southwest"},
    "aa.com": {"category": SignalCategory.TRAVEL, "subcategory": "airlines", "platform": "American Airlines"},
    "uber.com": {"category": SignalCategory.TRAVEL, "subcategory": "rideshare", "platform": "Uber"},
    "lyft.com": {"category": SignalCategory.TRAVEL, "subcategory": "rideshare", "platform": "Lyft"},

    # ==================== FOOD & LIFESTYLE ====================
    "doordash.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "food_delivery", "platform": "DoorDash"},
    "ubereats.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "food_delivery", "platform": "Uber Eats"},
    "grubhub.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "food_delivery", "platform": "Grubhub"},
    "postmates.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "food_delivery", "platform": "Postmates"},
    "instacart.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "grocery_delivery", "platform": "Instacart"},
    "hellofresh.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "meal_kits", "platform": "HelloFresh"},
    "blueapron.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "meal_kits", "platform": "Blue Apron"},
    "opentable.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "restaurant_reservations", "platform": "OpenTable"},
    "yelp.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "reviews", "platform": "Yelp"},
    "starbucks.com": {"category": SignalCategory.FOOD_LIFESTYLE, "subcategory": "coffee", "platform": "Starbucks"},

    # ==================== HEALTH & FITNESS ====================
    "myfitnesspal.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "nutrition", "platform": "MyFitnessPal"},
    "fitbit.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "fitness_tracking", "platform": "Fitbit"},
    "strava.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "fitness_tracking", "platform": "Strava"},
    "peloton.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "fitness_equipment", "platform": "Peloton"},
    "headspace.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "meditation", "platform": "Headspace"},
    "calm.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "meditation", "platform": "Calm"},
    "noom.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "weight_loss", "platform": "Noom"},
    "classpass.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "fitness_classes", "platform": "ClassPass"},
    "mindbody.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "fitness_classes", "platform": "Mindbody"},
    "nike.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "sports", "platform": "Nike"},
    "underarmour.com": {"category": SignalCategory.HEALTH_FITNESS, "subcategory": "sports", "platform": "Under Armour"},

    # ==================== FINANCE ====================
    "paypal.com": {"category": SignalCategory.FINANCE, "subcategory": "payments", "platform": "PayPal"},
    "venmo.com": {"category": SignalCategory.FINANCE, "subcategory": "payments", "platform": "Venmo"},
    "squareup.com": {"category": SignalCategory.FINANCE, "subcategory": "payments", "platform": "Square"},
    "stripe.com": {"category": SignalCategory.FINANCE, "subcategory": "payments", "platform": "Stripe"},
    "robinhood.com": {"category": SignalCategory.FINANCE, "subcategory": "investing", "platform": "Robinhood"},
    "fidelity.com": {"category": SignalCategory.FINANCE, "subcategory": "investing", "platform": "Fidelity"},
    "vanguard.com": {"category": SignalCategory.FINANCE, "subcategory": "investing", "platform": "Vanguard"},
    "schwab.com": {"category": SignalCategory.FINANCE, "subcategory": "investing", "platform": "Charles Schwab"},
    "coinbase.com": {"category": SignalCategory.FINANCE, "subcategory": "crypto", "platform": "Coinbase"},
    "binance.com": {"category": SignalCategory.FINANCE, "subcategory": "crypto", "platform": "Binance"},
    "mint.com": {"category": SignalCategory.FINANCE, "subcategory": "budgeting", "platform": "Mint"},
    "ynab.com": {"category": SignalCategory.FINANCE, "subcategory": "budgeting", "platform": "YNAB"},
    "creditkarma.com": {"category": SignalCategory.FINANCE, "subcategory": "credit", "platform": "Credit Karma"},

    # ==================== GAMING ====================
    "steampowered.com": {"category": SignalCategory.GAMING, "subcategory": "pc_gaming", "platform": "Steam"},
    "epicgames.com": {"category": SignalCategory.GAMING, "subcategory": "pc_gaming", "platform": "Epic Games"},
    "playstation.com": {"category": SignalCategory.GAMING, "subcategory": "console_gaming", "platform": "PlayStation"},
    "xbox.com": {"category": SignalCategory.GAMING, "subcategory": "console_gaming", "platform": "Xbox"},
    "nintendo.com": {"category": SignalCategory.GAMING, "subcategory": "console_gaming", "platform": "Nintendo"},
    "ea.com": {"category": SignalCategory.GAMING, "subcategory": "gaming_publisher", "platform": "EA"},
    "ubisoft.com": {"category": SignalCategory.GAMING, "subcategory": "gaming_publisher", "platform": "Ubisoft"},
    "blizzard.com": {"category": SignalCategory.GAMING, "subcategory": "gaming_publisher", "platform": "Blizzard"},
    "riotgames.com": {"category": SignalCategory.GAMING, "subcategory": "gaming_publisher", "platform": "Riot Games"},
    "discord.com": {"category": SignalCategory.GAMING, "subcategory": "gaming_social", "platform": "Discord"},

    # ==================== SOCIAL MEDIA ====================
    "twitter.com": {"category": SignalCategory.SOCIAL, "subcategory": "social_network", "platform": "Twitter"},
    "x.com": {"category": SignalCategory.SOCIAL, "subcategory": "social_network", "platform": "X"},
    "facebook.com": {"category": SignalCategory.SOCIAL, "subcategory": "social_network", "platform": "Facebook"},
    "instagram.com": {"category": SignalCategory.SOCIAL, "subcategory": "social_network", "platform": "Instagram"},
    "tiktok.com": {"category": SignalCategory.SOCIAL, "subcategory": "social_network", "platform": "TikTok"},
    "reddit.com": {"category": SignalCategory.SOCIAL, "subcategory": "community", "platform": "Reddit"},
    "pinterest.com": {"category": SignalCategory.SOCIAL, "subcategory": "visual_discovery", "platform": "Pinterest"},
    "snapchat.com": {"category": SignalCategory.SOCIAL, "subcategory": "messaging", "platform": "Snapchat"},
    "whatsapp.com": {"category": SignalCategory.SOCIAL, "subcategory": "messaging", "platform": "WhatsApp"},
    "telegram.org": {"category": SignalCategory.SOCIAL, "subcategory": "messaging", "platform": "Telegram"},

    # ==================== NEWS & MEDIA ====================
    "medium.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "blogging", "platform": "Medium"},
    "substack.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "newsletters", "platform": "Substack"},
    "nytimes.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "NY Times"},
    "wsj.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "Wall Street Journal"},
    "washingtonpost.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "Washington Post"},
    "theguardian.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "The Guardian"},
    "bbc.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "BBC"},
    "cnn.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "news", "platform": "CNN"},
    "forbes.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "business_news", "platform": "Forbes"},
    "bloomberg.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "business_news", "platform": "Bloomberg"},
    "techcrunch.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "tech_news", "platform": "TechCrunch"},
    "theverge.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "tech_news", "platform": "The Verge"},
    "wired.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "tech_news", "platform": "Wired"},
    "arstechnica.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "tech_news", "platform": "Ars Technica"},
    "hackernews.com": {"category": SignalCategory.NEWS_MEDIA, "subcategory": "tech_news", "platform": "Hacker News"},

    # ==================== EVENTS ====================
    "eventbrite.com": {"category": SignalCategory.EVENTS, "subcategory": "ticketing", "platform": "Eventbrite"},
    "meetup.com": {"category": SignalCategory.EVENTS, "subcategory": "community_events", "platform": "Meetup"},
    "ticketmaster.com": {"category": SignalCategory.EVENTS, "subcategory": "entertainment_tickets", "platform": "Ticketmaster"},
    "stubhub.com": {"category": SignalCategory.EVENTS, "subcategory": "entertainment_tickets", "platform": "StubHub"},
    "seatgeek.com": {"category": SignalCategory.EVENTS, "subcategory": "entertainment_tickets", "platform": "SeatGeek"},
    "luma.com": {"category": SignalCategory.EVENTS, "subcategory": "tech_events", "platform": "Luma"},
    "lu.ma": {"category": SignalCategory.EVENTS, "subcategory": "tech_events", "platform": "Luma"},
}

# Email type patterns - detect what kind of email this is
EMAIL_TYPE_PATTERNS = {
    "purchase": [
        r"order\s*(?:confirmation|confirmed|received|#)",
        r"your\s+(?:order|purchase)",
        r"receipt\s+for",
        r"payment\s+(?:confirmation|received|successful)",
        r"thank\s+you\s+for\s+(?:your\s+)?(?:order|purchase)",
        r"invoice\s+#?\d+",
        r"you\s+bought",
        r"order\s+shipped",
        r"shipping\s+confirmation",
    ],
    "subscription": [
        r"subscription\s+(?:confirmation|activated|renewed|started)",
        r"welcome\s+to\s+(?:your\s+)?(?:\w+\s+)?(?:subscription|membership|premium)",
        r"your\s+(?:\w+\s+)?(?:subscription|membership)",
        r"trial\s+(?:started|activated|beginning)",
        r"free\s+trial",
        r"billing\s+(?:statement|summary)",
        r"renewal\s+(?:notice|confirmation)",
        r"membership\s+(?:confirmation|activated)",
    ],
    "notification": [
        r"new\s+(?:message|comment|reply|follower|connection)",
        r"(?:someone|a\s+user)\s+(?:mentioned|tagged|replied)",
        r"activity\s+(?:update|summary|digest)",
        r"weekly\s+(?:digest|summary|update)",
        r"daily\s+(?:digest|summary|update)",
        r"you\s+have\s+\d+\s+new",
        r"notification\s+from",
    ],
    "newsletter": [
        r"newsletter",
        r"weekly\s+(?:roundup|digest|update)",
        r"monthly\s+(?:roundup|digest|update)",
        r"this\s+week\s+in",
        r"top\s+stories",
        r"curated\s+(?:links|articles|content)",
        r"unsubscribe",
        r"view\s+in\s+browser",
    ],
    "course_enrollment": [
        r"welcome\s+to\s+(?:the\s+)?(?:course|class|program)",
        r"you(?:'ve|\s+have)\s+enrolled",
        r"enrollment\s+confirmed",
        r"start(?:ed|ing)\s+learning",
        r"course\s+begins",
        r"class\s+starts",
    ],
    "course_progress": [
        r"continue\s+(?:learning|watching|your\s+course)",
        r"you(?:'re|\s+are)\s+\d+%\s+(?:through|complete)",
        r"(?:new\s+)?lesson\s+available",
        r"assignment\s+(?:due|reminder)",
        r"quiz\s+(?:available|reminder)",
        r"certificate\s+(?:available|ready)",
    ],
    "certificate": [
        r"congratulations.+?(?:completed|earned|passed|graduated)",
        r"certificate\s+(?:of\s+completion|earned|awarded)",
        r"you(?:'ve|\s+have)\s+(?:completed|earned|passed)",
        r"credential\s+(?:earned|awarded)",
        r"badge\s+earned",
    ],
    "job_alert": [
        r"job\s+(?:alert|match|recommendation)",
        r"new\s+jobs?\s+(?:matching|for\s+you)",
        r"(?:apply|applied)\s+(?:now|for)",
        r"hiring\s+(?:now|manager)",
        r"we(?:'re|\s+are)\s+hiring",
        r"your\s+application",
        r"interview\s+(?:invitation|request|scheduled)",
    ],
    "travel_booking": [
        r"booking\s+(?:confirmation|confirmed)",
        r"reservation\s+(?:confirmation|confirmed)",
        r"itinerary",
        r"flight\s+(?:confirmation|details|itinerary)",
        r"hotel\s+(?:confirmation|reservation)",
        r"check-?in\s+(?:details|reminder)",
        r"your\s+trip\s+to",
    ],
    "event_ticket": [
        r"ticket(?:s)?\s+(?:confirmation|confirmed|purchased)",
        r"event\s+(?:confirmation|registration|ticket)",
        r"you(?:'re|\s+are)\s+(?:registered|going)",
        r"rsvp\s+confirmed",
        r"your\s+(?:ticket|registration)\s+for",
    ],
    "financial": [
        r"account\s+(?:statement|summary|activity)",
        r"transaction\s+(?:alert|notification)",
        r"payment\s+(?:due|reminder|received)",
        r"deposit\s+(?:received|confirmed)",
        r"withdrawal\s+(?:processed|confirmed)",
        r"balance\s+(?:update|alert)",
        r"stock\s+(?:alert|update)",
        r"dividend\s+(?:payment|received)",
    ],
    "security": [
        r"security\s+(?:alert|notification|update)",
        r"new\s+(?:sign-?in|login|device)",
        r"password\s+(?:changed|reset|updated)",
        r"two-?factor\s+(?:authentication|verification)",
        r"verify\s+your\s+(?:email|account|identity)",
        r"suspicious\s+activity",
    ],
}


class SignalExtractor:
    """
    Comprehensive signal extractor that analyzes ALL email types
    to build a complete user profile.
    """

    def __init__(self):
        self.domain_mapping = DOMAIN_MAPPING
        self.email_type_patterns = EMAIL_TYPE_PATTERNS

    def extract_signals(self, emails: List[RawEmail]) -> List[ExtractedSignal]:
        """
        Extract signals from a list of emails.

        Args:
            emails: List of raw emails from Gmail

        Returns:
            List of extracted signals
        """
        signals = []

        for email in emails:
            try:
                email_signals = self._extract_from_email(email)
                signals.extend(email_signals)
            except Exception as e:
                logger.warning(f"[SIGNAL_EXTRACTOR] Error processing email {email.message_id}: {e}")
                continue

        logger.info(f"[SIGNAL_EXTRACTOR] Extracted {len(signals)} signals from {len(emails)} emails")
        return signals

    def _extract_from_email(self, email: RawEmail) -> List[ExtractedSignal]:
        """Extract signals from a single email"""
        signals = []

        # Get domain info
        domain_info = self._get_domain_info(email.sender_domain)

        # Detect email type
        email_type = self._detect_email_type(email)

        # Extract based on category
        if domain_info:
            category = domain_info["category"]
            subcategory = domain_info["subcategory"]
            platform = domain_info["platform"]
        else:
            category = self._infer_category(email, email_type)
            subcategory = email_type or "general"
            platform = email.sender_domain

        # Create base signal
        signal = ExtractedSignal(
            category=category,
            subcategory=subcategory,
            source=platform,
            signal_type=email_type or "notification",
            date=email.date,
            confidence=0.7 if domain_info else 0.5,
            source_email_id=email.message_id
        )

        # Extract additional details based on email type
        self._enrich_signal(signal, email, email_type)

        signals.append(signal)

        return signals

    def _get_domain_info(self, domain: str) -> Optional[Dict]:
        """Look up domain in mapping"""
        # Direct match
        if domain in self.domain_mapping:
            return self.domain_mapping[domain]

        # Partial match (for subdomains)
        for known_domain, info in self.domain_mapping.items():
            if known_domain in domain or domain.endswith(f".{known_domain}"):
                return info

        return None

    def _detect_email_type(self, email: RawEmail) -> Optional[str]:
        """Detect what type of email this is"""
        text = f"{email.subject} {email.snippet}".lower()

        for email_type, patterns in self.email_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return email_type

        return None

    def _infer_category(self, email: RawEmail, email_type: Optional[str]) -> SignalCategory:
        """Infer category when domain is unknown"""
        if email_type:
            type_to_category = {
                "purchase": SignalCategory.SHOPPING,
                "subscription": SignalCategory.SUBSCRIPTION,
                "newsletter": SignalCategory.NEWS_MEDIA,
                "course_enrollment": SignalCategory.EDUCATION,
                "course_progress": SignalCategory.EDUCATION,
                "certificate": SignalCategory.EDUCATION,
                "job_alert": SignalCategory.PROFESSIONAL,
                "travel_booking": SignalCategory.TRAVEL,
                "event_ticket": SignalCategory.EVENTS,
                "financial": SignalCategory.FINANCE,
                "security": SignalCategory.TECHNOLOGY,
            }
            return type_to_category.get(email_type, SignalCategory.OTHER)

        return SignalCategory.OTHER

    def _enrich_signal(self, signal: ExtractedSignal, email: RawEmail, email_type: Optional[str]):
        """Enrich signal with additional extracted data"""
        text = f"{email.subject} {email.snippet} {email.body_text[:2000]}"

        # Extract title/item name
        signal.title = self._extract_title(text, email_type)

        # Extract amount if purchase/financial
        if email_type in ["purchase", "subscription", "financial"]:
            amount, currency = self._extract_amount(text)
            signal.amount = amount
            signal.currency = currency

        # Extract topics
        signal.topics = self._extract_topics(text)

        # Extract interest indicators
        signal.interest_indicators = self._extract_interest_indicators(signal)

        # Extract skill indicators (for education/tech)
        if signal.category in [SignalCategory.EDUCATION, SignalCategory.TECHNOLOGY]:
            signal.skill_indicators = self._extract_skill_indicators(text)

        # Extract lifestyle indicators
        signal.lifestyle_indicators = self._extract_lifestyle_indicators(signal)

    def _extract_title(self, text: str, email_type: Optional[str]) -> Optional[str]:
        """Extract the main item/course/event title"""
        patterns = [
            r"(?:enrolled in|started|completed|purchased|ordered|booked)\s+[\"']?([^\"'\n]{5,60})[\"']?",
            r"(?:course|class|program|event|ticket for|order of)\s*[:\-]?\s*[\"']?([^\"'\n]{5,60})[\"']?",
            r"(?:welcome to|thank you for)\s+[\"']?([^\"'\n]{5,60})[\"']?",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # Clean up
                title = re.sub(r'\s+', ' ', title)
                if len(title) > 5 and len(title) < 100:
                    return title

        return None

    def _extract_amount(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract purchase amount and currency"""
        patterns = [
            r"(?:total|amount|price|charged|paid)[:\s]*\$?(\d+(?:\.\d{2})?)\s*(USD|EUR|GBP|INR)?",
            r"\$(\d+(?:\.\d{2})?)",
            r"(\d+(?:\.\d{2})?)\s*(USD|EUR|GBP|INR)",
            r"(?:₹|€|£)(\d+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                currency = match.group(2) if len(match.groups()) > 1 else "USD"
                return amount, currency

        return None, None

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        topics = []
        text_lower = text.lower()

        topic_keywords = {
            "programming": ["python", "javascript", "java", "coding", "programming", "software", "developer"],
            "data_science": ["data science", "machine learning", "ai", "analytics", "data analysis"],
            "design": ["design", "ui", "ux", "graphic", "creative", "figma", "photoshop"],
            "business": ["business", "marketing", "sales", "management", "strategy", "finance"],
            "photography": ["photography", "camera", "photo", "lightroom", "portrait"],
            "music": ["music", "guitar", "piano", "audio", "production", "song"],
            "fitness": ["fitness", "workout", "exercise", "gym", "yoga", "running"],
            "cooking": ["cooking", "recipe", "food", "kitchen", "chef", "baking"],
            "gaming": ["game", "gaming", "playstation", "xbox", "steam", "esports"],
            "travel": ["travel", "flight", "hotel", "vacation", "trip", "destination"],
            "reading": ["book", "reading", "kindle", "ebook", "audiobook", "author"],
            "investing": ["stock", "invest", "trading", "crypto", "portfolio", "dividend"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        return topics[:5]

    def _extract_interest_indicators(self, signal: ExtractedSignal) -> List[str]:
        """Extract interest indicators from signal"""
        indicators = []

        # Category-based indicators
        category_interests = {
            SignalCategory.EDUCATION: ["learning", "self_improvement", "career_development"],
            SignalCategory.TECHNOLOGY: ["technology", "software", "innovation"],
            SignalCategory.CREATIVE: ["creativity", "art", "design"],
            SignalCategory.HEALTH_FITNESS: ["health", "wellness", "fitness"],
            SignalCategory.TRAVEL: ["travel", "exploration", "adventure"],
            SignalCategory.GAMING: ["gaming", "entertainment", "competition"],
            SignalCategory.FINANCE: ["finance", "investing", "money_management"],
        }

        if signal.category in category_interests:
            indicators.extend(category_interests[signal.category])

        # Topic-based indicators
        indicators.extend(signal.topics)

        return list(set(indicators))[:10]

    def _extract_skill_indicators(self, text: str) -> List[str]:
        """Extract skill indicators from text"""
        skills = []
        text_lower = text.lower()

        skill_keywords = [
            "python", "javascript", "java", "c++", "sql", "html", "css",
            "react", "angular", "vue", "node", "django", "flask",
            "machine learning", "deep learning", "data analysis", "statistics",
            "aws", "azure", "gcp", "docker", "kubernetes",
            "photoshop", "illustrator", "figma", "sketch",
            "excel", "tableau", "power bi",
            "project management", "agile", "scrum",
            "leadership", "communication", "presentation",
        ]

        for skill in skill_keywords:
            if skill in text_lower:
                skills.append(skill.replace(" ", "_"))

        return skills[:10]

    def _extract_lifestyle_indicators(self, signal: ExtractedSignal) -> List[str]:
        """Extract lifestyle indicators from signal"""
        indicators = []

        # Subcategory-based lifestyle signals
        subcategory_lifestyle = {
            "streaming_video": ["entertainment_focused", "digital_media_consumer"],
            "streaming_music": ["music_lover", "audio_consumer"],
            "fitness_tracking": ["health_conscious", "active_lifestyle"],
            "meditation": ["wellness_focused", "mindfulness"],
            "food_delivery": ["convenience_oriented", "urban_lifestyle"],
            "meal_kits": ["cooking_interested", "health_conscious"],
            "travel_booking": ["traveler", "explorer"],
            "investing": ["financially_savvy", "future_planning"],
            "online_courses": ["lifelong_learner", "self_improvement"],
            "pc_gaming": ["gamer", "tech_enthusiast"],
        }

        if signal.subcategory in subcategory_lifestyle:
            indicators.extend(subcategory_lifestyle[signal.subcategory])

        # Amount-based indicators (premium vs budget)
        if signal.amount:
            if signal.amount > 100:
                indicators.append("premium_spender")
            elif signal.amount < 20:
                indicators.append("budget_conscious")

        return list(set(indicators))[:5]

    def aggregate_by_category(self, signals: List[ExtractedSignal]) -> Dict[SignalCategory, List[ExtractedSignal]]:
        """Group signals by category"""
        grouped = defaultdict(list)
        for signal in signals:
            grouped[signal.category].append(signal)
        return dict(grouped)

    def get_top_platforms(self, signals: List[ExtractedSignal], limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequent platforms"""
        platform_counts = defaultdict(int)
        for signal in signals:
            platform_counts[signal.source] += 1

        sorted_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_platforms[:limit]

    def get_interest_summary(self, signals: List[ExtractedSignal]) -> Dict[str, float]:
        """Aggregate interests with scores"""
        interest_scores = defaultdict(float)

        for signal in signals:
            weight = signal.confidence

            for interest in signal.interest_indicators:
                interest_scores[interest] += weight

            for topic in signal.topics:
                interest_scores[topic] += weight * 0.8

        # Normalize
        if interest_scores:
            max_score = max(interest_scores.values())
            interest_scores = {k: v / max_score for k, v in interest_scores.items()}

        return dict(sorted(interest_scores.items(), key=lambda x: x[1], reverse=True))
