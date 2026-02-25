# Image Generation Issue

## Bug #2: Missing Images on Questions

**Reported:** Q3 "How many apples" and Q9 "How many blue birds" had no images

## Current Status

Image generation is configured but may fail silently when:
1. Image generation takes too long (timeout)
2. Gemini image model quota exceeded
3. Image URL is broken or file not saved

## Settings

- `IMAGE_PROBABILITY=0.10` (10% of questions get images)
- `IMAGE_TOPIC_KEYWORDS` in content_v1.py boosts probability for visual topics
- Images saved to `static/images/` with SHA-256 hash names

## Investigation Needed

Need to check:
1. Are images being generated but not rendering?
2. Are generation failures being logged?
3. Are image URLs correct?

## Temporary Workaround

Questions that reference images but don't have them are unanswerable.
Consider:
- Rejecting questions with image references but no image widget
- Adding fallback text descriptions
- Increasing generation timeout
