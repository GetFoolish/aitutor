"""
InsightExtractor Service - Gmail-based personalization for cold start problem

This service extracts learning insights from user's Gmail (with consent) to
personalize the AI tutor experience from the first session.
"""
import os
import sys
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.logging_config import get_logger
from shared.auth_middleware import get_current_user
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware

from services.InsightExtractor.gmail_client import GmailClient, GmailOAuthHandler
from services.InsightExtractor.parsers.course_parser import CourseParser
from services.InsightExtractor.parsers.newsletter_parser import NewsletterParser
from services.InsightExtractor.parsers.certificate_parser import CertificateParser
from services.InsightExtractor.extractors.llm_classifier import LLMClassifier
from services.InsightExtractor.extractors.profile_builder import ProfileBuilder
from services.InsightExtractor.extractors.signal_extractor import SignalExtractor
from services.InsightExtractor.extractors.persona_builder import PersonaBuilder, UserPersona
from services.InsightExtractor.models.schemas import (
    ColdStartProfile,
    InsightExtractionRequest,
    InsightExtractionResponse,
    GmailConsentRequest,
    GmailConsentResponse,
    UserInsightDocument
)

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="InsightExtractor Service",
    description="Gmail-based personalization for AI tutor cold start",
    version="1.0.0"
)

# Add middleware
app.add_middleware(UnpluggedTimingMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Service configuration
BASE_URL = os.getenv("INSIGHT_SERVICE_URL", "http://localhost:8004")
GMAIL_REDIRECT_URI = f"{BASE_URL}/insights/gmail/callback"

# Initialize components
gmail_oauth = GmailOAuthHandler(GMAIL_REDIRECT_URI)

# Legacy parsers (still used for detailed extraction)
course_parser = CourseParser()
newsletter_parser = NewsletterParser()
certificate_parser = CertificateParser()
profile_builder = ProfileBuilder()

# New comprehensive extractors
signal_extractor = SignalExtractor()
persona_builder = PersonaBuilder()

# In-memory state storage (use Redis in production)
_oauth_states = {}


# Request/Response Models
class InitiateGmailConsentRequest(BaseModel):
    """Request to initiate Gmail OAuth consent"""
    pass  # user_id comes from JWT


class GmailCallbackRequest(BaseModel):
    """OAuth callback parameters"""
    code: str
    state: str


class ExtractInsightsRequest(BaseModel):
    """Request to extract insights from stored Gmail tokens"""
    max_emails: int = 500
    lookback_months: int = 6
    use_llm: bool = True


class ProfileResponse(BaseModel):
    """Response with user's cold start profile"""
    has_profile: bool
    profile: Optional[ColdStartProfile] = None
    last_updated: Optional[datetime] = None


class ApplyProfileRequest(BaseModel):
    """Request to apply profile to DASH"""
    pass  # user_id comes from JWT


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "InsightExtractor",
        "timestamp": datetime.utcnow().isoformat()
    }


# Gmail OAuth endpoints
@app.post("/insights/gmail/initiate", response_model=GmailConsentResponse)
async def initiate_gmail_consent(request: Request):
    """
    Initiate Gmail OAuth consent flow.

    Returns authorization URL for user to grant Gmail access.
    """
    user_id = get_current_user(request)

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": user_id,
        "created_at": time.time()
    }

    # Clean up old states (older than 10 minutes)
    current_time = time.time()
    expired_states = [
        s for s, data in _oauth_states.items()
        if current_time - data["created_at"] > 600
    ]
    for s in expired_states:
        del _oauth_states[s]

    authorization_url = gmail_oauth.get_authorization_url(state)

    logger.info(f"[GMAIL_CONSENT] Initiated consent for user {user_id}")

    return GmailConsentResponse(
        authorization_url=authorization_url,
        state=state
    )


