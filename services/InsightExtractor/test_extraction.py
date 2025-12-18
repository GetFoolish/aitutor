#!/usr/bin/env python3
"""
Test Script for InsightExtractor - Extract your persona from Gmail

Usage:
    1. Set environment variables (or create .env file)
    2. Run: python test_extraction.py
    3. Browser will open for Gmail consent
    4. Your persona will be printed

Required Environment Variables:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GEMINI_API_KEY (optional, for LLM classification)
"""
import os
import sys
import json
import asyncio
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from threading import Thread

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Load .env if exists
try:
    from dotenv import load_dotenv
    # Try local .env first, then project root
    local_env = os.path.join(os.path.dirname(__file__), '.env')
    root_env = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env)
    elif os.path.exists(root_env):
        load_dotenv(root_env)
except ImportError:
    pass

from services.InsightExtractor.gmail_client import GmailClient, GmailOAuthHandler
from services.InsightExtractor.extractors.signal_extractor import SignalExtractor
from services.InsightExtractor.extractors.persona_builder import PersonaBuilder
from services.InsightExtractor.extractors.llm_classifier import LLMClassifier
from services.InsightExtractor.parsers.course_parser import CourseParser
from services.InsightExtractor.parsers.newsletter_parser import NewsletterParser
from services.InsightExtractor.parsers.certificate_parser import CertificateParser


# Configuration
CALLBACK_PORT = 8888
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

