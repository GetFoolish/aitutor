"""
Question Loader Module
Loads and processes educational questions from JSON files
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any


class QuestionLoader:
    """Loads questions from directory structure"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def load_all_questions(self) -> List[Dict[str, Any]]:
        """Load all questions from the directory structure"""
        questions = []

        # Find all JSON files
        json_files = list(self.base_path.rglob("*.json"))

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                question_data = self._extract_question_data(data, json_file)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue

        return questions

    def _extract_question_data(self, data: Dict, file_path: Path) -> Dict[str, Any]:
        """Extract relevant data from question JSON"""
        try:
            item = data.get("data", {}).get("assessmentItem", {}).get("item", {})

            if not item:
                return None

            # Parse the itemData JSON string
            item_data_str = item.get("itemData", "{}")
            item_data = json.loads(item_data_str)

            # Extract question content
            question_content = item_data.get("question", {}).get("content", "")

            # Clean the question content (remove LaTeX, widgets, etc.)
            clean_content = self._clean_content(question_content)

            # Extract topic from file path
            topic = self._extract_topic_from_path(file_path)

            return {
                "id": item.get("id", ""),
                "content": clean_content,
                "raw_content": question_content,
                "problem_type": item.get("problemType", ""),
                "topic": topic,
                "file_path": str(file_path)
            }
        except Exception as e:
            print(f"Error extracting question data: {e}")
            return None

    def _clean_content(self, content: str) -> str:
        """Clean question content by removing LaTeX, HTML, and special formatting"""
        # Remove LaTeX math expressions
        content = re.sub(r'\$+[^\$]+\$+', '', content)

        # Remove widget placeholders
        content = re.sub(r'\[\[☃[^\]]+\]\]', '', content)

        # Remove image references
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)

        # Remove markdown formatting
        content = re.sub(r'\*\*', '', content)
        content = re.sub(r'\*', '', content)

        # Remove extra whitespace
        content = ' '.join(content.split())

        return content.strip()

    def _extract_topic_from_path(self, file_path: Path) -> str:
        """Extract topic from file path"""
        # Get the parts of the path
        parts = file_path.parts

        # Find educational topic parts (those starting with numbers)
        topic_parts = []
        for part in parts:
            if re.match(r'^\d+\.\d+', part):
                # Clean up the topic name
                topic = part.split('_', 1)[-1] if '_' in part else part
                topic = topic.replace('_', ' ')
                topic_parts.append(topic)

        return ' > '.join(topic_parts) if topic_parts else "Unknown"

    def group_by_topic(self, questions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group questions by their topic"""
        grouped = {}
        for q in questions:
            topic = q.get("topic", "Unknown")
            if topic not in grouped:
                grouped[topic] = []
            grouped[topic].append(q)

        return grouped