@app.get("/insights/gmail/callback")
async def gmail_callback(code: str, state: str):
    """
    Handle Gmail OAuth callback.

    Exchanges authorization code for tokens and stores them.
    """
    # Verify state
    if state not in _oauth_states:
        logger.error(f"[GMAIL_CALLBACK] Invalid or expired state")
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    state_data = _oauth_states.pop(state)
    user_id = state_data["user_id"]

    try:
        # Exchange code for tokens
        tokens = await gmail_oauth.exchange_code(code)

        # Store tokens in MongoDB
        from managers.mongodb_manager import mongo_db

        token_expiry = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])

        mongo_db.user_insights.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "gmail_connected": True,
                    "gmail_access_token": tokens["access_token"],
                    "gmail_refresh_token": tokens.get("refresh_token"),
                    "token_expiry": token_expiry,
                    "consent_timestamp": datetime.utcnow(),
                    "consent_version": "1.0"
                }
            },
            upsert=True
        )

        logger.info(f"[GMAIL_CALLBACK] Stored tokens for user {user_id}")

        # Redirect to frontend success page
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return {
            "success": True,
            "message": "Gmail connected successfully",
            "redirect_url": f"{frontend_url}/app/settings?gmail_connected=true"
        }

    except Exception as e:
        logger.error(f"[GMAIL_CALLBACK] Error exchanging code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect Gmail: {str(e)}")


