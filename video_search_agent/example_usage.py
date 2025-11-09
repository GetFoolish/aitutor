"""
Example Usage of Video Search Agent
Demonstrates how to use the agent with sample topics
"""

import os
from main_agent import VideoSearchAgent


def example_single_topic():
    """Example: Process a single topic"""

    # Initialize agent
    agent = VideoSearchAgent(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        youtube_api_key=os.environ.get("YOUTUBE_API_KEY"),
        vimeo_api_key=os.environ.get("VIMEO_API_KEY")
    )

    # Define a topic and sample questions
    topic = "Adding numbers within 20"
    questions = [
        {
            "content": "Add 6 + 1 using a number line",
            "topic": "Addition within 20"
        },
        {
            "content": "What is 12 + 7?",
            "topic": "Addition within 20"
        },
        {
            "content": "Use arrays to add numbers",
            "topic": "Addition with arrays"
        }
    ]

    # Process the topic
    results = agent.process_topic(
        topic=topic,
        questions=questions,
        max_videos_per_query=5,
        num_queries=3,
        min_match_score=40
    )

    # Display results
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)

    print(f"\nTopic: {results['topic']}")
    print(f"Total videos found: {results['total_videos_found']}")
    print(f"After filtering: {results['videos_after_filtering']}")

    print(f"\nTop 5 Recommended Videos:")
    print("-" * 80)

    for i, video in enumerate(results['top_videos'][:5], 1):
        print(f"\n{i}. {video['title']}")
        print(f"   URL: {video['url']}")
        print(f"   Quality Score: {video['quality_score']:.1f}/100")
        print(f"   Match Score: {video['match_score']}%")
        print(f"   Language: {video['language_name']}")
        print(f"   Region: {video['region']}")
        print(f"   Platform: {video['platform'].upper()}")
        print(f"   Views: {video['view_count']:,}")

    # Show language breakdown
    print("\n" + "="*80)
    print("VIDEOS BY LANGUAGE")
    print("="*80)
    for lang, videos in results['by_language'].items():
        print(f"{lang}: {len(videos)} videos")

    # Show region breakdown
    print("\n" + "="*80)
    print("VIDEOS BY REGION")
    print("="*80)
    for region, videos in results['by_region'].items():
        print(f"{region}: {len(videos)} videos")


def example_batch_processing():
    """Example: Process all topics from directory"""

    agent = VideoSearchAgent()

    # Process all topics from questions directory
    results = agent.process_all_topics(
        questions_dir="../files (1)",
        output_dir="output",
        max_videos_per_query=3,  # Fewer videos for faster processing
        num_queries=2,
        min_match_score=50  # Higher threshold
    )

    print(f"\nProcessed {len(results)} topics")
    print("Check the 'output' directory for detailed results")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        example_batch_processing()
    else:
        example_single_topic()
