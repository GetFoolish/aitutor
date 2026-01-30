#!/usr/bin/env python3
"""
Example Retriever for Question Generation

Retrieves reference questions from LOCAL MongoDB (questions_unified)
for few-shot learning with LLM-based question generation.

Uses the consolidated questions_unified collection (41,886 questions)
as the single source of truth.
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables (supports running without run_tutor.sh)
load_dotenv()


@dataclass
class QuestionExample:
    """A question example for LLM prompting."""
    question_id: str
    widget_type: str
    content: str
    widget_options: Dict[str, Any]
    hints: List[str]
    full_question: Dict[str, Any]
    
    def to_prompt_format(self) -> str:
        """Format as a prompt example for LLM."""
        hints_text = "\n".join([f"  - {h}" for h in self.hints[:3]])
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


class ExampleRetriever:
    """
    Retrieves question examples from LOCAL MongoDB (questions_unified).
    
    Uses the consolidated collection as the single source of truth.
    """
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """Initialize with local MongoDB connection."""
        self.client = MongoClient(mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
        self.db = self.client["ai_tutor"]
        self.questions = self.db["questions_unified"]
        
        print(f"[ExampleRetriever] Connected to local MongoDB")
        print(f"[ExampleRetriever] questions_unified: {self.questions.count_documents({})} questions")
    
    def get_examples(
        self,
        widget_type: str = None,
        topic: str = None,
        num_examples: int = 3,
        exclude_ids: List[str] = None
    ) -> List[QuestionExample]:
        """
        Retrieve question examples from the database.
        
        Args:
            widget_type: Filter by widget type (radio, numeric-input, etc.)
            topic: Search for topic in question content
            num_examples: Number of examples to retrieve
            exclude_ids: Question IDs to exclude
            
        Returns:
            List of QuestionExample objects
        """
        query = {}
        
        if widget_type:
            query["widget_types"] = widget_type
        
        if exclude_ids:
            query["question_id"] = {"$nin": exclude_ids}
        
        # Get candidates
        candidates = list(self.questions.find(query).limit(500))
        
        # Filter by topic if specified
        if topic:
            topic_lower = topic.lower()
            filtered = []
            for doc in candidates:
                content = doc.get("question", {}).get("content", "")
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
        """
        examples = self.get_examples(
            widget_type=widget_type,
            topic=topic,
            num_examples=num_examples
        )
        
        if not examples:
            return "No relevant examples found in database."
        
        prompt_parts = ["REFERENCE EXAMPLES FROM DATABASE:\n"]
        
        for i, ex in enumerate(examples, 1):
            prompt_parts.append(f"--- Example {i} ---")
            prompt_parts.append(ex.to_prompt_format())
        
        prompt_parts.append("\nUse these as reference for the correct Perseus format structure.")
        
        return "\n".join(prompt_parts)
    
    def get_widget_schema(self, widget_type: str) -> Dict[str, Any]:
        """
        Get the schema/structure for a widget type based on real examples.
        """
        examples = self.get_examples(widget_type=widget_type, num_examples=5)
        
        if not examples:
            return {}
        
        # Analyze common options
        all_options_keys = set()
        for ex in examples:
            all_options_keys.update(ex.widget_options.keys())
        
        return {
            "widget_type": widget_type,
            "common_options": list(all_options_keys),
            "example_structure": examples[0].widget_options
        }
    
    def get_all_widget_types(self) -> Dict[str, int]:
        """Get count of all widget types in database."""
        pipeline = [
            {"$unwind": "$widget_types"},
            {"$group": {"_id": "$widget_types", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        results = list(self.questions.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results if r["_id"]}
    
    def _doc_to_example(self, doc: Dict, target_widget_type: str = None) -> Optional[QuestionExample]:
        """Convert a MongoDB document to QuestionExample."""
        try:
            question = doc.get("question", {})
            content = question.get("content", "")
            widgets = question.get("widgets", {})
            hints_raw = doc.get("hints", [])
            
            # Extract hints content
            hints = []
            for h in hints_raw:
                if isinstance(h, dict):
                    hints.append(h.get("content", ""))
                elif isinstance(h, str):
                    hints.append(h)
            
            # Find the target widget
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
                content=content[:500],
                widget_options=widget_options,
                hints=hints[:3],
                full_question=question
            )
            
        except Exception as e:
            print(f"Error converting doc: {e}")
            return None


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Retrieve question examples from local MongoDB")
    parser.add_argument("--widget", "-w", help="Widget type to filter by")
    parser.add_argument("--topic", "-t", help="Topic to search for")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of examples")
    parser.add_argument("--types", action="store_true", help="List all widget types")
    
    args = parser.parse_args()
    
    retriever = ExampleRetriever()
    
    if args.types:
        print("\nWidget Types in questions_unified:")
        for wtype, count in retriever.get_all_widget_types().items():
            print(f"  {wtype}: {count}")
    else:
        prompt = retriever.get_examples_for_prompt(
            widget_type=args.widget,
            topic=args.topic,
            num_examples=args.count
        )
        print(prompt)
