#!/usr/bin/env python3
"""
Example Retriever for Question Generation

Retrieves relevant scraped questions from MongoDB to use as few-shot examples
for LLM-based question generation. Improves quality by showing real Perseus format.

Usage:
    from example_retriever import ExampleRetriever
    
    retriever = ExampleRetriever()
    examples = retriever.get_examples(
        widget_type="radio",
        topic="counting",
        difficulty="easy",
        num_examples=3
    )
"""

import os
import sys
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient


@dataclass
class QuestionExample:
    """A question example for LLM prompting."""
    question_id: str
    widget_type: str
    content: str
    widget_options: Dict[str, Any]
    hints: List[str]
    full_perseus: Dict[str, Any]
    
    def to_prompt_format(self) -> str:
        """Format as a prompt example for LLM."""
        hints_text = "\n".join([f"  - {h}" for h in self.hints[:3]])
        
        # Simplify widget options for prompt
        options_simplified = json.dumps(self.widget_options, indent=2)
        
        return f"""
Example Question ({self.widget_type}):
Content: {self.content}
Widget Type: {self.widget_type}
Widget Options:
{options_simplified}
Hints:
{hints_text}
"""
    
    def to_full_json(self) -> str:
        """Return full Perseus JSON for reference."""
        return json.dumps(self.full_perseus, indent=2)


