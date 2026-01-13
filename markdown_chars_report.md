# Markdown Characters Analysis Report

## Summary

- **Questions with # or * in content:** 35,116
- **Questions with # or * in hints:** 9,844
- **Total unique questions affected:** 36,026

## Common Patterns Found

### 1. Bold Formatting (`**text**`)
Most frequent pattern - used for emphasis in questions:
- `**Which of the programs has the following output?**`
- `**Select the decimal that is equivalent to...**`
- `**Can you match the teacher's comments to...**`

### 2. Hash in Code Blocks (`#`)
Used for Python comments in code examples:
- ` ``` #print("Hello there.") ``` `
- Appears in programming questions

### 3. LaTeX Formatting
Some occurrences in mathematical expressions

## Recommendations

1. **For `**text**` patterns:** These should be converted to proper HTML `<strong>` tags or removed
2. **For `#` in code:** These are legitimate and should be preserved within code blocks
3. **Migration needed:** A cleanup script should distinguish between legitimate uses (code) and formatting that should be converted

## Next Steps

Options:
1. Create automated cleanup script to convert `**text**` to HTML
2. Generate detailed report of most problematic questions
3. Manual review of edge cases before bulk conversion