@app.post("/insights/extract", response_model=InsightExtractionResponse)
async def extract_insights(
    request: Request,
    extract_request: ExtractInsightsRequest,
    background_tasks: BackgroundTasks
):
    """
    Extract learning insights from user's Gmail.

    Requires Gmail to be connected first via /insights/gmail/initiate.
    """
    user_id = get_current_user(request)
    start_time = time.time()

    logger.info(f"[EXTRACT] Starting extraction for user {user_id}")

    # Get stored tokens
    from managers.mongodb_manager import mongo_db

    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc or not insight_doc.get("gmail_connected"):
        raise HTTPException(
            status_code=400,
            detail="Gmail not connected. Please connect Gmail first."
        )

    access_token = insight_doc.get("gmail_access_token")
    refresh_token = insight_doc.get("gmail_refresh_token")
    token_expiry = insight_doc.get("token_expiry")

    if not access_token:
        raise HTTPException(status_code=400, detail="Gmail tokens not found")

    try:
        # Initialize Gmail client
        gmail_client = GmailClient(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )

        # Fetch emails
        logger.info(f"[EXTRACT] Fetching up to {extract_request.max_emails} emails")
        emails = await gmail_client.fetch_emails(
            max_emails=extract_request.max_emails,
            lookback_months=extract_request.lookback_months
        )

        logger.info(f"[EXTRACT] Fetched {len(emails)} emails")

        if not emails:
            return InsightExtractionResponse(
                success=True,
                user_id=user_id,
                profile=None,
                error="No learning-related emails found",
                processing_time_seconds=time.time() - start_time
            )

        # ============ COMPREHENSIVE SIGNAL EXTRACTION ============
        # Extract signals from ALL emails (shopping, subscriptions, travel, etc.)
        logger.info("[EXTRACT] Running comprehensive signal extraction")
        all_signals = signal_extractor.extract_signals(emails)
        logger.info(f"[EXTRACT] Extracted {len(all_signals)} signals from all email categories")

        # Get signal summary
        signals_by_category = signal_extractor.aggregate_by_category(all_signals)
        top_platforms = signal_extractor.get_top_platforms(all_signals, limit=15)
        interest_summary = signal_extractor.get_interest_summary(all_signals)

        logger.info(f"[EXTRACT] Signal categories found: {list(signals_by_category.keys())}")
        logger.info(f"[EXTRACT] Top platforms: {[p[0] for p in top_platforms[:5]]}")

        # ============ LEGACY PARSERS (for detailed education data) ============
        logger.info("[EXTRACT] Running specialized education parsers")
        learning_platform_emails = gmail_client.filter_learning_platforms(emails)
        newsletter_emails = gmail_client.filter_newsletters(emails)

        parsed_courses = course_parser.parse_emails(learning_platform_emails)
        parsed_newsletters = newsletter_parser.parse_emails(newsletter_emails)
        parsed_certificates = certificate_parser.parse_emails(emails)

        logger.info(f"[EXTRACT] Education signals: {len(parsed_courses)} courses, "
                   f"{len(parsed_newsletters)} newsletters, {len(parsed_certificates)} certificates")

        # ============ LLM CLASSIFICATION (optional) ============
        llm_profile = None
        llm_insights = None
        classified_emails = None

        if extract_request.use_llm and emails:
            try:
                logger.info("[EXTRACT] Running LLM classification")
                llm_classifier = LLMClassifier()

                # Classify a sample of emails
                sample_size = min(100, len(emails))
                email_sample = emails[:sample_size]

                classified_emails = await llm_classifier.classify_email_batch(email_sample)
                llm_profile = await llm_classifier.infer_learning_profile(classified_emails)

                # Convert to dict for persona builder
                if llm_profile:
                    llm_insights = {
                        "interests": llm_profile.interests,
                        "skill_levels": llm_profile.skill_levels,
                        "learning_goals": llm_profile.learning_goals,
                        "career_signals": llm_profile.career_signals,
                        "confidence": llm_profile.confidence
                    }

                logger.info(f"[EXTRACT] LLM classified {len(classified_emails)} emails")
            except Exception as e:
                logger.warning(f"[EXTRACT] LLM classification failed (continuing without): {e}")

        # ============ BUILD COMPREHENSIVE PERSONA ============
        logger.info("[EXTRACT] Building comprehensive user persona")
        user_persona = persona_builder.build_persona(
            user_id=user_id,
            signals=all_signals,
            llm_insights=llm_insights
        )

        logger.info(f"[EXTRACT] Persona built: {len(user_persona.interests.primary_interests)} primary interests, "
                   f"{len(user_persona.persona_tags)} tags, confidence={user_persona.confidence_score:.2f}")

        # ============ BUILD LEGACY PROFILE (for backward compatibility) ============
        logger.info("[EXTRACT] Building cold start profile (legacy format)")
        profile = profile_builder.build_profile(
            user_id=user_id,
            parsed_courses=parsed_courses,
            parsed_newsletters=parsed_newsletters,
            parsed_certificates=parsed_certificates,
            llm_profile=llm_profile,
            classified_emails=classified_emails,
            total_emails_scanned=len(emails)
        )

        # ============ STORE IN MONGODB ============
        mongo_db.user_insights.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    # Legacy profile (for backward compatibility)
                    "processed_profile": profile.model_dump(),

                    # New comprehensive persona
                    "user_persona": user_persona.to_dict(),

                    # Comprehensive signal data
                    "all_signals": {
                        "total_count": len(all_signals),
                        "by_category": {k.value: len(v) for k, v in signals_by_category.items()},
                        "top_platforms": [{"platform": p[0], "count": p[1]} for p in top_platforms],
                        "interest_scores": interest_summary,
                    },

                    # Legacy education signals
                    "education_signals": {
                        "courses_detected": [c.model_dump() for c in profile.active_courses],
                        "newsletters": [n.model_dump() for n in profile.newsletters],
                        "certificates": [c.model_dump() for c in profile.certificates]
                    },

                    # Metadata
                    "last_scan": datetime.utcnow(),
                    "persona_tags": user_persona.persona_tags,
                    "confidence_score": user_persona.confidence_score,
                },
                "$inc": {"scan_count": 1}
            }
        )

        processing_time = time.time() - start_time
        logger.info(f"[EXTRACT] Completed in {processing_time:.2f}s")

        return InsightExtractionResponse(
            success=True,
            user_id=user_id,
            profile=profile,
            processing_time_seconds=processing_time
        )

    except Exception as e:
        logger.error(f"[EXTRACT] Error extracting insights: {e}")
        import traceback
        logger.error(f"[EXTRACT] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.get("/insights/profile", response_model=ProfileResponse)
async def get_profile(request: Request):
    """
    Get user's cold start profile if available (legacy format).
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc or not insight_doc.get("processed_profile"):
        return ProfileResponse(has_profile=False)

    profile_data = insight_doc["processed_profile"]

    # Convert stored dict back to Pydantic model
    profile = ColdStartProfile(**profile_data)

    return ProfileResponse(
        has_profile=True,
        profile=profile,
        last_updated=insight_doc.get("last_scan")
    )


@app.get("/insights/persona")
async def get_persona(request: Request):
    """
    Get user's comprehensive persona with all extracted signals.

    Returns a complete user profile including:
    - Interests & passions
    - Skills & expertise
    - Learning preferences
    - Lifestyle & behavior patterns
    - Professional signals
    - Content preferences
    - Persona tags for quick categorization
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc:
        return {
            "has_persona": False,
            "message": "No data extracted yet. Connect Gmail and run extraction first."
        }

    if not insight_doc.get("user_persona"):
        return {
            "has_persona": False,
            "message": "Legacy profile exists but comprehensive persona not available. Re-run extraction."
        }

    return {
        "has_persona": True,
        "persona": insight_doc["user_persona"],
        "signal_summary": insight_doc.get("all_signals", {}),
        "persona_tags": insight_doc.get("persona_tags", []),
        "confidence_score": insight_doc.get("confidence_score", 0),
        "last_updated": insight_doc.get("last_scan")
    }


@app.get("/insights/signals")
async def get_signals(request: Request):
    """
    Get raw signal data extracted from user's emails.

    Returns aggregated signals by category, top platforms, and interest scores.
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc or not insight_doc.get("all_signals"):
        return {
            "has_signals": False,
            "message": "No signals extracted yet."
        }

    return {
        "has_signals": True,
        "signals": insight_doc["all_signals"],
        "education_signals": insight_doc.get("education_signals", {}),
        "last_updated": insight_doc.get("last_scan")
    }


@app.post("/insights/apply-to-dash")
async def apply_profile_to_dash(request: Request):
    """
    Apply cold start profile to DASH system.

    Updates user's skill states based on inferred interests and level.
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db
    from services.DashSystem.dash_system import DASHSystem

    # Get profile
    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc or not insight_doc.get("processed_profile"):
        raise HTTPException(status_code=404, detail="No profile found. Extract insights first.")

    profile_data = insight_doc["processed_profile"]
    profile = ColdStartProfile(**profile_data)

    # Get DASH skills
    dash_system = DASHSystem()
    dash_skills = dash_system.skills

    # Map profile to skill adjustments
    skill_adjustments = profile_builder.map_to_dash_skills(profile, dash_skills)

    if not skill_adjustments:
        return {
            "success": True,
            "message": "Profile does not map to current DASH skills",
            "skills_adjusted": 0
        }

    # Apply adjustments to user's skill states
    user_data = mongo_db.users.find_one({"user_id": user_id})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found in DASH system")

    skill_states = user_data.get("skill_states", {})
    adjusted_count = 0

    for skill_id, adjustment in skill_adjustments.items():
        if skill_id in skill_states:
            # Apply adjustment to memory strength
            current_strength = skill_states[skill_id].get("memory_strength", 0)
            new_strength = current_strength + adjustment

            # Clamp to reasonable range
            new_strength = max(-3, min(3, new_strength))

            skill_states[skill_id]["memory_strength"] = new_strength
            skill_states[skill_id]["cold_start_adjusted"] = True
            adjusted_count += 1

    # Save updated skill states
    mongo_db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "skill_states": skill_states,
                "cold_start_applied": True,
                "cold_start_timestamp": datetime.utcnow()
            }
        }
    )

    logger.info(f"[APPLY_DASH] Applied profile adjustments to {adjusted_count} skills for user {user_id}")

    return {
        "success": True,
        "message": f"Applied cold start profile to {adjusted_count} skills",
        "skills_adjusted": adjusted_count,
        "inferred_level": profile.inferred_level.value,
        "top_interests": profile.interests[:5]
    }