class ExampleRetriever:
    """Retrieves relevant question examples from MongoDB for LLM prompting."""
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize with MongoDB connection."""
        self.uri = mongodb_uri or os.getenv("MONGODB_URI")
        if not self.uri:
            raise ValueError("MONGODB_URI not set")
        
        self.client = MongoClient(self.uri)
        self.questions_db = self.client["questions_db"]
        self.questions = self.questions_db["questions"]
        
    def get_examples(
        self,
        widget_type: str = None,
        topic: str = None,
        difficulty: str = None,
        grade_level: int = None,
        num_examples: int = 3,
        exclude_ids: List[str] = None
    ) -> List[QuestionExample]:
        """
        Retrieve relevant question examples from the database.
        
        Args:
            widget_type: Type of widget (radio, numeric-input, orderer, etc.)
            topic: Topic/subject keyword to search for
            difficulty: easy, medium, hard
            grade_level: Grade level (1-12)
            num_examples: Number of examples to retrieve
            exclude_ids: Question IDs to exclude
            
        Returns:
            List of QuestionExample objects
        """
        # Build query
        query = {}
        
        if widget_type:
            # Find questions with this widget type
            query[f"perseus_json.question.widgets"] = {"$exists": True}
        
        if exclude_ids:
            query["question_id"] = {"$nin": exclude_ids}
        
        # Get candidates
        candidates = list(self.questions.find(query).limit(500))
        
        # Filter by widget type if specified
        if widget_type:
            filtered = []
            for doc in candidates:
                widgets = doc.get("perseus_json", {}).get("question", {}).get("widgets", {})
                for wid, w in widgets.items():
                    if w.get("type") == widget_type:
                        filtered.append(doc)
                        break
            candidates = filtered
        
        # Filter by topic if specified (search in content)
        if topic:
            topic_lower = topic.lower()
            filtered = []
            for doc in candidates:
                content = doc.get("perseus_json", {}).get("question", {}).get("content", "")
                if topic_lower in content.lower():
                    filtered.append(doc)
            candidates = filtered if filtered else candidates[:num_examples * 2]
        
        # Convert to QuestionExample objects
        examples = []
        for doc in candidates[:num_examples]:
            example = self._doc_to_example(doc, widget_type)
            if example:
                examples.append(example)
        
        return examples
    
    def get_examples_by_widget_type(self, widget_type: str, num_examples: int = 3) -> List[QuestionExample]:
        """Get examples of a specific widget type."""
        return self.get_examples(widget_type=widget_type, num_examples=num_examples)
    
    def get_examples_for_prompt(
        self,
        widget_type: str = None,
        topic: str = None,
        num_examples: int = 2
    ) -> str:
        """
        Get formatted examples ready for LLM prompt injection.
        
        Returns a string with examples formatted for few-shot learning.
        """
        examples = self.get_examples(
            widget_type=widget_type,
            topic=topic,
            num_examples=num_examples
        )
        
        if not examples:
            return "No relevant examples found in database."
        
        prompt_parts = ["Here are real examples from our question database:\n"]
        
        for i, ex in enumerate(examples, 1):
            prompt_parts.append(f"--- Example {i} ---")
            prompt_parts.append(ex.to_prompt_format())
        
        prompt_parts.append("\nUse these as reference for the correct Perseus format structure.")
        
        return "\n".join(prompt_parts)
    
    def get_widget_type_schema(self, widget_type: str) -> Dict[str, Any]:
        """
        Get the schema/structure for a widget type based on real examples.
        
        Returns the common structure found in database examples.
        """
        examples = self.get_examples(widget_type=widget_type, num_examples=5)
        
        if not examples:
            return {}
        
        # Analyze common options across examples
        all_options_keys = set()
        for ex in examples:
            all_options_keys.update(ex.widget_options.keys())
        
        # Get a representative example
        representative = examples[0].widget_options
        
        return {
            "widget_type": widget_type,
            "common_options": list(all_options_keys),
            "example_structure": representative
        }
    
    def _doc_to_example(self, doc: Dict, target_widget_type: str = None) -> Optional[QuestionExample]:
        """Convert a MongoDB document to QuestionExample."""
        try:
            perseus = doc.get("perseus_json", {})
            question = perseus.get("question", {})
            content = question.get("content", "")
            widgets = question.get("widgets", {})
            hints_raw = perseus.get("hints", [])
            
            # Extract hints content
            hints = []
            for h in hints_raw:
                if isinstance(h, dict):
                    hints.append(h.get("content", ""))
                elif isinstance(h, str):
                    hints.append(h)
            
            # Find the target widget or first widget
            widget_type = None
            widget_options = {}
            
            for wid, w in widgets.items():
                wtype = w.get("type", "")
                if target_widget_type and wtype == target_widget_type:
                    widget_type = wtype
                    widget_options = w.get("options", {})
                    break
                elif not target_widget_type and not widget_type:
                    widget_type = wtype
                    widget_options = w.get("options", {})
            
            if not widget_type:
                return None
            
            return QuestionExample(
                question_id=doc.get("question_id", ""),
                widget_type=widget_type,
                content=content[:500],  # Truncate for prompt efficiency
                widget_options=widget_options,
                hints=hints[:3],  # Limit hints
                full_perseus=perseus
            )
            
        except Exception as e:
            print(f"Error converting doc: {e}")
            return None
    
    def get_all_widget_types(self) -> Dict[str, int]:
        """Get count of all widget types in database."""
        from collections import Counter
        
        widget_counts = Counter()
        
        for doc in self.questions.find({}).limit(5000):
            widgets = doc.get("perseus_json", {}).get("question", {}).get("widgets", {})
            for wid, w in widgets.items():
                widget_counts[w.get("type", "unknown")] += 1
        
        return dict(widget_counts.most_common())


def generate_question_with_examples(
    prompt: str,
    widget_type: str,
    topic: str = None,
    num_examples: int = 2
) -> str:
    """
    Generate a prompt with database examples for LLM question generation.
    
    Args:
        prompt: The user's generation prompt
        widget_type: Target widget type
        topic: Optional topic filter
        num_examples: Number of examples to include
        
    Returns:
        Enhanced prompt with real examples
    """
    retriever = ExampleRetriever()
    
    # Get relevant examples
    examples_prompt = retriever.get_examples_for_prompt(
        widget_type=widget_type,
        topic=topic,
        num_examples=num_examples
    )
    
    # Get widget schema
    schema = retriever.get_widget_type_schema(widget_type)
    schema_json = json.dumps(schema, indent=2)
    
    enhanced_prompt = f"""
{examples_prompt}

Widget Type Schema for {widget_type}:
{schema_json}

---
USER REQUEST:
{prompt}

IMPORTANT: Generate questions in the exact Perseus format shown in the examples above.
Ensure 'options' is always an OBJECT (not an array) containing the widget-specific properties.
"""
    
    return enhanced_prompt


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Retrieve question examples from database")
    parser.add_argument("--widget", "-w", help="Widget type to filter by")
    parser.add_argument("--topic", "-t", help="Topic to search for")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of examples")
    parser.add_argument("--schema", "-s", action="store_true", help="Show widget schema")
    parser.add_argument("--types", action="store_true", help="List all widget types")
    
    args = parser.parse_args()
    
    retriever = ExampleRetriever()
    
    if args.types:
        print("Widget Types in Database:")
        for wtype, count in retriever.get_all_widget_types().items():
            print(f"  {wtype}: {count}")
    elif args.schema and args.widget:
        schema = retriever.get_widget_type_schema(args.widget)
        print(json.dumps(schema, indent=2))
    else:
        prompt = retriever.get_examples_for_prompt(
            widget_type=args.widget,
            topic=args.topic,
            num_examples=args.count
        )
        print(prompt)
