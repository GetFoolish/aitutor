"""
Analyze MongoDB perseus_questions collection structure
This script examines the schema of questions stored in MongoDB
"""

import os
import sys
import json
from collections import defaultdict
from typing import Any, Dict, Set

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from managers.mongodb_manager import mongo_db

def analyze_field_types(data: Any, path: str = "", type_map: Dict[str, Set[str]] = None) -> Dict[str, Set[str]]:
    """Recursively analyze field types in a document"""
    if type_map is None:
        type_map = defaultdict(set)

    if isinstance(data, dict):
        for key, value in data.items():
            field_path = f"{path}.{key}" if path else key
            type_name = type(value).__name__
            type_map[field_path].add(type_name)

            if isinstance(value, dict):
                analyze_field_types(value, field_path, type_map)
            elif isinstance(value, list) and value:
                type_map[f"{field_path}[]"].add(type(value[0]).__name__)
                if isinstance(value[0], dict):
                    analyze_field_types(value[0], f"{field_path}[]", type_map)

    return type_map

def analyze_widget_types(questions: list) -> Dict[str, int]:
    """Count widget types across all questions"""
    widget_types = defaultdict(int)

    for q in questions:
        question = q.get('question', {})
        widgets = question.get('widgets', {})

        for widget_id, widget_data in widgets.items():
            widget_type = widget_data.get('type', 'unknown')
            widget_types[widget_type] += 1

    return dict(widget_types)

def main():
    print("=" * 80)
    print("MongoDB perseus_questions Collection Analysis")
    print("=" * 80)

    # Get total count
    total_count = mongo_db.perseus_questions.count_documents({})
    print(f"\nTotal questions in database: {total_count}")

    # Get sample questions
    sample_size = min(100, total_count)
    questions = list(mongo_db.perseus_questions.find({}).limit(sample_size))

    print(f"Analyzing {len(questions)} sample questions...")

    # Analyze field structure
    print("\n" + "=" * 80)
    print("FIELD STRUCTURE ANALYSIS")
    print("=" * 80)

    all_fields = defaultdict(set)
    for q in questions:
        analyze_field_types(q, "", all_fields)

    # Print top-level fields
    print("\nTop-level fields:")
    top_level = sorted([f for f in all_fields.keys() if '.' not in f])
    for field in top_level:
        types = ', '.join(all_fields[field])
        print(f"  - {field}: {types}")

    # Analyze widget types
    print("\n" + "=" * 80)
    print("WIDGET TYPES ANALYSIS")
    print("=" * 80)

    widget_types = analyze_widget_types(questions)
    sorted_widgets = sorted(widget_types.items(), key=lambda x: -x[1])

    print(f"\nWidget types found ({len(widget_types)} types):")
    for widget_type, count in sorted_widgets:
        print(f"  - {widget_type}: {count} occurrences")

    # Analyze question.content structure
    print("\n" + "=" * 80)
    print("QUESTION CONTENT STRUCTURE")
    print("=" * 80)

    question_fields = sorted([f for f in all_fields.keys() if f.startswith('question.')])
    for field in question_fields[:30]:  # Limit output
        types = ', '.join(all_fields[field])
        print(f"  - {field}: {types}")

    # Sample widget options by type
    print("\n" + "=" * 80)
    print("SAMPLE WIDGET OPTIONS BY TYPE")
    print("=" * 80)

    widget_samples = {}
    for q in questions:
        question = q.get('question', {})
        widgets = question.get('widgets', {})

        for widget_id, widget_data in widgets.items():
            widget_type = widget_data.get('type', 'unknown')
            if widget_type not in widget_samples:
                widget_samples[widget_type] = {
                    'options': widget_data.get('options', {}),
                    'sample_id': widget_id
                }

    for widget_type, sample in widget_samples.items():
        print(f"\n{widget_type}:")
        print(f"  Sample ID: {sample['sample_id']}")
        options = sample['options']
        if options:
            print("  Options fields:")
            for key in list(options.keys())[:10]:  # Limit to 10 fields
                value = options[key]
                value_type = type(value).__name__
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                elif isinstance(value, (list, dict)):
                    value_type = f"{value_type}[{len(value)}]"
                    value = "..."
                print(f"    - {key}: {value_type} = {value}")

    # Print a full sample question
    print("\n" + "=" * 80)
    print("SAMPLE FULL QUESTION (First question)")
    print("=" * 80)

    if questions:
        sample = questions[0]
        # Convert ObjectId to string for JSON serialization
        sample_copy = dict(sample)
        sample_copy['_id'] = str(sample_copy.get('_id', ''))
        print(json.dumps(sample_copy, indent=2, default=str)[:3000])
        if len(json.dumps(sample_copy, default=str)) > 3000:
            print("\n... (truncated)")

    # Analyze hints structure
    print("\n" + "=" * 80)
    print("HINTS STRUCTURE")
    print("=" * 80)

    hints_count = 0
    hints_with_widgets = 0
    for q in questions:
        hints = q.get('hints', [])
        if hints:
            hints_count += len(hints)
            for hint in hints:
                if hint.get('widgets'):
                    hints_with_widgets += 1

    print(f"Total hints across sample: {hints_count}")
    print(f"Hints with widgets: {hints_with_widgets}")

    # Analyze answerArea structure
    print("\n" + "=" * 80)
    print("ANSWER AREA STRUCTURE")
    print("=" * 80)

    answer_area_fields = sorted([f for f in all_fields.keys() if f.startswith('answerArea.')])
    for field in answer_area_fields[:20]:
        types = ', '.join(all_fields[field])
        print(f"  - {field}: {types}")

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
