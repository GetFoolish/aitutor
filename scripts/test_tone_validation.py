#!/usr/bin/env python3
"""
Test script to verify tone validation catches problematic phrases.
Run: python scripts/test_tone_validation.py
"""
import sys
from pathlib import Path

# Add content directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "content"))

from tone_guidelines import validate_tone, BANNED_PHRASES

# Test cases: phrases that SHOULD be rejected
SHOULD_FAIL = [
    # Exact failures from the reviewer
    "okay, let's dive in! here's a question for you.",
    "right, so imagine you have some apples.",
    "alright, here's the thing about fractions.",
    "okay, so here's a head-scratcher for you.",
    
    # Other banned patterns
    "right then, let's count some apples.",
    "okay this is a fun one! count the stars.",
    "okay, try this one for size.",
    "let's see if you can figure this out.",
    "can you figure out the answer?",
    "Great job! Now try this next one.",
    "Excellent! You're doing amazing.",
    "Amazing! Keep up the good work.",
    
    # More subtle variants
    "okay so here we go with adding.",
    "alright so you've got 3 apples.",
    "right, let's start with counting.",
    "let's dive in and see what we can do.",
    "let's try this math problem.",
    "let's get started with subtraction.",
    "here's a fun one about shapes.",
    "ready? here we go with fractions!",
]

# Test cases: phrases that SHOULD pass
SHOULD_PASS = [
    "so there are some apples here. have a count.",
    "you've got 3 apples. someone nice gives you 2 more. how many now?",
    "here we go. count the stars and let us know.",
    "quick one. 5 plus 7. go on, you know this one.",
    "have a go at this. what's 8 minus 3?",
    "ooh, this is good. how many cookies are left?",
    "try this. you've got 4 groups of 3. what's the total?",
    "5 plus 7. go on, you know this one. (you've got this)",
    "count the shapes. take your time, no rush.",
]

def test_tone_validation():
    print("=" * 60)
    print("TONE VALIDATION TEST")
    print("=" * 60)
    
    print(f"\nBanned phrases list ({len(BANNED_PHRASES)} items):")
    for phrase in BANNED_PHRASES:
        print(f"  • {phrase}")
    
    print("\n" + "-" * 60)
    print("SHOULD FAIL (must have violations):")
    print("-" * 60)
    
    failed_to_catch = []
    for phrase in SHOULD_FAIL:
        violations = validate_tone(phrase)
        if violations:
            print(f"✅ CAUGHT: \"{phrase[:50]}...\"")
            print(f"   → {violations[0]}")
        else:
            print(f"❌ MISSED: \"{phrase[:50]}...\"")
            failed_to_catch.append(phrase)
    
    print("\n" + "-" * 60)
    print("SHOULD PASS (must have no violations):")
    print("-" * 60)
    
    false_positives = []
    for phrase in SHOULD_PASS:
        violations = validate_tone(phrase)
        if not violations:
            print(f"✅ PASSED: \"{phrase[:50]}...\"")
        else:
            print(f"❌ FALSE POSITIVE: \"{phrase[:50]}...\"")
            print(f"   → {violations}")
            false_positives.append((phrase, violations))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if failed_to_catch:
        print(f"\n❌ FAILED TO CATCH ({len(failed_to_catch)} phrases):")
        for phrase in failed_to_catch:
            print(f"   • {phrase[:60]}")
    else:
        print("\n✅ All bad phrases caught correctly!")
    
    if false_positives:
        print(f"\n❌ FALSE POSITIVES ({len(false_positives)} phrases):")
        for phrase, violations in false_positives:
            print(f"   • {phrase[:60]} → {violations}")
    else:
        print("✅ No false positives!")
    
    total_issues = len(failed_to_catch) + len(false_positives)
    if total_issues == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️ {total_issues} issues found")
        return False

if __name__ == "__main__":
    success = test_tone_validation()
    sys.exit(0 if success else 1)
