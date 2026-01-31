#!/usr/bin/env python3
"""
Unit tests for tone_guidelines.py

Verifies that:
1. validate_tone() catches all banned patterns
2. BANNED_PHRASES list is comprehensive (no gaps with regex patterns)
3. Safe openers pass validation
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from content.tone_guidelines import validate_tone, BANNED_PHRASES


class TestBannedPhrases:
    """Test that all banned patterns are caught."""

    @pytest.mark.parametrize("phrase", [
        # "right" variants
        "right, so let me explain",
        "right so here's the deal",
        "right, let's do this",
        "right then, let's begin",
        # "okay" variants
        "okay, so you have 5 apples",
        "okay so there are some numbers",
        "okay, let's try this",
        "okay let's see",
        "okay, check this out",
        "okay check it out",
        "okay, here's the thing",
        "okay here's a puzzle",
        "okay this one is tricky",
        "okay this one's about fractions",
        "okay this is a fun one",
        "okay, try this one out",
        # "alright" variants
        "alright, so you have a rectangle",
        "alright so let me explain",
        "alright, let's dive in",
        "alright let's try",
        "alright, here's a question",
        "alright here's the thing",
        # "let's" patterns
        "let's dive in and learn",
        "let's get started with math",
        "let's see if you can solve this",
        "let's try something new",
        # Other formulaic patterns
        "can you figure out the answer?",
        "here's a head-scratcher for you",
        "here's a fun one!",
        "ready? here we go!",
        # Banned praise
        "Great job! You got it!",
        "Excellent! That's correct!",
        "Amazing! You're so smart!",
    ])
    def test_banned_phrases_caught(self, phrase):
        """Each banned phrase should be caught by validate_tone()."""
        violations = validate_tone(phrase)
        assert len(violations) > 0, f"Expected violation for: '{phrase}'"


class TestSafeOpeners:
    """Test that safe openers pass validation."""

    @pytest.mark.parametrize("opener", [
        # Safe openers that should pass
        "so there are some apples here. have a count.",
        "here we go. you've got 5 cookies.",
        "have a go at this. what's 3 + 2?",
        "try this. how many stars can you see?",
        "quick one. what shape is this?",
        "ooh, this is good. count the triangles.",
        # No opener at all
        "you've got 3 apples. someone nice gives you 2 more. how many now?",
        "there are 5 birds. 2 fly away. how many left?",
        # Gentle encouragement (allowed)
        "5 plus 7. go on, you know this one. (you've got this)",
        "count the shapes. (no rush, we'll wait)",
    ])
    def test_safe_openers_pass(self, opener):
        """Safe openers should pass validation with no violations."""
        violations = validate_tone(opener)
        assert len(violations) == 0, f"Unexpected violations for safe opener: '{opener}' -> {violations}"


class TestBannedPhrasesComprehensive:
    """Test that BANNED_PHRASES list covers all regex patterns."""

    def test_banned_phrases_includes_all_variants(self):
        """BANNED_PHRASES should include all key banned patterns."""
        # These are the critical patterns that must be in BANNED_PHRASES
        must_include = [
            "right, so",
            "okay, so",
            "alright, so",
            "okay, let's",
            "alright, let's",
            "let's dive in",
            "let's see if",
            "okay this one",
            "okay, here's",
            "alright, here's",
        ]
        
        banned_lower = [p.lower() for p in BANNED_PHRASES]
        
        for pattern in must_include:
            assert pattern.lower() in banned_lower, \
                f"Missing from BANNED_PHRASES: '{pattern}'"

    def test_validate_tone_empty_content(self):
        """Empty content should be flagged."""
        violations = validate_tone("")
        assert "empty content" in violations
        
        violations = validate_tone(None)
        assert "empty content" in violations


class TestEdgeCases:
    """Test edge cases and tricky patterns."""

    def test_case_insensitive(self):
        """Validation should be case-insensitive."""
        violations = validate_tone("OKAY, SO here's the thing")
        assert len(violations) > 0

        violations = validate_tone("Right, Let's Do This")
        assert len(violations) > 0

    def test_partial_match_in_sentence(self):
        """Banned phrases should be caught even mid-sentence."""
        violations = validate_tone("and then okay, so you have 5 apples")
        assert len(violations) > 0

    def test_legitimate_so_allowed(self):
        """'so' alone at start should be allowed (not 'okay, so')."""
        violations = validate_tone("so there are some apples here.")
        assert len(violations) == 0, f"'so' alone should be allowed: {violations}"

    def test_legitimate_here_we_go(self):
        """'here we go' is allowed, 'ready? here we go' is not."""
        # Allowed
        violations = validate_tone("here we go. count the apples.")
        assert len(violations) == 0, f"'here we go' should be allowed: {violations}"
        
        # Not allowed
        violations = validate_tone("ready? here we go!")
        assert len(violations) > 0, "'ready? here we go' should be banned"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
