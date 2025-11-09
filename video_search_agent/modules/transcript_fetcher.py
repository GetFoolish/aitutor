"""
Transcript Fetcher Module
Fetches and processes video transcripts from YouTube and Vimeo
"""

from typing import Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests


class TranscriptFetcher:
    """Fetches transcripts from video platforms"""

    def __init__(self):
        pass

    def fetch_youtube_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript for a YouTube video

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None if unavailable
        """
        try:
            # Try to get transcript in English first
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to find an English transcript (manual or auto-generated)
            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
            except:
                # If no English transcript, try to get any available and translate
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    # Get any available transcript
                    available = list(transcript_list)
                    if available:
                        transcript = available[0]

            if transcript:
                transcript_data = transcript.fetch()
                # Combine all text segments
                full_text = ' '.join([segment['text'] for segment in transcript_data])
                return full_text.strip()

        except TranscriptsDisabled:
            print(f"Transcripts are disabled for video {video_id}")
        except NoTranscriptFound:
            print(f"No transcript found for video {video_id}")
        except Exception as e:
            print(f"Error fetching YouTube transcript for {video_id}: {e}")

        return None

    def fetch_vimeo_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript for a Vimeo video

        Args:
            video_id: Vimeo video ID

        Returns:
            Transcript text or None if unavailable
        """
        try:
            # Vimeo API endpoint for text tracks (captions/subtitles)
            url = f"https://api.vimeo.com/videos/{video_id}/texttracks"

            # Note: This requires authentication with Vimeo API
            # For now, return None as Vimeo transcript access is more restricted
            # In production, implement with proper Vimeo API credentials

            print(f"Vimeo transcript fetching not fully implemented for {video_id}")
            return None

        except Exception as e:
            print(f"Error fetching Vimeo transcript for {video_id}: {e}")
            return None

    def fetch_transcript(self, video: Dict[str, Any]) -> Optional[str]:
        """
        Fetch transcript for a video based on its platform

        Args:
            video: Video metadata dictionary with 'platform' and 'video_id'

        Returns:
            Transcript text or None if unavailable
        """
        platform = video.get('platform', '').lower()
        video_id = video.get('video_id')

        if not video_id:
            return None

        if platform == 'youtube':
            return self.fetch_youtube_transcript(video_id)
        elif platform == 'vimeo':
            return self.fetch_vimeo_transcript(video_id)
        else:
            return None

    def get_transcript_with_fallback(self, video: Dict[str, Any]) -> str:
        """
        Get transcript with fallback to description if transcript unavailable

        Args:
            video: Video metadata dictionary

        Returns:
            Transcript or description text
        """
        transcript = self.fetch_transcript(video)

        if transcript:
            return transcript

        # Fallback to video description
        description = video.get('description', '')
        if description:
            return f"[No transcript available. Video description:] {description}"

        return "[No transcript or description available]"
