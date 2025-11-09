"""
Video Categorizer Module
Categorizes videos by language, region, and ranks by quality
"""

from typing import List, Dict, Any
from langdetect import detect, DetectorFactory
import re

# Set seed for consistent language detection
DetectorFactory.seed = 0


class VideoCategorizer:
    """Categorizes and ranks videos"""

    def __init__(self):
        self.language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh-cn': 'Chinese (Simplified)',
            'zh-tw': 'Chinese (Traditional)',
            'ar': 'Arabic',
            'hi': 'Hindi'
        }

    def detect_language(self, text: str) -> str:
        """
        Detect language from text

        Args:
            text: Text to analyze

        Returns:
            Language code (e.g., 'en', 'es')
        """
        try:
            if not text or len(text.strip()) < 10:
                return 'unknown'

            lang_code = detect(text)
            return lang_code

        except Exception as e:
            return 'unknown'

    def get_language_name(self, lang_code: str) -> str:
        """Get full language name from code"""
        return self.language_names.get(lang_code, lang_code.upper())

    def categorize_video(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add language and region categorization to video

        Args:
            video: Video metadata dictionary

        Returns:
            Video dict with added categorization
        """
        # Detect language from transcript, title, and description
        transcript = video.get('transcript', '')
        title = video.get('title', '')
        description = video.get('description', '')

        # Combine text for language detection (transcript is most reliable)
        if transcript and not transcript.startswith('[No transcript'):
            lang_code = self.detect_language(transcript)
        else:
            # Fallback to title and description
            combined_text = f"{title} {description}"
            lang_code = self.detect_language(combined_text)

        video['language_code'] = lang_code
        video['language_name'] = self.get_language_name(lang_code)

        # Detect region from channel name and title
        video['region'] = self._detect_region(video)

        return video

    def _detect_region(self, video: Dict[str, Any]) -> str:
        """
        Detect region/country from video metadata

        Args:
            video: Video metadata

        Returns:
            Region string
        """
        channel = video.get('channel', '').lower()
        title = video.get('title', '').lower()
        description = video.get('description', '').lower()

        combined = f"{channel} {title} {description}"

        # Simple keyword-based region detection
        region_keywords = {
            'US': ['usa', 'american', 'united states'],
            'UK': ['uk', 'british', 'britain'],
            'CA': ['canada', 'canadian'],
            'AU': ['australia', 'australian', 'aussie'],
            'IN': ['india', 'indian'],
            'DE': ['germany', 'german', 'deutsch'],
            'FR': ['france', 'french', 'français'],
            'ES': ['spain', 'spanish', 'español'],
        }

        for region, keywords in region_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return region

        # Default to language-based region
        lang_code = video.get('language_code', 'unknown')
        if lang_code == 'en':
            return 'International English'
        elif lang_code == 'es':
            return 'Spanish-speaking'
        elif lang_code == 'fr':
            return 'French-speaking'
        elif lang_code == 'de':
            return 'German-speaking'
        else:
            return 'International'

    def rank_by_quality(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank videos by quality score

        Quality factors:
        1. Match score (40%)
        2. Engagement metrics (30%): view count, like ratio
        3. Transcript availability (15%)
        4. Video duration appropriateness (15%)

        Args:
            videos: List of video dictionaries

        Returns:
            Sorted list of videos with quality_score added
        """
        scored_videos = []

        for video in videos:
            quality_score = self._calculate_quality_score(video)
            video['quality_score'] = quality_score
            scored_videos.append(video)

        # Sort by quality score descending
        scored_videos.sort(key=lambda x: x['quality_score'], reverse=True)

        return scored_videos

    def _calculate_quality_score(self, video: Dict[str, Any]) -> float:
        """Calculate overall quality score for a video"""

        score = 0.0

        # 1. Match score (40% weight)
        match_score = video.get('match_score', 0)
        score += (match_score / 100) * 40

        # 2. Engagement metrics (30% weight)
        view_count = video.get('view_count', 0)
        like_count = video.get('like_count', 0)

        # Normalize view count (log scale)
        if view_count > 0:
            view_score = min(10, (view_count / 1000) ** 0.5)  # Square root scaling
            score += view_score * 2  # Max 20 points

        # Like ratio
        if view_count > 0 and like_count > 0:
            like_ratio = like_count / view_count
            like_score = min(10, like_ratio * 1000)  # Max 10 points
            score += like_score

        # 3. Transcript availability (15% weight)
        transcript = video.get('transcript', '')
        if transcript and not transcript.startswith('[No transcript'):
            score += 15
        elif '[No transcript available. Video description:]' in transcript:
            score += 5  # Partial credit for having description

        # 4. Video duration appropriateness (15% weight)
        duration = video.get('duration', '')
        duration_seconds = self._parse_duration(duration)

        # Ideal duration: 5-20 minutes for educational content
        if 300 <= duration_seconds <= 1200:  # 5-20 minutes
            score += 15
        elif 180 <= duration_seconds < 300 or 1200 < duration_seconds <= 1800:
            score += 10  # Acceptable but not ideal
        elif duration_seconds > 0:
            score += 5  # Has duration info but not ideal

        return round(score, 2)

    def _parse_duration(self, duration: str) -> int:
        """
        Parse duration string to seconds

        Args:
            duration: Duration string (ISO 8601 for YouTube or seconds for Vimeo)

        Returns:
            Duration in seconds
        """
        if not duration:
            return 0

        # If already an integer (Vimeo)
        if isinstance(duration, int):
            return duration

        # Parse ISO 8601 duration (YouTube)
        # Format: PT#H#M#S
        try:
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass

        return 0

    def categorize_and_rank(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Full categorization and ranking pipeline

        Args:
            videos: List of video dictionaries

        Returns:
            Dictionary with categorized and ranked videos
        """
        # Categorize all videos
        categorized = [self.categorize_video(video) for video in videos]

        # Rank by quality
        ranked = self.rank_by_quality(categorized)

        # Group by language
        by_language = {}
        for video in ranked:
            lang = video.get('language_name', 'Unknown')
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(video)

        # Group by region
        by_region = {}
        for video in ranked:
            region = video.get('region', 'Unknown')
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(video)

        return {
            'all_videos': ranked,
            'by_language': by_language,
            'by_region': by_region,
            'total_count': len(ranked)
        }
