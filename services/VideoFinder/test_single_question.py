#!/usr/bin/env python3
"""
Video Finder Testing Script - Single Question
Tests complete video finding workflow for a single question
Includes detailed logging to file and console
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file in VideoFinder directory
video_finder_dir = Path(__file__).parent
dotenv_path = video_finder_dir / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Create logs directory if it doesn't exist
logs_dir = video_finder_dir / "logs"
logs_dir.mkdir(exist_ok=True)

# Setup detailed logging
log_file = logs_dir / f"video_finder_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 100)
logger.info("VIDEO FINDER TESTING SCRIPT - SINGLE QUESTION")
logger.info("=" * 100)

# Initialize MongoDB connection
mongo_uri = os.getenv('MONGODB_URI')
if not mongo_uri:
    raise ValueError(
        "MONGODB_URI not found in environment variables. "
        "Please create a .env file in the VideoFinder directory with MONGODB_URI."
    )

db_name = os.getenv('MONGODB_DB_NAME', 'ai_tutor')
mongo_client = MongoClient(mongo_uri)
db = mongo_client[db_name]

# Test connection
try:
    mongo_client.admin.command('ping')
    logger.info(f"[TEST] Connected to MongoDB database: {db_name}")
except Exception as e:
    logger.error(f"[TEST] MongoDB connection failed: {e}")
    raise

# Import after path setup
from find_videos import VideoFinder

def log_separator(title=""):
    """Print a separator line"""
    if title:
        logger.info(f"\n{'=' * 40} {title} {'=' * 40}\n")
    else:
        logger.info("=" * 100)

def test_apis():
    """Test if APIs are configured"""
    logger.info("\n[STEP 1] TESTING API CONFIGURATION")
    log_separator("API Configuration Check")

    # Check environment variables
    gemini_key = os.getenv('GEMINI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    youtube_key = os.getenv('YOUTUBE_API_KEY')

    logger.info(f"GEMINI_API_KEY set: {bool(gemini_key)}")
    if gemini_key:
        logger.info(f"  └─ Key starts with: {gemini_key[:20]}...")
    else:
        logger.warning("  └─ NOT SET!")

    logger.info(f"GOOGLE_API_KEY set: {bool(google_key)}")
    if google_key:
        logger.info(f"  └─ Key starts with: {google_key[:20]}...")

    logger.info(f"YOUTUBE_API_KEY set: {bool(youtube_key)}")
    if youtube_key:
        logger.info(f"  └─ Key starts with: {youtube_key[:20]}...")
    else:
        logger.warning("  └─ NOT SET! (Required for YouTube search)")

    logger.info(f"\nMONGODB_URI set: {bool(os.getenv('MONGODB_URI'))}")

    return bool(youtube_key)

def initialize_apis():
    """Initialize VideoFinder"""
    logger.info("\n[STEP 2] INITIALIZING VIDEO FINDER")
    log_separator("VideoFinder Initialization")

    try:
        finder = VideoFinder()
        logger.info("✅ VideoFinder initialized successfully")
        return finder
    except Exception as e:
        logger.error(f"❌ Failed to initialize VideoFinder: {e}")
        logger.error("Make sure YOUTUBE_API_KEY is set in .env file")
        return None

def get_test_question():
    """Get a test question from MongoDB"""
    logger.info("\n[STEP 3] FETCHING TEST QUESTION FROM MONGODB")
    log_separator("Test Question Selection")

    try:
        # Try to get a question with existing learning_videos first to avoid duplicates
        question = db['scraped_questions'].find_one({
            "questionId": {"$exists": True},
            "learning_videos": {"$size": 0}  # No approved videos yet
        })

        if not question:
            # If not found, get any question
            question = db['scraped_questions'].find_one({
                "questionId": {"$exists": True}
            })

        if not question:
            logger.error("❌ No questions found in MongoDB")
            return None

        question_id = question.get("questionId")
        logger.info(f"✅ Found test question")
        logger.info(f"   Question ID: {question_id}")

        # Check existing videos
        suggested_count = len(question.get("suggested_videos", []))
        learning_count = len(question.get("learning_videos", []))
        logger.info(f"   Existing suggested videos: {suggested_count}")
        logger.info(f"   Existing learning videos: {learning_count}")

        return question

    except Exception as e:
        logger.error(f"❌ Error fetching question: {e}")
        return None

def extract_question_text(question):
    """Extract and clean question text"""
    logger.info("\n[STEP 4] EXTRACTING QUESTION TEXT")
    log_separator("Question Text Extraction")

    try:
        question_id = question.get("questionId")
        assessment_data = question.get("assessmentData", {})

        # Navigate to itemData
        item_data_str = assessment_data.get("data", {}).get("assessmentItem", {}).get("item", {}).get("itemData", "")

        if not item_data_str:
            logger.error("❌ No itemData found in question")
            logger.debug(f"   Question structure: {json.dumps(question.keys())}")
            return None

        logger.info("✅ Found itemData")

        # Parse JSON
        try:
            item_data = json.loads(item_data_str)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse itemData JSON: {e}")
            return None

        # Extract question content
        question_obj = item_data.get("question", {})
        question_text = question_obj.get("content", "")

        if not question_text:
            logger.error("❌ No content found in question object")
            logger.debug(f"   Question object keys: {json.dumps(list(question_obj.keys()))}")
            return None

        logger.info(f"📝 Raw question text: {question_text[:100]}...")

        # Clean up Perseus formatting - comprehensive cleaning
        import re
        cleaned_text = question_text

        # 1. Remove Perseus widget markers: [[☃...]]
        cleaned_text = re.sub(r'\[\[☃[^\]]+\]\]', '', cleaned_text)

        # 2. Remove LaTeX expressions with single/double dollar signs: $...$ or $$...$$
        cleaned_text = re.sub(r'\$+[^\$]*\$+', '', cleaned_text)

        # 3. Remove LaTeX commands with backslashes: \command, \Large, etc
        cleaned_text = re.sub(r'\\[a-zA-Z]+', '', cleaned_text)

        # 4. Remove curly braces with content: {...}
        cleaned_text = re.sub(r'\{[^\}]*\}', '', cleaned_text)

        # 5. Remove markdown image syntax: ![...](...)
        cleaned_text = re.sub(r'!\[([^\]]*)\]\(([^\)]*)\)', '', cleaned_text)

        # 6. Remove image URIs with web+graphie or similar patterns
        cleaned_text = re.sub(r'web\+graphie://[^\s)]+', '', cleaned_text)

        # 7. Remove asterisks used for emphasis: *text* or **text**
        cleaned_text = re.sub(r'\*+', '', cleaned_text)

        # 8. Remove excessive whitespace (multiple spaces, tabs, newlines)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        # 9. Clean up trailing dots and commas after stripping
        cleaned_text = cleaned_text.strip()
        cleaned_text = re.sub(r'^[\.\,\s]+', '', cleaned_text)  # Remove leading dots/commas/spaces
        cleaned_text = re.sub(r'[\.\,\s]+$', '', cleaned_text)  # Remove trailing dots/commas/spaces
        cleaned_text = cleaned_text.strip()

        logger.info(f"✅ Cleaned question text: {cleaned_text[:100]}...")
        logger.info(f"   Cleaned length: {len(cleaned_text)} characters")

        return cleaned_text

    except Exception as e:
        logger.error(f"❌ Error extracting question text: {e}")
        import traceback
        logger.debug(f"   Traceback: {traceback.format_exc()}")
        return None

def search_videos(finder, question_text, question_id):
    """Search for videos using Gemini + YouTube"""
    logger.info("\n[STEP 5] SEARCHING FOR VIDEOS")
    log_separator("Video Search (Gemini + YouTube)")

    try:
        logger.info(f"Query: {question_text}")
        logger.info("Searching YouTube for videos (4-20 minutes)...")

        videos = finder.search_youtube(question_text, max_results=5)

        if not videos:
            logger.warning("⚠️  No videos found")
            return []

        logger.info(f"✅ Found {len(videos)} videos")

        for i, video in enumerate(videos, 1):
            logger.info(f"\n   Video {i}:")
            logger.info(f"   ├─ Title: {video.get('title', 'N/A')}")
            logger.info(f"   ├─ Channel: {video.get('channel_title', 'N/A')}")
            logger.info(f"   ├─ Video ID: {video.get('video_id', 'N/A')}")
            logger.info(f"   └─ Description: {video.get('description', 'N/A')[:80]}...")

        return videos

    except Exception as e:
        logger.error(f"❌ Error searching videos: {e}")
        import traceback
        logger.debug(f"   Traceback: {traceback.format_exc()}")
        return []

def analyze_and_store_videos(finder, question, videos):
    """Analyze videos and store in database"""
    logger.info("\n[STEP 6] ANALYZING AND STORING VIDEOS")
    log_separator("Video Analysis & Storage")

    question_id = question.get("questionId")
    stored_count = 0

    try:
        # Check for duplicates
        existing_video_ids = set()
        suggested = question.get("suggested_videos", [])
        learning = question.get("learning_videos", [])

        for video in suggested + learning:
            existing_video_ids.add(video.get("video_id", ""))

        if existing_video_ids:
            logger.info(f"Existing video IDs: {existing_video_ids}")

        for i, video in enumerate(videos, 1):
            video_id = video.get('video_id')

            logger.info(f"\n   Processing Video {i}/{len(videos)}")
            logger.info(f"   Video ID: {video_id}")

            # Check for duplicates
            if video_id in existing_video_ids:
                logger.warning(f"   ⚠️  DUPLICATE - Skipping this video")
                continue

            # Detect language
            try:
                from langdetect import detect
                title = video.get('title', '')
                description = video.get('description', '')
                language = detect(title) if title else 'en'
                logger.info(f"   Language detected: {language}")
            except Exception as e:
                logger.warning(f"   ⚠️  Language detection failed: {e}, defaulting to 'en'")
                language = 'en'

            # Create video object
            pending_video = {
                "video_id": video_id,
                "title": video.get('title'),
                "channel": video.get('channel_title', ''),
                "language": language,
                "score": 0,
                "views": 0,
                "helpful_count": 0,
                "suggested_at": datetime.now()
            }

            # Store in MongoDB
            try:
                result = db['scraped_questions'].update_one(
                    {"questionId": question_id},
                    {"$push": {"suggested_videos": pending_video}},
                    upsert=True
                )
                logger.info(f"   ✅ Stored in MongoDB")
                logger.info(f"      Matched: {result.matched_count}, Modified: {result.modified_count}")
                stored_count += 1
                existing_video_ids.add(video_id)

            except Exception as e:
                logger.error(f"   ❌ Failed to store in MongoDB: {e}")
                continue

        logger.info(f"\n✅ Stored {stored_count}/{len(videos)} videos successfully")
        return stored_count

    except Exception as e:
        logger.error(f"❌ Error in analysis and storage: {e}")
        import traceback
        logger.debug(f"   Traceback: {traceback.format_exc()}")
        return 0

def verify_database_storage(question_id):
    """Verify videos were stored correctly in database"""
    logger.info("\n[STEP 7] VERIFYING DATABASE STORAGE")
    log_separator("Database Verification")

    try:
        # Fetch the question from database
        question_from_db = db['scraped_questions'].find_one({"questionId": question_id})

        if not question_from_db:
            logger.error("❌ Question not found in database after storage")
            return False

        suggested = question_from_db.get("suggested_videos", [])
        learning = question_from_db.get("learning_videos", [])

        logger.info(f"✅ Question found in database")
        logger.info(f"   Total suggested videos: {len(suggested)}")
        logger.info(f"   Total learning videos: {len(learning)}")

        if suggested:
            logger.info(f"\n   Suggested Videos (pending approval):")
            for i, video in enumerate(suggested[-5:], 1):  # Show last 5
                logger.info(f"   {i}. {video.get('title', 'N/A')}")
                logger.info(f"      └─ Video ID: {video.get('video_id')}")
                logger.info(f"      └─ Language: {video.get('language')}")
                logger.info(f"      └─ Added: {video.get('suggested_at')}")

        return True

    except Exception as e:
        logger.error(f"❌ Error verifying database: {e}")
        import traceback
        logger.debug(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main test function"""
    logger.info(f"\nTest started at: {datetime.now()}")

    # Step 1: Check APIs
    if not test_apis():
        logger.error("\n❌ YouTube API key not configured. Cannot proceed.")
        logger.info("Please set YOUTUBE_API_KEY in your .env file")
        return False

    # Step 2: Initialize APIs
    finder = initialize_apis()
    if not finder:
        return False

    # Step 3: Get test question
    question = get_test_question()
    if not question:
        return False

    question_id = question.get("questionId")

    # Step 4: Extract question text
    question_text = extract_question_text(question)
    if not question_text:
        return False

    # Step 5: Search for videos
    videos = search_videos(finder, question_text, question_id)
    if not videos:
        logger.warning("⚠️  No videos found, but test will continue")

    # Step 6: Analyze and store videos
    if videos:
        stored_count = analyze_and_store_videos(finder, question, videos)
    else:
        stored_count = 0

    # Step 7: Verify database storage
    success = verify_database_storage(question_id)

    # Final summary
    log_separator("TEST SUMMARY")
    logger.info(f"Test completed at: {datetime.now()}")
    logger.info(f"Videos found: {len(videos)}")
    logger.info(f"Videos stored: {stored_count}")
    logger.info(f"Database verification: {'✅ PASSED' if success else '❌ FAILED'}")
    logger.info(f"\n📝 Detailed log saved to: {log_file}")

    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