@app.get("/insights/status")
async def get_insight_status(request: Request):
    """
    Get status of Gmail connection and insight extraction.
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    insight_doc = mongo_db.user_insights.find_one({"user_id": user_id})

    if not insight_doc:
        return {
            "gmail_connected": False,
            "has_profile": False,
            "last_scan": None,
            "scan_count": 0
        }

    return {
        "gmail_connected": insight_doc.get("gmail_connected", False),
        "has_profile": insight_doc.get("processed_profile") is not None,
        "last_scan": insight_doc.get("last_scan"),
        "scan_count": insight_doc.get("scan_count", 0),
        "consent_timestamp": insight_doc.get("consent_timestamp")
    }


@app.delete("/insights/disconnect")
async def disconnect_gmail(request: Request):
    """
    Disconnect Gmail and delete all extracted data.
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    result = mongo_db.user_insights.delete_one({"user_id": user_id})

    if result.deleted_count == 0:
        return {"success": True, "message": "No Gmail connection found"}

    logger.info(f"[DISCONNECT] Removed Gmail data for user {user_id}")

    return {
        "success": True,
        "message": "Gmail disconnected and all extracted data deleted"
    }


@app.delete("/insights/profile")
async def delete_profile(request: Request):
    """
    Delete only the extracted profile, keeping Gmail connected.
    """
    user_id = get_current_user(request)

    from managers.mongodb_manager import mongo_db

    mongo_db.user_insights.update_one(
        {"user_id": user_id},
        {
            "$unset": {
                "processed_profile": "",
                "raw_signals": ""
            },
            "$set": {
                "last_scan": None
            }
        }
    )

    logger.info(f"[DELETE_PROFILE] Deleted profile for user {user_id}")

    return {
        "success": True,
        "message": "Profile deleted. Gmail remains connected."
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("INSIGHT_PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
