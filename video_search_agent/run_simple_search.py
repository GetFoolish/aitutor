#!/usr/bin/env python3
"""
Simplified Video Search - Without LLM Features
Searches YouTube and Vimeo for all topics and saves results
"""

import json
import os
from pathlib import Path
from modules.question_loader import QuestionLoader
from googleapiclient.discovery import build
import requests

# API Keys
YOUTUBE_API_KEY = "AIzaSyB3Qm7DI9swfzv6aF5sJeUy1mOUW0bm2I0"
VIMEO_API_KEY = "5ef882523f5d85a22d64e94c82bcb43f"

class SimpleVideoSearcher:
    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    def search_youtube(self, query, max_results=5):
        """Search YouTube"""
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                relevanceLanguage="en"
            )
            response = request.execute()

            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                # Get video details
                details_request = self.youtube.videos().list(
                    part="contentDetails,statistics",
                    id=video_id
                )
                details_response = details_request.execute()

                if details_response['items']:
                    details = details_response['items'][0]
                    videos.append({
                        'platform': 'youtube',
                        'video_id': video_id,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel': snippet['channelTitle'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail': snippet['thumbnails']['high']['url'],
                        'duration': details['contentDetails']['duration'],
                        'view_count': int(details['statistics'].get('viewCount', 0)),
                        'like_count': int(details['statistics'].get('likeCount', 0)),
                        'query': query
                    })

            return videos
        except Exception as e:
            print(f"YouTube error: {e}")
            return []

    def search_vimeo(self, query, max_results=5):
        """Search Vimeo"""
        try:
            url = "https://api.vimeo.com/videos"
            headers = {
                "Authorization": f"bearer {VIMEO_API_KEY}",
                "Content-Type": "application/json"
            }
            params = {
                "query": query,
                "per_page": max_results,
                "sort": "relevant"
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
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
                        'view_count': item['stats']['plays'] or 0,
                        'like_count': item['metadata']['connections']['likes']['total'],
                        'query': query
                    })

                return videos
            return []
        except Exception as e:
            print(f"Vimeo error: {e}")
            return []

def main():
    print("\n" + "="*80)
    print("SIMPLE VIDEO SEARCH - ALL TOPICS")
    print("="*80)

    # Load questions
    questions_dir = "../files (1)"
    loader = QuestionLoader(questions_dir)
    all_questions = loader.load_all_questions()

    # Group by main topics (not individual files)
    topics_dict = {}
    for q in all_questions:
        topic = q.get('topic', '')
        topic_parts = topic.split(' > ')
        if len(topic_parts) > 1:
            main_topic = ' > '.join(topic_parts[:-1])
        else:
            main_topic = topic

        if main_topic not in topics_dict:
            topics_dict[main_topic] = []
        topics_dict[main_topic].append(q)

    print(f"\nFound {len(all_questions)} questions in {len(topics_dict)} topics")

    # Create searcher
    searcher = SimpleVideoSearcher()

    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    all_results = {}

    for i, (topic, questions) in enumerate(topics_dict.items(), 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(topics_dict)}] Processing: {topic}")
        print(f"{'='*80}")

        # Create search query
        query_parts = topic.split(' > ')
        query = query_parts[-1].replace('_', ' ')

        print(f"Search query: '{query}'")
        print(f"Questions: {len(questions)}")

        # Search both platforms
        print("\nSearching YouTube...")
        youtube_videos = searcher.search_youtube(query, max_results=5)
        print(f"  Found {len(youtube_videos)} videos")

        print("Searching Vimeo...")
        vimeo_videos = searcher.search_vimeo(query, max_results=5)
        print(f"  Found {len(vimeo_videos)} videos")

        all_videos = youtube_videos + vimeo_videos

        # Save results for this topic
        topic_results = {
            'topic': topic,
            'query': query,
            'num_questions': len(questions),
            'sample_questions': [q.get('content', '')[:100] for q in questions[:3]],
            'total_videos_found': len(all_videos),
            'youtube_count': len(youtube_videos),
            'vimeo_count': len(vimeo_videos),
            'videos': all_videos
        }

        all_results[topic] = topic_results

        # Save individual topic file
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
        safe_topic = safe_topic.replace(' ', '_')[:100]
        topic_file = output_dir / f"{safe_topic}_simple.json"

        with open(topic_file, 'w') as f:
            json.dump(topic_results, f, indent=2)

        print(f"  Saved to: {topic_file}")

        # Show top videos
        if all_videos:
            print(f"\n  Top 3 videos:")
            for j, video in enumerate(all_videos[:3], 1):
                print(f"    {j}. [{video['platform'].upper()}] {video['title'][:60]}")
                print(f"       {video['url']}")

    # Save combined results
    combined_file = output_dir / "combined_simple_results.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    # Summary
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)

    total_youtube = sum(r['youtube_count'] for r in all_results.values())
    total_vimeo = sum(r['vimeo_count'] for r in all_results.values())

    print(f"\nTopics processed: {len(all_results)}")
    print(f"Total YouTube videos: {total_youtube}")
    print(f"Total Vimeo videos: {total_vimeo}")
    print(f"Total videos found: {total_youtube + total_vimeo}")

    print(f"\nResults saved to: {output_dir}/")
    print(f"Combined file: {combined_file}")

    print("\n✅ Video search complete!")

if __name__ == "__main__":
    main()