# Global to store auth code
auth_code = None
auth_error = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback"""

    def do_GET(self):
        global auth_code, auth_error

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Gmail Connected Successfully!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>window.close();</script>
                </body>
                </html>
            """)
        else:
            auth_error = params.get('error', ['Unknown error'])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Authorization Failed</h1>
                    <p>Error: {auth_error}</p>
                </body>
                </html>
            """.encode())

    def log_message(self, format, *args):
        pass  # Suppress logging


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(title, content):
    """Print a section with title"""
    print(f"\n--- {title} ---")
    if isinstance(content, list):
        for item in content[:10]:  # Limit to 10 items
            print(f"  - {item}")
        if len(content) > 10:
            print(f"  ... and {len(content) - 10} more")
    elif isinstance(content, dict):
        for key, value in list(content.items())[:10]:
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  {content}")


def print_persona(persona):
    """Pretty print the persona"""
    print_header("YOUR PERSONA")

    # Tags
    if persona.persona_tags:
        print("\nPersona Tags:")
        print("  " + " | ".join(persona.persona_tags[:10]))

    # Confidence
    print(f"\nConfidence Score: {persona.confidence_score:.1%}")
    print(f"Signals Analyzed: {persona.signals_analyzed}")
    print(f"Date Range: {persona.date_range_days} days")

    # Interests
    print_header("INTERESTS")
    print_section("Primary Interests", persona.interests.primary_interests)
    print_section("Secondary Interests", persona.interests.secondary_interests[:5])
    if persona.interests.interest_scores:
        print_section("Interest Scores (Top 10)",
                     dict(list(persona.interests.interest_scores.items())[:10]))

    # Skills
    print_header("SKILLS")
    if persona.skills.verified_skills:
        print_section("Verified Skills (from certificates)", persona.skills.verified_skills)
    if persona.skills.inferred_skills:
        print_section("Inferred Skills", persona.skills.inferred_skills[:10])
    if persona.skills.learning_skills:
        print_section("Currently Learning", persona.skills.learning_skills)

    # Learning
    print_header("LEARNING PROFILE")
    print(f"\n  Learning Style: {persona.learning.learning_style.value}")
    print(f"  Learning Frequency: {persona.learning.learning_frequency}")
    print(f"  Certificates Earned: {persona.learning.certificates_earned}")
    print(f"  Courses Completed: {persona.learning.courses_completed}")
    if persona.learning.preferred_platforms:
        print_section("Preferred Platforms", persona.learning.preferred_platforms)
    if persona.learning.topics_studied:
        print_section("Topics Studied", persona.learning.topics_studied[:10])

    # Lifestyle
    print_header("LIFESTYLE")
    print(f"\n  Activity Level: {persona.lifestyle.activity_level}")
    print(f"  Health Conscious: {'Yes' if persona.lifestyle.health_conscious else 'No'}")
    print(f"  Travel Frequency: {persona.lifestyle.travel_frequency}")
    if persona.lifestyle.hobbies:
        print_section("Hobbies", persona.lifestyle.hobbies)

    # Professional
    print_header("PROFESSIONAL PROFILE")
    print(f"\n  Career Stage: {persona.professional.career_stage}")
    print(f"  Job Search Active: {'Yes' if persona.professional.job_search_active else 'No'}")
    print(f"  Freelance Signals: {'Yes' if persona.professional.freelance_signals else 'No'}")
    print(f"  Leadership Signals: {'Yes' if persona.professional.leadership_signals else 'No'}")
    if persona.professional.professional_interests:
        print_section("Professional Interests", persona.professional.professional_interests)

    # Behavior
    print_header("BEHAVIOR PROFILE")
    print(f"\n  Engagement Level: {persona.behavior.engagement_level.value}")
    print(f"  Spending Tier: {persona.behavior.spending_tier.value}")
    print(f"  Tech Savviness: {persona.behavior.tech_savviness.value}")
    print(f"  Subscription Count: {persona.behavior.subscription_count}")
    if persona.behavior.preferred_shopping_categories:
        print_section("Shopping Categories", persona.behavior.preferred_shopping_categories)
    if persona.behavior.brand_preferences:
        print_section("Top Brands", persona.behavior.brand_preferences[:10])

    # Content
    print_header("CONTENT PREFERENCES")
    if persona.content.preferred_formats:
        print_section("Preferred Formats", persona.content.preferred_formats)
    if persona.content.topics_followed:
        print_section("Topics Followed", persona.content.topics_followed[:10])
    if persona.content.media_platforms:
        print_section("Media Platforms", persona.content.media_platforms)


def print_signal_summary(signals, signal_extractor):
    """Print summary of extracted signals"""
    print_header("SIGNAL SUMMARY")

    # By category
    by_category = signal_extractor.aggregate_by_category(signals)
    print("\nSignals by Category:")
    for category, cat_signals in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {category.value}: {len(cat_signals)}")

    # Top platforms
    top_platforms = signal_extractor.get_top_platforms(signals, limit=15)
    print("\nTop Platforms:")
    for platform, count in top_platforms:
        print(f"  {platform}: {count} emails")

    # Interest summary
    interests = signal_extractor.get_interest_summary(signals)
    if interests:
        print("\nTop Interests from Signals:")
        for interest, score in list(interests.items())[:10]:
            bar = "█" * int(score * 20)
            print(f"  {interest:20} {bar} {score:.2f}")


async def main():
    global auth_code, auth_error

    print_header("GMAIL PERSONA EXTRACTOR")
    print("\nThis tool will analyze your Gmail to build your persona.")
    print("Your data stays local - nothing is uploaded.\n")

    # Check environment
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Missing required environment variables!")
        print("\nPlease set:")
        print("  export GOOGLE_CLIENT_ID='your-client-id'")
        print("  export GOOGLE_CLIENT_SECRET='your-client-secret'")
        print("\nGet these from: https://console.cloud.google.com/apis/credentials")
        print("\nMake sure to:")
        print("  1. Enable Gmail API")
        print("  2. Add http://localhost:8888/callback to authorized redirect URIs")
        return

    # Initialize OAuth handler
    oauth_handler = GmailOAuthHandler(REDIRECT_URI)

    # Start callback server
    print("Starting OAuth callback server...")
    server = HTTPServer(('localhost', CALLBACK_PORT), OAuthCallbackHandler)
    server_thread = Thread(target=server.handle_request)
    server_thread.start()

    # Get authorization URL
    import secrets
    state = secrets.token_urlsafe(16)
    auth_url = oauth_handler.get_authorization_url(state)

    print(f"\nOpening browser for Gmail authorization...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")

    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authorization...")
    server_thread.join(timeout=120)

    if auth_error:
        print(f"\nAuthorization failed: {auth_error}")
        return

    if not auth_code:
        print("\nAuthorization timed out. Please try again.")
        return

    print("Authorization successful!")

    # Exchange code for tokens
    print("\nExchanging code for tokens...")
    try:
        tokens = await oauth_handler.exchange_code(auth_code)
    except Exception as e:
        print(f"Failed to exchange code: {e}")
        return

    # Initialize Gmail client
    print("Initializing Gmail client...")
    gmail_client = GmailClient(
        access_token=tokens['access_token'],
        refresh_token=tokens.get('refresh_token')
    )

    # Fetch emails - optimized for token usage
    max_emails = 500
    lookback_days = 30  # Last 30 days only
    subject_only = True  # Only fetch subject lines, not full body

    print(f"\nFetching up to {max_emails} emails from last {lookback_days} days...")
    print(f"Mode: {'Subject-only (optimized)' if subject_only else 'Full email'}\n")

    try:
        emails = await gmail_client.fetch_emails(
            max_emails=max_emails,
            lookback_days=lookback_days,
            subject_only=subject_only
        )
    except Exception as e:
        print(f"Failed to fetch emails: {e}")
        return

    if not emails:
        print("No relevant emails found.")
        return

    print(f"Fetched {len(emails)} emails")

    # Extract signals
    print("\nExtracting signals from all emails...")
    signal_extractor = SignalExtractor()
    signals = signal_extractor.extract_signals(emails)
    print(f"Extracted {len(signals)} signals")

    # Print signal summary
    print_signal_summary(signals, signal_extractor)

    # Build persona
    print("\n\nBuilding your persona...")
    persona_builder = PersonaBuilder()

    # Skip LLM classification in subject_only mode to save tokens
    llm_insights = None
    if not subject_only and os.getenv("GEMINI_API_KEY"):
        try:
            print("Running LLM classification (this may take a moment)...")
            llm_classifier = LLMClassifier()
            sample = emails[:50]
            classified = await llm_classifier.classify_email_batch(sample)
            llm_profile = await llm_classifier.infer_learning_profile(classified)
            llm_insights = {
                "interests": llm_profile.interests,
                "skill_levels": llm_profile.skill_levels,
                "learning_goals": llm_profile.learning_goals,
                "career_signals": llm_profile.career_signals,
                "confidence": llm_profile.confidence
            }
            print("LLM classification complete")
        except Exception as e:
            print(f"LLM classification skipped: {e}")
    elif subject_only:
        print("(LLM classification skipped in subject-only mode)")

    # Build persona
    persona = persona_builder.build_persona(
        user_id="test_user",
        signals=signals,
        llm_insights=llm_insights
    )

    # Print persona
    print_persona(persona)

    # Run education parsers only in full mode (needs body content)
    if not subject_only:
        print_header("EDUCATION DETAILS")

        learning_emails = gmail_client.filter_learning_platforms(emails)
        newsletter_emails = gmail_client.filter_newsletters(emails)

        course_parser = CourseParser()
        newsletter_parser = NewsletterParser()
        certificate_parser = CertificateParser()

        courses = course_parser.parse_emails(learning_emails)
        newsletters = newsletter_parser.parse_emails(newsletter_emails)
        certificates = certificate_parser.parse_emails(emails)

        if courses:
            print(f"\nCourses Detected ({len(courses)}):")
            for course in courses[:10]:
                status_emoji = {"completed": "✓", "in_progress": "→", "enrolled": "○"}.get(course.status, "?")
                print(f"  {status_emoji} [{course.platform}] {course.course_name}")
                print(f"      Topic: {course.topic} | Status: {course.status}")

        if certificates:
            print(f"\nCertificates ({len(certificates)}):")
            for cert in certificates[:10]:
                print(f"  ✓ [{cert.platform}] {cert.course_name}")
                if cert.skills_demonstrated:
                    print(f"      Skills: {', '.join(cert.skills_demonstrated[:5])}")

        if newsletters:
            print(f"\nNewsletters ({len(newsletters)}):")
            for nl in newsletters[:10]:
                print(f"  - {nl.name} ({nl.frequency}) - {nl.email_count} emails")
                print(f"      Topics: {', '.join(nl.topics[:3])}")
    else:
        print("\n(Detailed education parsing skipped in subject-only mode)")

    # Save to file
    output_file = "my_persona.json"
    print(f"\n\nSaving full persona to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(persona.to_dict(), f, indent=2, default=str)

    print(f"\nDone! Full persona saved to {output_file}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
