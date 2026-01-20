#!/usr/bin/env python3
"""
Educational Video Finder
Finds relevant YouTube videos for educational questions using Gemini AI.

Usage:
    python find_videos.py <questions_folder> [--output output.json]

Environment Variables Required:
    GOOGLE_API_KEY - Gemini API key
    YOUTUBE_API_KEY - YouTube Data API v3 key
"""

import os
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import time
from dotenv import load_dotenv

# Load environment variables from .env file in VideoFinder directory
video_finder_dir = Path(__file__).parent
dotenv_path = video_finder_dir / '.env'
load_dotenv(dotenv_path=dotenv_path)


class VideoFinder:
    """Main class for finding educational videos using Gemini AI."""
    
    def __init__(self):
        """Initialize the VideoFinder with API keys from environment."""
        # Load API keys from environment
        # Try both GEMINI_API_KEY and GOOGLE_API_KEY
        self.gemini_api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set. Get key from: https://makersuite.google.com/app/apikey")

        if not self.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable not set. Get key from: https://console.cloud.google.com/apis/credentials")

        # Initialize Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.gemini_model = genai.GenerativeModel('models/gemini-2.5-pro')

        # Initialize YouTube API
        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)

        print("✅ APIs initialized successfully")
        print(f"   - Gemini API: Connected")
        print(f"   - YouTube API: Connected")
    
    def find_nested_key(self, data: Any, target_key: str) -> Any:
        """
        Recursively search for a key in nested dictionary/list structures.

        Args:
            data: The data structure to search
            target_key: The key to find

        Returns:
            The value of the first matching key, or None if not found
        """
        if isinstance(data, dict):
            if target_key in data:
                return data[target_key]
            for value in data.values():
                result = self.find_nested_key(value, target_key)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self.find_nested_key(item, target_key)
                if result is not None:
                    return result
        return None

    def load_questions(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Load questions from JSON files in the specified folder.
        Dynamically finds 'itemData' no matter how deeply nested.

        Args:
            folder_path: Path to folder containing question JSON files

        Returns:
            List of question dictionaries with metadata
        """
        questions = []
        folder = Path(folder_path)

        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Find all JSON files
        json_files = list(folder.glob('*.json'))

        if not json_files:
            raise ValueError(f"No JSON files found in: {folder_path}")

        print(f"\n📂 Loading questions from {len(json_files)} files...")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Try to find itemData dynamically
                    item_data_str = self.find_nested_key(data, 'itemData')

                    if item_data_str and isinstance(item_data_str, str):
                        # Parse the itemData JSON string
                        item_data = json.loads(item_data_str)

                        # Extract question content
                        question_content = self.find_nested_key(item_data, 'content')

                        if question_content and isinstance(question_content, str):
                            # Clean up Perseus widgets and markdown - comprehensive cleaning
                            import re
                            cleaned = question_content

                            # 1. Remove Perseus widget markers: [[☃...]]
                            cleaned = re.sub(r'\[\[☃[^\]]+\]\]', '', cleaned)

                            # 2. Remove LaTeX expressions with single/double dollar signs: $...$ or $$...$$
                            cleaned = re.sub(r'\$+[^\$]*\$+', '', cleaned)

                            # 3. Remove LaTeX commands with backslashes: \command, \Large, etc
                            cleaned = re.sub(r'\\[a-zA-Z]+', '', cleaned)

                            # 4. Remove curly braces with content: {...}
                            cleaned = re.sub(r'\{[^\}]*\}', '', cleaned)

                            # 5. Remove markdown image syntax: ![...](...)
                            cleaned = re.sub(r'!\[([^\]]*)\]\(([^\)]*)\)', '', cleaned)

                            # 6. Remove image URIs with web+graphie or similar patterns
                            cleaned = re.sub(r'web\+graphie://[^\s)]+', '', cleaned)

                            # 7. Remove asterisks used for emphasis: *text* or **text**
                            cleaned = re.sub(r'\*+', '', cleaned)

                            # 8. Remove excessive whitespace (multiple spaces, tabs, newlines)
                            cleaned = re.sub(r'\s+', ' ', cleaned)

                            # 9. Clean up trailing dots and commas after stripping
                            cleaned = cleaned.strip()
                            cleaned = re.sub(r'^[\.\,\s]+', '', cleaned)  # Remove leading dots/commas/spaces
                            cleaned = re.sub(r'[\.\,\s]+$', '', cleaned)  # Remove trailing dots/commas/spaces
                            cleaned = cleaned.strip()

                            if cleaned:
                                # Derive topic from folder structure
                                topic = json_file.parent.parent.name

                                questions.append({
                                    'topic': topic,
                                    'content': cleaned,
                                    'source_file': json_file.name
                                })

                    # Fallback: original format handling
                    elif isinstance(data, dict) and 'questions' in data:
                        topic = data.get('topic', json_file.stem)
                        for q in data['questions']:
                            content = q.get('content', '') if isinstance(q, dict) else str(q)
                            if content:
                                questions.append({
                                    'topic': topic,
                                    'content': content,
                                    'source_file': json_file.name
                                })

            except Exception as e:
                print(f"⚠️  Error loading {json_file.name}: {e}")
                continue

        print(f"✅ Loaded {len(questions)} questions from {len(json_files)} files")
        return questions
    
    def generate_search_queries(self, topic: str, sample_questions: List[str], num_queries: int = 3) -> List[str]:
        """
        Generate search queries using Gemini AI.
        
        Args:
            topic: Educational topic
            sample_questions: Sample questions for context
            num_queries: Number of queries to generate
            
        Returns:
            List of search query strings
        """
        prompt = f"""You are an expert at finding educational videos. Generate {num_queries} diverse YouTube search queries to find the best educational videos for this topic.

Topic: {topic}

Sample Questions:
{chr(10).join('- ' + q for q in sample_questions[:5])}

Generate {num_queries} search queries that will find:
1. Clear explanations and tutorials
2. Different teaching approaches (visual, conceptual, step-by-step)
3. Content suitable for students learning this topic

Return ONLY the search queries, one per line, without numbering or extra text."""

        try:
            response = self.gemini_model.generate_content(prompt)
            queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
            return queries[:num_queries]
        except Exception as e:
            print(f"⚠️  Gemini API error, using fallback queries: {e}")
            # Fallback queries
            return [
                f"{topic} tutorial",
                f"{topic} explained",
                f"how to {topic.lower()}"
            ]
    
    def search_youtube(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of video metadata dictionaries
        """
        try:
            request = self.youtube.search().list(
                q=query,
                part='snippet',
                maxResults=max_results,
                type='video',
                videoDuration='medium',  # 4-20 minutes
                videoDefinition='any',
                relevanceLanguage='en'
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                videos.append({
                    'video_id': video_id,
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'channel_title': snippet['channelTitle'],
                    'published_at': snippet['publishedAt']
                })
            
            return videos
            
        except Exception as e:
            print(f"⚠️  YouTube search error for '{query}': {e}")
            return []
    
    def get_video_stats(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed statistics for videos.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            Dictionary mapping video_id to stats
        """
        if not video_ids:
            return {}
        
        try:
            request = self.youtube.videos().list(
                part='statistics,contentDetails',
                id=','.join(video_ids)
            )
            response = request.execute()
            
            stats = {}
            for item in response.get('items', []):
                video_id = item['id']
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                
                stats[video_id] = {
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'duration': content_details.get('duration', 'PT0S')
                }
            
            return stats
            
        except Exception as e:
            print(f"⚠️  Error getting video stats: {e}")
            return {}
    
    def get_transcript(self, video_id: str) -> str:
        """
        Get video transcript.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text or empty string if unavailable
        """
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = ' '.join([entry['text'] for entry in transcript_list])
            return transcript[:5000]  # Limit to first 5000 chars
        except (TranscriptsDisabled, NoTranscriptFound):
            return ""
        except Exception as e:
            print(f"⚠️  Transcript error for {video_id}: {e}")
            return ""
    
    def analyze_video_match(self, video: Dict[str, Any], topic: str, sample_questions: List[str]) -> Dict[str, Any]:
        """
        Analyze how well a video matches the topic using Gemini.
        
        Args:
            video: Video metadata dictionary
            topic: Educational topic
            sample_questions: Sample questions for context
            
        Returns:
            Dictionary with match_score, relevance, and teaching_style
        """
        # Get transcript
        transcript = video.get('transcript', '')
        
        # Prepare content for analysis
        content = f"""Title: {video['title']}
Description: {video['description']}
Transcript Preview: {transcript[:1000] if transcript else 'No transcript available'}"""

        prompt = f"""Analyze if this video is good for teaching this topic.

TOPIC: {topic}

SAMPLE QUESTIONS:
{chr(10).join('- ' + q for q in sample_questions[:3])}

VIDEO CONTENT:
{content}

Rate this video on:
1. Match Score (0-100): How well does it cover the topic?
2. Relevance (High/Medium/Low): Is it directly about this topic?
3. Teaching Style: What's the teaching approach? (Visual/Conceptual/Step-by-step/Practice/Mixed)

Return ONLY in this exact format:
MATCH_SCORE: [number 0-100]
RELEVANCE: [High/Medium/Low]
TEACHING_STYLE: [style]"""

        try:
            response = self.gemini_model.generate_content(prompt)
            text = response.text.strip()
            
            # Parse response
            lines = text.split('\n')
            match_score = 50  # default
            relevance = "Medium"
            teaching_style = "Mixed"
            
            for line in lines:
                if 'MATCH_SCORE:' in line:
                    try:
                        match_score = int(''.join(filter(str.isdigit, line)))
                    except:
                        pass
                elif 'RELEVANCE:' in line:
                    relevance = line.split(':')[-1].strip()
                elif 'TEACHING_STYLE:' in line:
                    teaching_style = line.split(':')[-1].strip()
            
            return {
                'match_score': match_score,
                'relevance': relevance,
                'teaching_style': teaching_style
            }
            
        except Exception as e:
            print(f"⚠️  Error analyzing video {video.get('video_id', 'unknown')}: {e}")
            return {
                'match_score': 50,
                'relevance': 'Medium',
                'teaching_style': 'Unknown'
            }
    
    def calculate_quality_score(self, video: Dict[str, Any]) -> float:
        """
        Calculate overall quality score for a video.
        
        Args:
            video: Video with all metadata
            
        Returns:
            Quality score (0-100)
        """
        score = 0
        
        # Match score (40%)
        score += video.get('match_score', 0) * 0.4
        
        # Engagement (30%)
        views = video.get('view_count', 0)
        likes = video.get('like_count', 0)
        like_ratio = (likes / views * 1000) if views > 0 else 0
        engagement_score = min(views / 10000, 30) + min(like_ratio, 30)
        score += min(engagement_score, 30)
        
        # Transcript availability (15%)
        if video.get('transcript'):
            score += 15
        
        # Duration appropriateness (15%)
        # Assume PT10M (10 minutes) is ideal
        score += 15  # Simplified
        
        return round(score, 1)
    
    def process_topic(self, topic: str, questions: List[Dict[str, Any]], 
                     max_videos: int = 10, num_queries: int = 3) -> Dict[str, Any]:
        """
        Process a single topic to find relevant videos.
        
        Args:
            topic: Educational topic
            questions: List of question dictionaries
            max_videos: Maximum videos to return
            num_queries: Number of search queries to generate
            
        Returns:
            Dictionary with topic results
        """
        print(f"\n🔍 Processing topic: {topic}")
        
        # Extract question content
        question_content = [q['content'] for q in questions if q['content']]
        
        if not question_content:
            print(f"⚠️  No questions found for topic: {topic}")
            return {
                'topic': topic,
                'videos': [],
                'error': 'No questions provided'
            }
        
        # Generate search queries
        print(f"   Generating search queries...")
        queries = self.generate_search_queries(topic, question_content, num_queries)
        print(f"   Generated {len(queries)} queries")
        
        # Search for videos
        all_videos = []
        seen_ids = set()
        
        for query in queries:
            print(f"   Searching: {query}")
            videos = self.search_youtube(query, max_results=5)
            
            for video in videos:
                if video['video_id'] not in seen_ids:
                    seen_ids.add(video['video_id'])
                    all_videos.append(video)
            
            time.sleep(0.5)  # Rate limiting
        
        print(f"   Found {len(all_videos)} unique videos")
        
        # Get video statistics
        video_ids = [v['video_id'] for v in all_videos]
        stats = self.get_video_stats(video_ids)
        
        # Add stats to videos
        for video in all_videos:
            vid_id = video['video_id']
            if vid_id in stats:
                video.update(stats[vid_id])
        
        # Get transcripts and analyze
        print(f"   Analyzing videos...")
        analyzed_videos = []
        
        for video in all_videos[:max_videos * 2]:  # Analyze more than needed
            # Get transcript
            video['transcript'] = self.get_transcript(video['video_id'])
            
            # Analyze match
            analysis = self.analyze_video_match(video, topic, question_content)
            video.update(analysis)
            
            # Calculate quality score
            video['quality_score'] = self.calculate_quality_score(video)
            
            # Add URL
            video['url'] = f"https://www.youtube.com/watch?v={video['video_id']}"
            
            analyzed_videos.append(video)
            
            time.sleep(0.3)  # Rate limiting for Gemini
        
        # Sort by quality score
        analyzed_videos.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # Take top videos
        top_videos = analyzed_videos[:max_videos]
        
        print(f"   ✅ Selected top {len(top_videos)} videos")
        
        return {
            'topic': topic,
            'queries_used': queries,
            'total_videos_found': len(all_videos),
            'videos_analyzed': len(analyzed_videos),
            'videos': top_videos
        }
    
    def process_folder(self, folder_path: str, output_path: str = 'video_results.json',
                      max_videos_per_topic: int = 10) -> Dict[str, Any]:
        """
        Process all questions in a folder.
        
        Args:
            folder_path: Path to folder with question JSON files
            output_path: Path to output JSON file
            max_videos_per_topic: Maximum videos per topic
            
        Returns:
            Complete results dictionary
        """
        print("\n" + "="*80)
        print("🎥 EDUCATIONAL VIDEO FINDER")
        print("="*80)
        
        # Load questions
        questions = self.load_questions(folder_path)
        
        # Group by topic
        topics = {}
        for q in questions:
            topic = q['topic']
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(q)
        
        print(f"\n📊 Found {len(topics)} unique topics")
        
        # Process each topic
        results = {
            'total_topics': len(topics),
            'total_questions': len(questions),
            'topics': []
        }
        
        for i, (topic, topic_questions) in enumerate(topics.items(), 1):
            print(f"\n[{i}/{len(topics)}] Processing: {topic}")
            
            topic_result = self.process_topic(
                topic=topic,
                questions=topic_questions,
                max_videos=max_videos_per_topic
            )
            
            results['topics'].append(topic_result)
        
        # Save results
        print(f"\n💾 Saving results to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "="*80)
        print("✅ COMPLETE!")
        print("="*80)
        print(f"Topics processed: {len(topics)}")
        print(f"Total videos found: {sum(len(t['videos']) for t in results['topics'])}")
        print(f"Output saved to: {output_path}")
        print("="*80 + "\n")
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Find educational videos for questions using Gemini AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_videos.py ./questions
  python find_videos.py ./questions --output my_results.json
  python find_videos.py ./questions --max-videos 15

Environment Variables:
  GOOGLE_API_KEY    - Gemini API key (required)
  YOUTUBE_API_KEY   - YouTube Data API v3 key (required)

Get API Keys:
  Gemini: https://makersuite.google.com/app/apikey
  YouTube: https://console.cloud.google.com/apis/credentials
        """
    )
    
    parser.add_argument(
        'folder',
        help='Path to folder containing question JSON files'
    )
    parser.add_argument(
        '--output', '-o',
        default='video_results.json',
        help='Output JSON file path (default: video_results.json)'
    )
    parser.add_argument(
        '--max-videos', '-m',
        type=int,
        default=10,
        help='Maximum videos per topic (default: 10)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize finder
        finder = VideoFinder()
        
        # Process folder
        finder.process_folder(
            folder_path=args.folder,
            output_path=args.output,
            max_videos_per_topic=args.max_videos
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
