"""
Main Video Search Agent
Orchestrates the entire video search and analysis pipeline
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from modules.question_loader import QuestionLoader
from modules.query_generator import QueryGenerator
from modules.video_searcher import VideoSearcher
from modules.transcript_fetcher import TranscriptFetcher
from modules.topic_matcher import TopicMatcher
from modules.video_categorizer import VideoCategorizer


class VideoSearchAgent:
    """Main agent orchestrating video search and analysis"""

    def __init__(
        self,
        openrouter_api_key: str = None,
        youtube_api_key: str = None,
        vimeo_api_key: str = None
    ):
        """
        Initialize the video search agent

        Args:
            openrouter_api_key: OpenRouter API key for LLM
            youtube_api_key: YouTube Data API key
            vimeo_api_key: Vimeo API key
        """
        self.query_generator = QueryGenerator(openrouter_api_key)
        self.video_searcher = VideoSearcher(youtube_api_key, vimeo_api_key)
        self.transcript_fetcher = TranscriptFetcher()
        self.topic_matcher = TopicMatcher(openrouter_api_key)
        self.categorizer = VideoCategorizer()

    def process_topic(
        self,
        topic: str,
        questions: List[Dict[str, Any]],
        max_videos_per_query: int = 5,
        num_queries: int = 3,
        min_match_score: int = 40
    ) -> Dict[str, Any]:
        """
        Process a single topic: search, analyze, and rank videos

        Args:
            topic: Educational topic
            questions: List of questions for this topic
            max_videos_per_query: Max videos to fetch per search query
            num_queries: Number of search queries to generate
            min_match_score: Minimum match score to include video (0-100)

        Returns:
            Dictionary with processed video results
        """
        print(f"\n{'='*80}")
        print(f"Processing topic: {topic}")
        print(f"{'='*80}")

        # Step 1: Generate search queries
        print(f"\n[1/6] Generating {num_queries} search queries...")
        queries = self.query_generator.generate_queries(topic, questions, num_queries)
        print(f"Generated queries:")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")

        # Step 2: Search for videos
        print(f"\n[2/6] Searching for videos...")
        all_videos = []
        for query in queries:
            videos = self.video_searcher.search_all_platforms(query, max_videos_per_query)
            all_videos.extend(videos)
            print(f"  Found {len(videos)} videos for: {query}")

        # Remove duplicates (same video_id and platform)
        unique_videos = self._deduplicate_videos(all_videos)
        print(f"  Total unique videos: {len(unique_videos)}")

        # Step 3: Fetch transcripts
        print(f"\n[3/6] Fetching transcripts...")
        videos_with_transcripts = []
        for i, video in enumerate(unique_videos, 1):
            print(f"  [{i}/{len(unique_videos)}] Fetching transcript for: {video['title'][:60]}...")
            transcript = self.transcript_fetcher.get_transcript_with_fallback(video)
            video['transcript'] = transcript
            videos_with_transcripts.append(video)

        # Step 4: Match videos to topic and score
        print(f"\n[4/6] Analyzing topic match and scoring...")
        scored_videos = self.topic_matcher.batch_score_videos(
            topic,
            questions,
            videos_with_transcripts
        )

        # Filter by minimum match score
        filtered_videos = [v for v in scored_videos if v['match_score'] >= min_match_score]
        print(f"  {len(filtered_videos)} videos meet minimum score of {min_match_score}")

        # Step 5: Categorize and rank
        print(f"\n[5/6] Categorizing by language/region and ranking by quality...")
        results = self.categorizer.categorize_and_rank(filtered_videos)

        print(f"  Languages found: {', '.join(results['by_language'].keys())}")
        print(f"  Regions found: {', '.join(results['by_region'].keys())}")

        # Step 6: Compile final results
        print(f"\n[6/6] Compiling results...")
        final_results = {
            'topic': topic,
            'queries_used': queries,
            'total_videos_found': len(all_videos),
            'unique_videos': len(unique_videos),
            'videos_after_filtering': len(filtered_videos),
            'top_videos': results['all_videos'][:10],  # Top 10
            'all_videos': results['all_videos'],
            'by_language': results['by_language'],
            'by_region': results['by_region']
        }

        print(f"\nTop 3 videos:")
        for i, video in enumerate(results['all_videos'][:3], 1):
            print(f"  {i}. [{video['quality_score']:.1f}] {video['title']}")
            print(f"     Match: {video['match_score']}% | {video['language_name']} | {video['platform']}")

        return final_results

    def process_all_topics(
        self,
        questions_dir: str,
        output_dir: str = "output",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process all topics from a questions directory

        Args:
            questions_dir: Directory containing question JSON files
            output_dir: Directory to save results
            **kwargs: Additional arguments passed to process_topic

        Returns:
            Dictionary with all results
        """
        # Load questions
        print("Loading questions from directory...")
        loader = QuestionLoader(questions_dir)
        all_questions = loader.load_all_questions()
        grouped_questions = loader.group_by_topic(all_questions)

        print(f"Found {len(grouped_questions)} topics with {len(all_questions)} total questions")

        # Process each topic
        all_results = {}

        for topic, questions in grouped_questions.items():
            try:
                results = self.process_topic(topic, questions, **kwargs)
                all_results[topic] = results

                # Save individual topic results
                self._save_topic_results(topic, results, output_dir)

            except Exception as e:
                print(f"Error processing topic '{topic}': {e}")
                continue

        # Save combined results
        self._save_combined_results(all_results, output_dir)

        return all_results

    def _deduplicate_videos(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate videos based on platform and video_id"""
        seen = set()
        unique = []

        for video in videos:
            key = (video['platform'], video['video_id'])
            if key not in seen:
                seen.add(key)
                unique.append(video)

        return unique

    def _save_topic_results(self, topic: str, results: Dict[str, Any], output_dir: str):
        """Save results for a single topic"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Create safe filename
        safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
        safe_topic = safe_topic.replace(' ', '_')[:100]

        filename = output_path / f"{safe_topic}_results.json"

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\nSaved results to: {filename}")

    def _save_combined_results(self, all_results: Dict[str, Any], output_dir: str):
        """Save combined results from all topics"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        filename = output_path / "combined_results.json"

        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n{'='*80}")
        print(f"All results saved to: {filename}")
        print(f"{'='*80}")


def main():
    """Main entry point"""
    import sys

    # Check for API keys
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    if not os.environ.get("YOUTUBE_API_KEY"):
        print("WARNING: YOUTUBE_API_KEY not set. YouTube search will not work.")
        print("Get one from: https://console.developers.google.com/")

    # Initialize agent
    agent = VideoSearchAgent()

    # Example: Process questions from directory
    questions_dir = "../files (1)"

    if len(sys.argv) > 1:
        questions_dir = sys.argv[1]

    if not os.path.exists(questions_dir):
        print(f"ERROR: Questions directory not found: {questions_dir}")
        sys.exit(1)

    # Process all topics
    results = agent.process_all_topics(
        questions_dir=questions_dir,
        output_dir="output",
        max_videos_per_query=5,
        num_queries=3,
        min_match_score=40
    )

    print(f"\n{'='*80}")
    print(f"PROCESSING COMPLETE!")
    print(f"Processed {len(results)} topics")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
