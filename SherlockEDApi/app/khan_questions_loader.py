# MVP components to build
# Load from /CurriculumBuilder/khan_academy_json/
import json
import os
import random
import glob
import pathlib

from db.mongo_client import ping_database
from db.perseus_repository import get_random_questions

path = pathlib.Path(__file__).parent.parent.resolve() / "CurriculumBuilder" 

def load_json_objects_from_dir(directory: str, pattern: str = "*.json") -> list:
    """Load all JSON objects from files in a directory matching a pattern."""
    all_objects = []
    file_pattern = os.path.join(directory, pattern)
    for file_path in glob.glob(file_pattern):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If the file contains a list, extend; if dict, append
                if isinstance(data, list):
                    all_objects.extend(data)
                else:
                    all_objects.append(data)
        except Exception as e:
            print(f"⚠️ Failed to load {file_path}: {e}")
    return all_objects

def load_questions(sample_size: int = 10):
    """Loads the requested number of questions"""
    if ping_database():
        try:
            questions = get_random_questions(sample_size)
            if questions:
                return questions
        except Exception as exc:
            print(f"⚠️ MongoDB question load failed: {exc}")

    all_questions = load_json_objects_from_dir(path)
    if all_questions:
        try:
            return random.sample(all_questions, min(sample_size, len(all_questions)))
        except Exception as e:
            print(f"Failed to load questions from files: {e}")
    return []
