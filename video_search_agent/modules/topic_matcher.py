"""
Topic Matcher Module
Matches video transcripts to educational topics with percentage scoring
"""

import os
from typing import Dict, Any, List
from openai import OpenAI
import re


class TopicMatcher:
    """Matches video content to educational topics using OpenRouter LLM"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free")

    def calculate_match_score(
        self,
        topic: str,
        questions: List[Dict[str, Any]],
        transcript: str,
        video_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate how well a video matches the topic

        Args:
            topic: The educational topic
            questions: Sample questions for the topic
            transcript: Video transcript text
            video_metadata: Video metadata including title and description

        Returns:
            Dictionary with match score and analysis
        """

        # Limit transcript length for API call
        transcript_sample = transcript[:8000] if len(transcript) > 8000 else transcript

        # Sample questions for context
        sample_questions = questions[:3] if len(questions) > 3 else questions
        question_texts = [q.get("content", "") for q in sample_questions]

        prompt = f"""You are an expert at evaluating educational video content.

Topic: {topic}

Sample Questions this video should help with:
{chr(10).join(f"- {q}" for q in question_texts if q)}

Video Title: {video_metadata.get('title', '')}
Video Description: {video_metadata.get('description', '')[:500]}

Transcript Sample:
{transcript_sample}

Analyze how well this video matches the educational topic and would help answer the questions.

Provide your response in this EXACT format:
MATCH_SCORE: [number from 0-100]
RELEVANCE: [Low/Medium/High]
TEACHING_STYLE: [Visual/Conceptual/Practical/Mixed]
COVERAGE: [Brief description of what aspects of the topic are covered]
QUALITY_INDICATORS: [Brief notes on video quality indicators]

Be strict in your scoring. Only give high scores (70+) if the video directly teaches the topic."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis_text = response.choices[0].message.content.strip()

            # Parse the structured response
            result = self._parse_analysis(analysis_text)
            result['raw_analysis'] = analysis_text

            return result

        except Exception as e:
            print(f"Error calculating match score: {e}")
            # Return fallback scoring
            return self._calculate_fallback_score(topic, transcript, video_metadata)

    def _parse_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the structured analysis response"""
        result = {
            'match_score': 0,
            'relevance': 'Unknown',
            'teaching_style': 'Unknown',
            'coverage': '',
            'quality_indicators': ''
        }

        # Extract match score
        match_score_match = re.search(r'MATCH_SCORE:\s*(\d+)', analysis_text)
        if match_score_match:
            result['match_score'] = int(match_score_match.group(1))

        # Extract relevance
        relevance_match = re.search(r'RELEVANCE:\s*(\w+)', analysis_text)
        if relevance_match:
            result['relevance'] = relevance_match.group(1)

        # Extract teaching style
        style_match = re.search(r'TEACHING_STYLE:\s*([^\n]+)', analysis_text)
        if style_match:
            result['teaching_style'] = style_match.group(1).strip()

        # Extract coverage
        coverage_match = re.search(r'COVERAGE:\s*([^\n]+)', analysis_text)
        if coverage_match:
            result['coverage'] = coverage_match.group(1).strip()

        # Extract quality indicators
        quality_match = re.search(r'QUALITY_INDICATORS:\s*([^\n]+)', analysis_text)
        if quality_match:
            result['quality_indicators'] = quality_match.group(1).strip()

        return result

    def _calculate_fallback_score(
        self,
        topic: str,
        transcript: str,
        video_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate a basic fallback score using keyword matching"""

        # Extract key terms from topic
        topic_terms = set(topic.lower().split())

        # Count matches in title (weighted 3x)
        title = video_metadata.get('title', '').lower()
        title_matches = sum(3 for term in topic_terms if term in title)

        # Count matches in description (weighted 2x)
        description = video_metadata.get('description', '').lower()
        desc_matches = sum(2 for term in topic_terms if term in description)

        # Count matches in transcript
        transcript_lower = transcript.lower()
        transcript_matches = sum(1 for term in topic_terms if term in transcript_lower)

        # Calculate basic score (max 100)
        total_matches = title_matches + desc_matches + transcript_matches
        score = min(100, total_matches * 10)

        return {
            'match_score': score,
            'relevance': 'Medium' if score > 30 else 'Low',
            'teaching_style': 'Unknown',
            'coverage': 'Automated keyword-based analysis',
            'quality_indicators': 'Fallback analysis used'
        }

    def batch_score_videos(
        self,
        topic: str,
        questions: List[Dict[str, Any]],
        videos_with_transcripts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Score multiple videos for a topic

        Args:
            topic: Educational topic
            questions: Questions for the topic
            videos_with_transcripts: List of video dicts with 'transcript' key

        Returns:
            List of videos with added scoring information
        """
        scored_videos = []

        for video in videos_with_transcripts:
            transcript = video.get('transcript', '')

            if not transcript or transcript.startswith('[No transcript'):
                # Skip videos without transcripts or use lower priority
                score_result = {
                    'match_score': 0,
                    'relevance': 'Unknown',
                    'teaching_style': 'Unknown',
                    'coverage': 'No transcript available',
                    'quality_indicators': 'Cannot analyze without transcript'
                }
            else:
                score_result = self.calculate_match_score(
                    topic,
                    questions,
                    transcript,
                    video
                )

            # Add scoring to video
            video['match_score'] = score_result['match_score']
            video['relevance'] = score_result['relevance']
            video['teaching_style'] = score_result['teaching_style']
            video['coverage'] = score_result['coverage']
            video['quality_indicators'] = score_result['quality_indicators']

            scored_videos.append(video)

        return scored_videos
