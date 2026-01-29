#!/usr/bin/env python3
"""
Lesson Format → Perseus Format Converter

Converts lesson/module format JSON files (with widget.props, correctAnswer, etc.)
into Perseus-compatible format (with widget.options, answers array, etc.)

Usage:
    python lesson_to_perseus_converter.py input.json output.json
    python lesson_to_perseus_converter.py --dir ./lessons ./questions
"""

import json
import argparse
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib
import time


def generate_question_id(content: str, index: int) -> str:
    """Generate a unique question ID based on content hash."""
    hash_input = f"{content}_{index}_{time.time()}"
    return f"x{hashlib.md5(hash_input.encode()).hexdigest()[:16]}"


def convert_widget_props_to_options(widget_type: str, props: Dict[str, Any], correct_answer: Any) -> Dict[str, Any]:
    """
    Convert lesson format widget.props to Perseus widget.options format.
    
    Lesson format uses:
        - widget.props with minValue, maxValue, etc.
        - correctAnswer as a separate field
    
    Perseus format uses:
        - widget.options with answers array containing correct values
    """
    options = {}
    
    if widget_type == "numeric-input":
        # Convert numeric input widget
        options = {
            "answers": [
                {
                    "value": correct_answer,
                    "status": "correct",
                    "message": "",
                    "simplify": "required",
                    "strict": False,
                    "maxError": props.get("tolerance", None)
                }
            ],
            "size": props.get("size", "normal"),
            "coefficient": props.get("coefficient", False),
            "labelText": props.get("label", "")
        }
        
    elif widget_type == "radio":
        # Convert radio/multiple choice widget
        choices = props.get("choices", [])
        if isinstance(correct_answer, int):
            # correctAnswer is an index
            options = {
                "choices": [
                    {
                        "content": choice.get("content", choice) if isinstance(choice, dict) else str(choice),
                        "correct": i == correct_answer
                    }
                    for i, choice in enumerate(choices)
                ],
                "randomize": props.get("randomize", False),
                "multipleSelect": props.get("multipleSelect", False),
                "countChoices": False,
                "deselectEnabled": False,
                "displayCount": None,
                "hasNoneOfTheAbove": False,
                "numCorrect": 1
            }
        elif isinstance(correct_answer, list):
            # Multiple correct answers
            options = {
                "choices": [
                    {
                        "content": choice.get("content", choice) if isinstance(choice, dict) else str(choice),
                        "correct": i in correct_answer
                    }
                    for i, choice in enumerate(choices)
                ],
                "randomize": props.get("randomize", False),
                "multipleSelect": True,
                "countChoices": False,
                "deselectEnabled": False,
                "displayCount": None,
                "hasNoneOfTheAbove": False,
                "numCorrect": len(correct_answer)
            }
        else:
            # correctAnswer is the actual value - find matching choice
            options = {
                "choices": [
                    {
                        "content": choice.get("content", choice) if isinstance(choice, dict) else str(choice),
                        "correct": (choice.get("content", choice) if isinstance(choice, dict) else str(choice)) == str(correct_answer)
                    }
                    for choice in choices
                ],
                "randomize": props.get("randomize", False),
                "multipleSelect": False,
                "countChoices": False,
                "deselectEnabled": False,
                "displayCount": None,
                "hasNoneOfTheAbove": False,
                "numCorrect": 1
            }
            
    elif widget_type == "input-number":
        # Legacy input-number widget
        options = {
            "value": correct_answer,
            "simplify": props.get("simplify", "required"),
            "size": props.get("size", "normal"),
            "inexact": props.get("inexact", False),
            "maxError": props.get("maxError", 0.1),
            "answerType": props.get("answerType", "number")
        }
        
    elif widget_type == "expression":
        # Expression/equation widget
        options = {
            "answerForms": [
                {
                    "value": str(correct_answer),
                    "form": props.get("form", False),
                    "simplify": props.get("simplify", False),
                    "considered": "correct"
                }
            ],
            "times": props.get("times", False),
            "buttonSets": props.get("buttonSets", ["basic"]),
            "functions": props.get("functions", ["f", "g", "h"])
        }
        
    elif widget_type == "dropdown":
        # Dropdown widget
        choices = props.get("choices", [])
        options = {
            "placeholder": props.get("placeholder", "Select an answer"),
            "choices": [
                {
                    "content": choice.get("content", choice) if isinstance(choice, dict) else str(choice),
                    "correct": i == correct_answer if isinstance(correct_answer, int) else 
                              (choice.get("content", choice) if isinstance(choice, dict) else str(choice)) == str(correct_answer)
                }
                for i, choice in enumerate(choices)
            ]
        }
        
    elif widget_type == "orderer":
        # Orderer widget (drag and drop ordering)
        options = {
            "options": [
                {"content": item, "images": {}, "widgets": {}}
                for item in props.get("items", [])
            ],
            "correctOptions": [
                {"content": item, "images": {}, "widgets": {}}
                for item in (correct_answer if isinstance(correct_answer, list) else props.get("items", []))
            ],
            "height": props.get("height", "auto"),
            "layout": props.get("layout", "horizontal"),
            "otherOptions": []
        }
        
    elif widget_type == "sorter":
        # Sorter widget
        options = {
            "correct": correct_answer if isinstance(correct_answer, list) else [correct_answer],
            "layout": props.get("layout", "horizontal"),
            "padding": props.get("padding", True)
        }
        
    elif widget_type == "matcher":
        # Matcher widget (match items)
        options = {
            "left": props.get("left", []),
            "right": props.get("right", []),
            "labels": props.get("labels", ["", ""]),
            "orderMatters": props.get("orderMatters", False),
            "padding": props.get("padding", True)
        }
        
    elif widget_type == "categorizer":
        # Categorizer widget
        options = {
            "items": props.get("items", []),
            "categories": props.get("categories", []),
            "values": correct_answer if isinstance(correct_answer, list) else [],
            "randomizeItems": props.get("randomizeItems", False)
        }
        
    elif widget_type == "image":
        # Image widget (pass through)
        options = {
            "backgroundImage": props.get("backgroundImage", {}),
            "alt": props.get("alt", ""),
            "caption": props.get("caption", ""),
            "title": props.get("title", ""),
            "labels": props.get("labels", []),
            "box": props.get("box", [400, 400]),
            "range": props.get("range", [[0, 10], [0, 10]]),
            "static": props.get("static", False)
        }
        
    else:
        # Unknown widget type - pass through props as options
        options = props.copy()
        if correct_answer is not None:
            options["_correctAnswer"] = correct_answer
            
    return options


