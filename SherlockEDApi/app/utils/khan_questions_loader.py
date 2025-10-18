import json
import os
import random
import glob
import pathlib


path = pathlib.Path(__file__).resolve().parents[2] / "CurriculumBuilder"
# paths for json validation
generated_path = pathlib.Path(__file__).resolve().parents[3] / "GenAIQuestions" / "new"
source_path = pathlib.Path(__file__).resolve().parents[3] / "GenAIQuestions" / "examples"


def load_json_objects_from_dir() -> list:
    """Load all JSON objects from files in a directory matching a pattern."""
    all_objects = []
    file_pattern = os.path.join(path, "*.json")
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

def load_generated_json_from_dir():
    """Load all generated questions"""
    file_pattern = os.path.join(source_path, "*.json")
    all_objects = []
    for file_path in glob.glob(file_pattern):
        filename = file_path.split("\\")[-1].removesuffix(".json")
        data = {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data["source"] = json.load(f)
            with open(f"{str(generated_path)}/{filename}_generated.json", "r", encoding="utf-8") as f:
                data["generated"] = json.load(f)
            all_objects.append(data)
        except Exception as e:
            print(f"Unable to load JSON: {e}")
    return all_objects

def load_questions(sample_size, is_generated: bool = False):
    """Loads the requested number of questions"""
    if (is_generated == True):
        all_questions = load_generated_json_from_dir()
    else:
        all_questions = load_json_objects_from_dir()
    if all_questions:
        if sample_size <= len(all_questions):
            try:
                sample = random.sample(all_questions,sample_size)
                return sample
            except Exception as e:
                print(f"Failed to load questions: {e}")
        if sample_size > len(all_questions):
            try:
                return all_questions
            except Exception as e:
                print(f"Failed to load questions: {e}")