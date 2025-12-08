"""
Base Filter Interface for Question Filtering
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path


class BaseQuestionFilter(ABC):
    """
    Abstract base class for question filters.
    Implement this interface to create custom filters for selecting questions.
    """

    @abstractmethod
    def filter(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of questions based on criteria.

        Args:
            questions: List of question dictionaries to filter

        Returns:
            Filtered list of questions
        """
        pass

    @abstractmethod
    def matches(self, question: Dict[str, Any]) -> bool:
        """
        Check if a single question matches the filter criteria.

        Args:
            question: Question dictionary to check

        Returns:
            True if question matches criteria, False otherwise
        """
        pass

    def filter_from_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Load and filter questions from a directory of JSON files.

        Args:
            directory: Path to directory containing JSON question files

        Returns:
            List of filtered questions with their file paths
        """
        import json

        filtered_questions = []
        directory = Path(directory)

        for json_file in directory.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    question_data = json.load(f)

                if self.matches(question_data):
                    question_data['_file_path'] = str(json_file)
                    question_data['_file_name'] = json_file.name
                    filtered_questions.append(question_data)

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading {json_file}: {e}")
                continue

        return filtered_questions