def convert_hints(hints: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert lesson format hints to Perseus format.
    
    Lesson format: ["hint 1", "hint 2", ...]
    Perseus format: [{"content": "hint 1", "images": {}, "widgets": {}}, ...]
    """
    perseus_hints = []
    
    for hint in hints:
        if isinstance(hint, str):
            # Simple string hint
            perseus_hints.append({
                "content": hint,
                "images": {},
                "widgets": {},
                "replace": False
            })
        elif isinstance(hint, dict):
            # Already structured hint
            perseus_hints.append({
                "content": hint.get("content", hint.get("text", "")),
                "images": hint.get("images", {}),
                "widgets": hint.get("widgets", {}),
                "replace": hint.get("replace", False)
            })
        else:
            # Unknown format - convert to string
            perseus_hints.append({
                "content": str(hint),
                "images": {},
                "widgets": {},
                "replace": False
            })
            
    return perseus_hints


def convert_problem_to_perseus(problem: Dict[str, Any], lesson_metadata: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Convert a single practice problem from lesson format to Perseus format.
    """
    problem_id = problem.get("id", f"problem-{index}")
    question_text = problem.get("question", "")
    widget_def = problem.get("widget", {})
    correct_answer = problem.get("correctAnswer")
    hints = problem.get("hints", [])
    
    widget_type = widget_def.get("type", "numeric-input")
    widget_props = widget_def.get("props", {})
    
    # Generate widget ID
    widget_id = f"{widget_type} 1"
    
    # Convert widget props to options
    widget_options = convert_widget_props_to_options(widget_type, widget_props, correct_answer)
    
    # Build question content with widget placeholder
    # Perseus uses [[☃ widget-id]] syntax for widget placeholders
    question_content = f"{question_text}\n\n[[☃ {widget_id}]]"
    
    # Handle visual context if present
    visual_context = problem.get("visualContext", {})
    if visual_context:
        image_url = visual_context.get("imageUrl", "")
        if image_url:
            # Add image widget before the question
            question_content = f"[[☃ image 1]]\n\n{question_content}"
    
    # Build the Perseus question structure
    perseus_question = {
        "questionId": generate_question_id(question_text, index),
        "question": {
            "content": question_content,
            "images": {},
            "widgets": {
                widget_id: {
                    "type": widget_type,
                    "alignment": "default",
                    "static": False,
                    "graded": True,
                    "options": widget_options,
                    "version": {"major": 0, "minor": 0}
                }
            }
        },
        "hints": convert_hints(hints),
        "answerArea": {
            "calculator": problem.get("allowCalculator", False),
            "options": {
                "content": "",
                "images": {},
                "widgets": {}
            },
            "type": "multiple"
        },
        "itemDataVersion": {"major": 0, "minor": 1}
    }
    
    # Add image widget if visual context exists
    if visual_context and visual_context.get("imageUrl"):
        perseus_question["question"]["widgets"]["image 1"] = {
            "type": "image",
            "alignment": "block",
            "static": False,
            "graded": True,
            "options": {
                "backgroundImage": {
                    "url": visual_context.get("imageUrl"),
                    "width": visual_context.get("width", 400),
                    "height": visual_context.get("height", 300)
                },
                "alt": visual_context.get("alt", ""),
                "caption": visual_context.get("caption", ""),
                "title": "",
                "labels": [],
                "box": [visual_context.get("width", 400), visual_context.get("height", 300)],
                "range": [[0, 10], [0, 10]],
                "static": False
            },
            "version": {"major": 0, "minor": 0}
        }
    
    # Add metadata from lesson
    perseus_question["_metadata"] = {
        "lesson_id": lesson_metadata.get("id", ""),
        "lesson_title": lesson_metadata.get("title", ""),
        "difficulty": problem.get("difficulty", lesson_metadata.get("difficulty", "medium")),
        "learning_objectives": lesson_metadata.get("learningObjectives", []),
        "problem_index": index,
        "original_problem_id": problem_id
    }
    
    return perseus_question


def convert_lesson_to_perseus(lesson_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a full lesson file to a list of Perseus questions.
    """
    # Check if this is already Perseus format (array of questions)
    if isinstance(lesson_data, list):
        # Might already be Perseus format - check first item
        if lesson_data and "question" in lesson_data[0] and "widgets" in lesson_data[0].get("question", {}):
            print("File appears to already be in Perseus format, skipping conversion")
            return lesson_data
    
    # Extract lesson metadata
    lesson_metadata = {
        "id": lesson_data.get("id", ""),
        "title": lesson_data.get("title", ""),
        "description": lesson_data.get("description", ""),
        "difficulty": lesson_data.get("difficulty", "medium"),
        "learningObjectives": lesson_data.get("learningObjectives", [])
    }
    
    # Get practice problems
    practice_problems = lesson_data.get("practiceProblems", [])
    
    if not practice_problems:
        print(f"Warning: No practiceProblems found in lesson {lesson_metadata['id']}")
        return []
    
    # Convert each problem
    perseus_questions = []
    for index, problem in enumerate(practice_problems):
        try:
            perseus_question = convert_problem_to_perseus(problem, lesson_metadata, index)
            perseus_questions.append(perseus_question)
        except Exception as e:
            print(f"Error converting problem {index}: {e}")
            continue
    
    return perseus_questions


def convert_file(input_path: str, output_path: str) -> bool:
    """Convert a single file from lesson format to Perseus format."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            lesson_data = json.load(f)
        
        perseus_questions = convert_lesson_to_perseus(lesson_data)
        
        if not perseus_questions:
            print(f"No questions converted from {input_path}")
            return False
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(perseus_questions, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Converted {len(perseus_questions)} questions: {input_path} → {output_path}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON error in {input_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error converting {input_path}: {e}")
        return False


def convert_directory(input_dir: str, output_dir: str) -> Dict[str, int]:
    """Convert all JSON files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if needed
    output_path.mkdir(parents=True, exist_ok=True)
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for json_file in input_path.glob("*.json"):
        output_file = output_path / f"{json_file.stem}_perseus.json"
        
        if convert_file(str(json_file), str(output_file)):
            stats["success"] += 1
        else:
            stats["failed"] += 1
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Convert lesson format JSON to Perseus format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Convert a single file
    python lesson_to_perseus_converter.py lesson.json questions.json
    
    # Convert all files in a directory
    python lesson_to_perseus_converter.py --dir ./lessons ./questions
    
    # Preview conversion without saving
    python lesson_to_perseus_converter.py --preview lesson.json
        """
    )
    
    parser.add_argument("input", help="Input file or directory (with --dir)")
    parser.add_argument("output", nargs="?", help="Output file or directory")
    parser.add_argument("--dir", action="store_true", help="Convert entire directory")
    parser.add_argument("--preview", action="store_true", help="Preview conversion without saving")
    
    args = parser.parse_args()
    
    if args.preview:
        # Preview mode - just show what would be converted
        with open(args.input, 'r') as f:
            data = json.load(f)
        
        questions = convert_lesson_to_perseus(data)
        print(json.dumps(questions, indent=2))
        print(f"\n--- Would convert {len(questions)} questions ---")
        return
    
    if args.dir:
        if not args.output:
            print("Error: Output directory required with --dir")
            sys.exit(1)
        
        stats = convert_directory(args.input, args.output)
        print(f"\n📊 Conversion complete:")
        print(f"   ✅ Success: {stats['success']}")
        print(f"   ❌ Failed: {stats['failed']}")
        
    else:
        if not args.output:
            # Default output name
            args.output = args.input.replace(".json", "_perseus.json")
        
        success = convert_file(args.input, args.output)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
