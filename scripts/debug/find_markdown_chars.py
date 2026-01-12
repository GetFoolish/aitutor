"""
Find questions that contain # or * characters in their content.
These Markdown formatting characters should not appear in raw question text.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db

def find_questions_with_markdown_chars():
    """Find all questions containing # or * in their content."""
    
    print("Searching for questions with # or * characters...\n")
    
    # Search for questions with # or * in question content
    query = {
        '$or': [
            {'question.content': {'$regex': '#'}},
            {'question.content': {'$regex': '\\*'}}
        ]
    }
    
    questions = list(mongo_db.scraped_questions.find(query))
    
    print(f"Found {len(questions)} questions with # or * characters\n")
    print("=" * 80)
    
    for i, q in enumerate(questions, 1):
        question_id = q.get('_id', 'Unknown')
        slug = q.get('slug', 'No slug')
        content = q.get('question', {}).get('content', '')
        
        # Count occurrences
        hash_count = content.count('#')
        star_count = content.count('*')
        
        print(f"\n{i}. Question ID: {question_id}")
        print(f"   Slug: {slug}")
        print(f"   # count: {hash_count}")
        print(f"   * count: {star_count}")
        
        # Show snippet with the characters
        if hash_count > 0:
            # Find first occurrence of #
            idx = content.find('#')
            start = max(0, idx - 30)
            end = min(len(content), idx + 50)
            snippet = content[start:end].replace('\n', ' ')
            print(f"   # snippet: ...{snippet}...")
        
        if star_count > 0:
            # Find first occurrence of *
            idx = content.find('*')
            start = max(0, idx - 30)
            end = min(len(content), idx + 50)
            snippet = content[start:end].replace('\n', ' ')
            print(f"   * snippet: ...{snippet}...")
        
        print("-" * 80)
    
    # Also check hints
    print("\n\nChecking hints for # or * characters...\n")
    print("=" * 80)
    
    hint_query = {
        '$or': [
            {'hints.content': {'$regex': '#'}},
            {'hints.content': {'$regex': '\\*'}}
        ]
    }
    
    questions_with_hint_issues = list(mongo_db.scraped_questions.find(hint_query))
    
    print(f"Found {len(questions_with_hint_issues)} questions with # or * in hints\n")
    
    for i, q in enumerate(questions_with_hint_issues, 1):
        question_id = q.get('_id', 'Unknown')
        slug = q.get('slug', 'No slug')
        hints = q.get('hints', [])
        
        print(f"\n{i}. Question ID: {question_id}")
        print(f"   Slug: {slug}")
        
        for j, hint in enumerate(hints):
            hint_content = hint.get('content', '')
            hash_count = hint_content.count('#')
            star_count = hint_content.count('*')
            
            if hash_count > 0 or star_count > 0:
                print(f"   Hint {j+1}: # count: {hash_count}, * count: {star_count}")
        
        print("-" * 80)
    
    print(f"\n\nSummary:")
    print(f"Questions with # or * in content: {len(questions)}")
    print(f"Questions with # or * in hints: {len(questions_with_hint_issues)}")
    print(f"Total unique questions: {len(set([str(q['_id']) for q in questions + questions_with_hint_issues]))}")

if __name__ == "__main__":
    find_questions_with_markdown_chars()
