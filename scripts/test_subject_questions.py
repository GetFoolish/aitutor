#!/usr/bin/env python3
"""
Sanity check script for subject-specific question generation.

Tests that:
1. Science subject returns science-appropriate questions (not math)
2. Computer Science subject returns coding-appropriate questions (not math)
3. Questions use conceptual widgets (radio/dropdown) for non-math subjects
4. Question text is not dominated by arithmetic operators

Usage:
    python scripts/test_subject_questions.py
    
    # With custom API URL
    DASH_API_URL=http://localhost:8000 python scripts/test_subject_questions.py
"""

import os
import re
import sys
import json
import requests
from typing import List, Dict, Tuple

API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")

# Arithmetic patterns that suggest math-style questions
ARITHMETIC_PATTERNS = [
    r'\b\d+\s*[\+\-\*\/\×\÷]\s*\d+\b',  # 5 + 3, 10 * 2, etc.
    r'\bhow many\b.*\b(total|altogether|in all)\b',  # "how many total"
    r'\bwhat is\b.*\b\d+\s*[\+\-\*\/]\b',  # "what is 5 +"
    r'\bcalculate\b',
    r'\bcompute\b',
    r'\bsolve.*equation\b',
    r'\b\d+\s*=\s*\d+\s*[\+\-\*\/]\b',  # 10 = 5 + ?
]

# Conceptual widgets that are appropriate for non-math subjects
CONCEPTUAL_WIDGETS = {"radio", "dropdown", "orderer"}


def check_arithmetic_heavy(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text is dominated by arithmetic patterns.
    Returns (is_arithmetic_heavy, matched_patterns).
    """
    text_lower = text.lower()
    matches = []
    
    for pattern in ARITHMETIC_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matches.append(pattern)
    
    # Consider it arithmetic-heavy if 2+ patterns match
    return len(matches) >= 2, matches


def test_subject(subject: str, expected_subject: str, grade: str = "3-5") -> Dict:
    """
    Test question generation for a subject.
    
    Returns dict with test results.
    """
    print(f"\n{'='*60}")
    print(f"Testing subject: {subject}")
    print(f"{'='*60}")
    
    result = {
        "subject": subject,
        "expected_subject": expected_subject,
        "passed": True,
        "errors": [],
        "warnings": [],
        "questions": []
    }
    
    try:
        # Call the API
        response = requests.post(
            f"{API_URL}/api/assessment/dynamic/start",
            json={
                "age_range": "8-10",
                "grade": grade,
                "subject": subject,
                "topics": [],  # Let it use defaults
                "question_count": 3,  # Just test a few
            },
            headers={"Content-Type": "application/json"},
            timeout=60  # Generation can take time
        )
        
        if response.status_code != 200:
            result["passed"] = False
            result["errors"].append(f"API returned {response.status_code}: {response.text[:200]}")
            return result
        
        data = response.json()
        questions = data.get("questions", [])
        
        if not questions:
            result["passed"] = False
            result["errors"].append("No questions returned")
            return result
        
        print(f"Received {len(questions)} questions")
        
        # Check each question
        for i, q in enumerate(questions):
            q_result = {"index": i, "issues": []}
            
            # Get question content
            content = q.get("question", {}).get("content", "")
            widgets = q.get("question", {}).get("widgets", {})
            metadata = q.get("dash_metadata", {})
            q_subject = metadata.get("subject", "")
            
            print(f"\nQ{i+1}: {content[:80]}...")
            print(f"     Subject in metadata: {q_subject}")
            
            # Check 1: Subject in metadata matches expected
            if q_subject != expected_subject:
                q_result["issues"].append(f"Wrong subject in metadata: got '{q_subject}', expected '{expected_subject}'")
                result["passed"] = False
            
            # Check 2: Widget types (for non-math, should be conceptual)
            if expected_subject != "math":
                widget_types = [w.get("type") for w in widgets.values() if isinstance(w, dict)]
                print(f"     Widget types: {widget_types}")
                
                non_conceptual = [wt for wt in widget_types if wt and wt not in CONCEPTUAL_WIDGETS]
                if non_conceptual:
                    q_result["issues"].append(f"Non-conceptual widgets for {expected_subject}: {non_conceptual}")
                    result["warnings"].append(f"Q{i+1} uses non-conceptual widgets: {non_conceptual}")
            
            # Check 3: Arithmetic patterns in content
            is_arithmetic, patterns = check_arithmetic_heavy(content)
            if is_arithmetic and expected_subject != "math":
                q_result["issues"].append(f"Arithmetic-heavy content for {expected_subject} subject")
                result["warnings"].append(f"Q{i+1} may be too arithmetic-focused")
                print(f"     ⚠️  Arithmetic patterns detected: {patterns[:2]}")
            
            result["questions"].append(q_result)
            
            if q_result["issues"]:
                for issue in q_result["issues"]:
                    print(f"     ❌ {issue}")
            else:
                print(f"     ✓ Looks good")
        
    except requests.exceptions.ConnectionError:
        result["passed"] = False
        result["errors"].append(f"Cannot connect to API at {API_URL}")
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Error: {str(e)}")
    
    return result


def main():
    print("=" * 60)
    print("SUBJECT-SPECIFIC QUESTION GENERATION TEST")
    print(f"API URL: {API_URL}")
    print("=" * 60)
    
    results = []
    
    # Test Science
    results.append(test_subject("science", "science"))
    
    # Test Computer Science (various input forms)
    results.append(test_subject("computer_science", "computer_science"))
    results.append(test_subject("coding", "computer_science"))
    results.append(test_subject("tech", "computer_science"))
    
    # Test Reading
    results.append(test_subject("reading", "reading"))
    
    # Test Math (baseline - should still work)
    results.append(test_subject("math", "math"))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for r in results:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(f"{status}: {r['subject']} → {r['expected_subject']}")
        
        if r["errors"]:
            for err in r["errors"]:
                print(f"       Error: {err}")
        if r["warnings"]:
            for warn in r["warnings"]:
                print(f"       Warning: {warn}")
        
        if not r["passed"]:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
