"""
Query Generator Module
Uses LLM to generate intelligent search queries for video platforms
"""

import os
from typing import List, Dict, Any
from openai import OpenAI


class QueryGenerator:
    """Generates intelligent search queries using OpenRouter LLM"""

    def __init__(self, api_key: str = None):
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free")

    def generate_queries(self, topic: str, questions: List[Dict[str, Any]], num_queries: int = 5) -> List[str]:
        """
        Generate intelligent search queries for a given topic and questions

        Args:
            topic: The educational topic
            questions: List of question dictionaries
            num_queries: Number of search queries to generate

        Returns:
            List of search query strings
        """

        # Sample a few questions for context
        sample_questions = questions[:5] if len(questions) > 5 else questions
        question_texts = [q.get("content", "") for q in sample_questions]

        prompt = f"""You are an expert at creating YouTube and Vimeo search queries for educational content.

Topic: {topic}

Sample Questions:
{chr(10).join(f"- {q}" for q in question_texts if q)}

Generate {num_queries} diverse and intelligent search queries that would help find high-quality educational videos for this topic.
The queries should:
1. Target different aspects of the topic
2. Include both general and specific searches
3. Use terms commonly found in educational videos
4. Consider different teaching styles (visual, conceptual, practical)
5. Include variations for different age groups if applicable

Return ONLY the search queries, one per line, without numbering or explanations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract queries from response
            queries_text = response.choices[0].message.content.strip()
            queries = [q.strip() for q in queries_text.split('\n') if q.strip()]

            return queries[:num_queries]

        except Exception as e:
            print(f"Error generating queries: {e}")
            # Fallback to basic queries
            return self._generate_fallback_queries(topic)

    def _generate_fallback_queries(self, topic: str) -> List[str]:
        """Generate basic fallback queries if LLM fails"""
        topic_clean = topic.replace(' > ', ' ')

        return [
            f"{topic_clean} tutorial",
            f"how to {topic_clean}",
            f"{topic_clean} explained",
            f"{topic_clean} for beginners",
            f"{topic_clean} lesson"
        ]

    def enhance_query_for_platform(self, query: str, platform: str) -> str:
        """Enhance query for specific platform"""
        if platform.lower() == "youtube":
            return query
        elif platform.lower() == "vimeo":
            # Vimeo tends to have more professional/educational content
            return f"{query} education"
        else:
            return query
