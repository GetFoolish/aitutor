#!/usr/bin/env python3
"""
MongoDB Integration for Video Finder
Runs continuously on Raspberry Pi to find and suggest videos for questions.
Finds videos for questions with < 6 learning videos.
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(asctime)s|%(message)s|file:%(filename)s:line %(lineno)d',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from managers.mongodb_manager import mongo_db
from services.VideoFinder.find_videos import VideoFinder

# For language detection
try:
    from langdetect import detect, LangDetectException
except ImportError:
    logger.warning("langdetect not installed, defaulting language to 'en'")
    def detect(text):
        return 'en'


class MongoDBVideoFinder:
    """Integration layer between VideoFinder and MongoDB"""

    def __init__(self):
        """Initialize the MongoDB video finder"""
        logger.info("[VIDEO_FINDER] Initializing MongoDBVideoFinder")
        self.finder = VideoFinder()
        self.batch_size = 5
        self.sleep_interval = 300  # 5 minutes between batches
        self.error_retry_interval = 60  # 1 minute on error
        logger.info("[VIDEO_FINDER] MongoDBVideoFinder initialized successfully")

    def get_questions_without_enough_videos(self, min_videos: int = 6) -> List[Dict[str, Any]]:
        """
        Get questions with fewer than min_videos learning videos.
        CRITICAL: Filter out questions that already have enough videos.
        """
        try:
            logger.info(f"[VIDEO_FINDER] Querying questions with < {min_videos} learning videos")

            # Query for questions with < min_videos learning videos
            # Using $size operator to count array elements
            questions = list(mongo_db.scraped_questions.find({
                "$expr": {
                    "$lt": [
                        {"$size": {"$ifNull": ["$learning_videos", []]}},
                        min_videos
                    ]
                }
            }).limit(self.batch_size))

            logger.info(f"[VIDEO_FINDER] Found {len(questions)} questions needing videos")
            return questions

        except Exception as e:
            logger.error(f"[VIDEO_FINDER] Error querying questions: {e}")
            return []

    def detect_video_language(self, video_id: str, title: str = "", description: str = "") -> str:
        """
        Detect video language from title and description.
        Returns language code (e.g., 'en', 'es', 'fr')
        Defaults to 'en' if detection fails.
        """
        try:
            # Try to detect from title first (usually more reliable)
            if title and len(title) > 10:
                language = detect(title)
                logger.info(f"[VIDEO_FINDER] Detected language for video {video_id}: {language}")
                return language

            # Fallback to description
            if description and len(description) > 10:
                language = detect(description)
                logger.info(f"[VIDEO_FINDER] Detected language from description: {language}")
                return language

            # Default
            logger.warning(f"[VIDEO_FINDER] Could not detect language for video {video_id}, defaulting to 'en'")
            return 'en'

        except Exception as e:
            logger.warning(f"[VIDEO_FINDER] Language detection error for {video_id}: {e}, defaulting to 'en'")
            return 'en'

    def add_videos_for_approval(self, question_id: str, videos: List[Dict[str, Any]]) -> int:
        """
        Add videos to suggested_videos collection for approval.
        Initializes tracking fields: score=0, views=0, helpful_count=0
        Prevents duplicate videos in suggested_videos or learning_videos.
        """
        try:
            if not videos:
                logger.info(f"[VIDEO_FINDER] No videos to add for question {question_id}")
                return 0

            # Get existing question to check for duplicates
            question_doc = mongo_db.scraped_questions.find_one({"questionId": question_id})

            existing_video_ids = set()
            if question_doc:
                # Get video IDs from both suggested and learning videos
                suggested = question_doc.get("suggested_videos", [])
                learning = question_doc.get("learning_videos", [])

                for video in suggested + learning:
                    existing_video_ids.add(video.get("video_id", ""))

            added_count = 0
            for video in videos:
                try:
                    video_id = video.get('id', '')

                    # Skip if video already exists (deduplication)
                    if video_id in existing_video_ids:
                        logger.info(f"[VIDEO_FINDER] Skipping duplicate video {video_id} for {question_id}")
                        continue

                    # Detect language
                    language = self.detect_video_language(
                        video_id,
                        video.get('title', ''),
                        video.get('description', '')
                    )

                    # Create pending video object with initialized tracking fields
                    pending_video = {
                        "video_id": video_id,
                        "title": video.get('title'),
                        "channel": video.get('channel_title', ''),
                        "language": language,
                        "score": 0,  # Initialize tracking fields
                        "views": 0,
                        "helpful_count": 0,
                        "suggested_at": datetime.now()
                    }

                    # Add to suggested_videos collection
                    mongo_db.scraped_questions.update_one(
                        {"questionId": question_id},
                        {"$push": {"suggested_videos": pending_video}},
                        upsert=True
                    )

                    added_count += 1
                    existing_video_ids.add(video_id)  # Add to set to prevent duplicates in this batch
                    logger.info(f"[VIDEO_FINDER] Added video {video_id} ({language}) to {question_id}")

                except Exception as e:
                    logger.error(f"[VIDEO_FINDER] Error adding video for {question_id}: {e}")
                    continue

            return added_count

        except Exception as e:
            logger.error(f"[VIDEO_FINDER] Error in add_videos_for_approval: {e}")
            return 0

    def process_questions(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process questions and find videos for them.
        Returns summary of processing results.
        """
        results = {
            "total_processed": len(questions),
            "videos_found": 0,
            "videos_added": 0,
            "errors": []
        }

        for question in questions:
            try:
                question_id = question.get('questionId')
                if not question_id:
                    logger.warning("[VIDEO_FINDER] Question without questionId")
                    continue

                # Extract question text for search
                assessment_data = question.get('assessmentData', {})
                
                # Navigate to itemData: assessmentData.data.assessmentItem.item.itemData
                question_text = ''
                try:
                    item_data_str = assessment_data.get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
                    if not item_data_str:
                        logger.warning(f"[VIDEO_FINDER] Question {question_id} has no itemData")
                        continue
                    
                    # Parse JSON string to get Perseus object
                    import json
                    item_data = json.loads(item_data_str)
                    
                    # Extract question content from Perseus format
                    question_obj = item_data.get('question', {})
                    question_text = question_obj.get('content', '')
                    
                    # Clean up Perseus widgets and markdown
                    import re
                    if question_text:
                        # Remove Perseus widget markers like [[☃ radio 3]]
                        question_text = re.sub(r'\[\[☃[^\]]+\]\]', '', question_text)
                        # Remove markdown bold markers
                        question_text = re.sub(r'\*\*', '', question_text)
                        # Remove LaTeX math expressions
                        question_text = re.sub(r'\$\\\\[^$]+\$', '', question_text)
                        question_text = question_text.strip()
                    
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    logger.warning(f"[VIDEO_FINDER] Error parsing itemData for {question_id}: {e}")
                    continue

                if not question_text or len(question_text) < 10:
                    logger.warning(f"[VIDEO_FINDER] Question {question_id} has empty content")
                    continue

                logger.info(f"[VIDEO_FINDER] Processing question {question_id}: '{question_text[:50]}...'")

                # Search for videos
                try:
                    videos = self.finder.search_youtube(question_text, max_results=5)
                except Exception as search_error:
                    logger.error(f"[VIDEO_FINDER] Error searching videos for {question_id}: {search_error}")
                    results["errors"].append(str(search_error))
                    continue

                if not videos:
                    logger.info(f"[VIDEO_FINDER] No videos found for {question_id}")
                    continue

                logger.info(f"[VIDEO_FINDER] Found {len(videos)} videos for {question_id}")
                results["videos_found"] += len(videos)

                # Add videos for approval
                added = self.add_videos_for_approval(question_id, videos)
                results["videos_added"] += added

                logger.info(f"[VIDEO_FINDER] Added {added} videos for approval on {question_id}")

            except Exception as e:
                logger.error(f"[VIDEO_FINDER] Error processing question: {e}")
                results["errors"].append(str(e))
                continue

        return results

    def run_continuously(self):
        """
        Run the video finder continuously.
        Processes batches of questions needing videos every sleep_interval seconds.
        Runs on Raspberry Pi.
        """
        logger.info("[VIDEO_FINDER] Starting continuous video finder")
        logger.info(f"[VIDEO_FINDER] Batch size: {self.batch_size}")
        logger.info(f"[VIDEO_FINDER] Sleep interval: {self.sleep_interval}s")

        iteration = 0

        while True:
            try:
                iteration += 1
                logger.info(f"\n[VIDEO_FINDER] === Iteration {iteration} ===")
                logger.info(f"[VIDEO_FINDER] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Get questions that need videos
                questions = self.get_questions_without_enough_videos(min_videos=6)

                if not questions:
                    logger.info("[VIDEO_FINDER] No questions need videos, sleeping...")
                    time.sleep(self.sleep_interval)
                    continue

                logger.info(f"[VIDEO_FINDER] Processing {len(questions)} questions")

                # Process questions and find videos
                results = self.process_questions(questions)

                logger.info(f"[VIDEO_FINDER] Iteration {iteration} results:")
                logger.info(f"  - Total processed: {results['total_processed']}")
                logger.info(f"  - Videos found: {results['videos_found']}")
                logger.info(f"  - Videos added: {results['videos_added']}")
                if results["errors"]:
                    logger.info(f"  - Errors: {len(results['errors'])}")

                # Sleep before next batch
                logger.info(f"[VIDEO_FINDER] Sleeping for {self.sleep_interval}s before next batch")
                time.sleep(self.sleep_interval)

            except Exception as e:
                logger.error(f"[VIDEO_FINDER] Error in main loop: {e}")
                import traceback
                logger.error(f"[VIDEO_FINDER] Traceback: {traceback.format_exc()}")
                logger.info(f"[VIDEO_FINDER] Retrying in {self.error_retry_interval}s")
                time.sleep(self.error_retry_interval)


def main():
    """Main entry point"""
    try:
        logger.info("="*80)
        logger.info("[VIDEO_FINDER] Starting MongoDB Video Finder Integration")
        logger.info("="*80)

        finder = MongoDBVideoFinder()
        finder.run_continuously()

    except KeyboardInterrupt:
        logger.info("[VIDEO_FINDER] Interrupted by user")
    except Exception as e:
        logger.error(f"[VIDEO_FINDER] Fatal error: {e}")
        import traceback
        logger.error(f"[VIDEO_FINDER] Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
