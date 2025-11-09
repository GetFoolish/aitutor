"""
Video Searcher Module
Searches YouTube and Vimeo for educational videos
"""

import os
import requests
from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class VideoSearcher:
    """Searches video platforms for educational content"""

    def __init__(self, youtube_api_key: str = None, vimeo_api_key: str = None):
        self.youtube_api_key = youtube_api_key or os.environ.get("YOUTUBE_API_KEY")
        self.vimeo_api_key = vimeo_api_key or os.environ.get("VIMEO_API_KEY")

        if self.youtube_api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)

    def search_youtube(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of video metadata dictionaries
        """
        if not self.youtube_api_key:
            print("YouTube API key not configured")
            return []

        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                order="relevance",
                videoDuration="medium",  # Prefer videos between 4-20 minutes
                videoDefinition="any",
                relevanceLanguage="en"
            )

            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                # Get additional video details
                video_details = self._get_youtube_video_details(video_id)

                videos.append({
                    'platform': 'youtube',
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'channel': snippet['channelTitle'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail': snippet['thumbnails']['high']['url'],
                    'duration': video_details.get('duration', ''),
                    'view_count': video_details.get('viewCount', 0),
                    'like_count': video_details.get('likeCount', 0),
                    'query': query
                })

            return videos

        except HttpError as e:
            print(f"YouTube API error: {e}")
            return []
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return []

    def _get_youtube_video_details(self, video_id: str) -> Dict[str, Any]:
        """Get detailed information about a YouTube video"""
        try:
            request = self.youtube.videos().list(
                part="contentDetails,statistics",
                id=video_id
            )

            response = request.execute()

            if response['items']:
                item = response['items'][0]
                return {
                    'duration': item['contentDetails']['duration'],
                    'viewCount': int(item['statistics'].get('viewCount', 0)),
                    'likeCount': int(item['statistics'].get('likeCount', 0))
                }

        except Exception as e:
            print(f"Error getting video details: {e}")

        return {}

    def search_vimeo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search Vimeo for videos

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of video metadata dictionaries
        """
        if not self.vimeo_api_key:
            print("Vimeo API key not configured")
            return []

        try:
            url = "https://api.vimeo.com/videos"
            headers = {
                "Authorization": f"bearer {self.vimeo_api_key}",
                "Content-Type": "application/json"
            }

            params = {
                "query": query,
                "per_page": max_results,
                "sort": "relevant",
                "filter": "CC",  # Creative Commons filter for educational content
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            videos = []
            for item in data.get('data', []):
                videos.append({
                    'platform': 'vimeo',
                    'video_id': item['uri'].split('/')[-1],
                    'url': item['link'],
                    'title': item['name'],
                    'description': item['description'] or '',
                    'channel': item['user']['name'],
                    'published_at': item['created_time'],
                    'thumbnail': item['pictures']['sizes'][-1]['link'] if item.get('pictures') else '',
                    'duration': item['duration'],
                    'view_count': item['stats']['plays'],
                    'like_count': item['metadata']['connections']['likes']['total'],
                    'query': query
                })

            return videos

        except Exception as e:
            print(f"Error searching Vimeo: {e}")
            return []

    def search_all_platforms(self, query: str, max_results_per_platform: int = 10) -> List[Dict[str, Any]]:
        """Search all configured platforms"""
        all_videos = []

        # Search YouTube
        youtube_videos = self.search_youtube(query, max_results_per_platform)
        all_videos.extend(youtube_videos)

        # Search Vimeo
        vimeo_videos = self.search_vimeo(query, max_results_per_platform)
        all_videos.extend(vimeo_videos)

        return all_videos
