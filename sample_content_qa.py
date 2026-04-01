#!/usr/bin/env python3
"""
Sample-based Educational Content QA with Screenshots
Tests a subset of subject/age combinations with visual verification
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Sample test matrix (covering edge cases)
TEST_SAMPLES = [
    {"subject": "Math", "age": 5, "preset": True},
    {"subject": "Math", "age": 18, "preset": True},
    {"subject": "Science", "age": 8, "preset": True},
    {"subject": "English", "age": 13, "preset": True},
    {"subject": "Geography", "age": 10, "preset": False},
    {"subject": "Physics", "age": 15, "preset": False},
    {"subject": "Chemistry", "age": 8, "preset": False},
    {"subject": "Spanish", "age": 13, "preset": False},
    {"subject": "Biology", "age": 18, "preset": False},
    {"subject": "Music Theory", "age": 10, "preset": False},
]

screenshots_dir = Path("/Users/gaganarora/Desktop/my projects/aitutor/qa_screenshots")
screenshots_dir.mkdir(exist_ok=True)

results = []


async def test_sample(page, subject, age, is_preset):
    """Test one subject/age combination with screenshots"""
    print(f"\n Testing: {subject} (age {age})")

    result = {
        "subject": subject,
        "age": age,
        "screenshots": [],
        "issues": [],
        "load_time": 0,
        "questions_found": 0
    }

    try:
        # Navigate to dev-login
        await page.goto("http://localhost:5173/dev-login", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Take screenshot of dev-login
        screenshot_path = screenshots_dir / f"{subject}_{age}_01_devlogin.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        result["screenshots"].append(str(screenshot_path))
        print(f"  Screenshot: {screenshot_path.name}")

        # Select subject
        if is_preset:
            # Click preset button
            await page.click(f"button:has-text('{subject}')")
        else:
            # Fill custom input
            await page.fill("#custom-subject-input", subject)

        await page.wait_for_timeout(1000)

        # Take screenshot after subject selection
        screenshot_path = screenshots_dir / f"{subject}_{age}_02_subject_selected.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        result["screenshots"].append(str(screenshot_path))

        # Click age button
        start_time = asyncio.get_event_loop().time()
        await page.click(f"button:has-text('{age}')")
        print(f"  Clicked age {age}, waiting for assessment...")

        # Wait for navigation (increased timeout)
        try:
            await page.wait_for_url("**/assessment/**", timeout=20000)
        except:
            print(f"  Warning: Did not navigate to assessment URL")

        await page.wait_for_timeout(4000)  # Wait for question to load

        result["load_time"] = round(asyncio.get_event_loop().time() - start_time, 2)
        print(f"  Load time: {result['load_time']}s")

        # Take screenshot of first question
        screenshot_path = screenshots_dir / f"{subject}_{age}_03_question1.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        result["screenshots"].append(str(screenshot_path))

        # Get page content for analysis
        page_text = await page.inner_text("body")

        # Check for issues
        if "[[☃" in page_text:
            result["issues"].append("Unrendered widget found")
        if "lorem ipsum" in page_text.lower():
            result["issues"].append("Placeholder content detected")
        if "error" in page_text.lower() and "no error" not in page_text.lower():
            result["issues"].append("Error message visible")
        if "undefined" in page_text or "null" in page_text:
            result["issues"].append("Undefined/null values in content")

        # Check if question loaded
        if len(page_text.strip()) > 100:
            result["questions_found"] = 1
            print(f"  Question loaded ({len(page_text)} chars)")
        else:
            result["issues"].append("Question appears empty or too short")
            print(f"  Warning: Page content is very short ({len(page_text)} chars)")

        # Try to interact with question (submit an answer)
        try:
            # Look for answer choices
            choices = await page.query_selector_all("button[class*='choice'], li[role='button']")
            if len(choices) > 0:
                await choices[0].click()
                await page.wait_for_timeout(500)

                # Click submit
                submit_button = await page.query_selector("button:has-text('Submit')")
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_timeout(2000)

                    # Take screenshot of feedback
                    screenshot_path = screenshots_dir / f"{subject}_{age}_04_feedback.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    result["screenshots"].append(str(screenshot_path))

                    # Click next
                    next_button = await page.query_selector("button:has-text('Next')")
                    if next_button:
                        await next_button.click()
                        await page.wait_for_timeout(2000)

                        # Take screenshot of second question
                        screenshot_path = screenshots_dir / f"{subject}_{age}_05_question2.png"
                        await page.screenshot(path=str(screenshot_path), full_page=True)
                        result["screenshots"].append(str(screenshot_path))
                        result["questions_found"] = 2
                        print(f"  Successfully navigated to question 2")
        except Exception as e:
            print(f"  Could not navigate through questions: {str(e)}")

    except Exception as e:
        result["issues"].append(f"Test failed: {str(e)}")
        print(f"  ERROR: {str(e)}")

        # Take error screenshot
        try:
            screenshot_path = screenshots_dir / f"{subject}_{age}_ERROR.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            result["screenshots"].append(str(screenshot_path))
        except:
            pass

    return result


async def main():
    print("=" * 80)
    print("SAMPLE-BASED EDUCATIONAL CONTENT QA")
    print("=" * 80)
    print(f"Testing {len(TEST_SAMPLES)} subject/age combinations")
    print(f"Screenshots will be saved to: {screenshots_dir}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Non-headless for debugging
        context = await browser.new_context(viewport={"width": 1280, "height": 1024})
        page = await context.new_page()

        for i, sample in enumerate(TEST_SAMPLES, 1):
            print(f"\n[{i}/{len(TEST_SAMPLES)}]", end="")
            result = await test_sample(page, sample["subject"], sample["age"], sample["preset"])
            results.append(result)
            await page.wait_for_timeout(1000)

        await browser.close()

    # Save results
    results_file = screenshots_dir.parent / "educational_qa_sample_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "samples_tested": len(TEST_SAMPLES),
            "results": results
        }, f, indent=2)

    # Generate summary report
    generate_summary_report()


def generate_summary_report():
    """Generate summary report from sample tests"""
    report_path = "/Users/gaganarora/Desktop/my projects/aitutor/EDUCATIONAL_CONTENT_QA.md"

    total_issues = sum(len(r["issues"]) for r in results)
    tests_with_issues = sum(1 for r in results if r["issues"])
    total_questions = sum(r["questions_found"] for r in results)
    avg_load_time = sum(r["load_time"] for r in results) / len(results) if results else 0

    report = f"""# Educational Content QA Report (Sample-Based)

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Testing Method:** Sample-based with visual verification (10 subject/age combinations)

## Executive Summary

- **Samples Tested:** {len(results)}
- **Tests with Issues:** {tests_with_issues} ({100*tests_with_issues//len(results) if len(results) else 0}%)
- **Total Issues Found:** {total_issues}
- **Questions Successfully Loaded:** {total_questions}/{len(results)*2} expected
- **Average Load Time:** {avg_load_time:.2f}s

### Key Findings

"""

    if total_questions < len(results):
        report += f"- **CRITICAL:** Only {total_questions}/{len(results)} tests could load questions\n"
    if avg_load_time > 8:
        report += f"- **PERFORMANCE:** Average load time {avg_load_time:.2f}s exceeds 8s threshold\n"
    if total_issues > 0:
        report += f"- **QUALITY:** {total_issues} content or technical issues detected\n"

    report += """
---

## Sample Test Results

"""

    for result in results:
        status = "✅" if not result["issues"] else "❌"
        report += f"\n### {status} {result['subject']} (Age {result['age']})\n\n"
        report += f"- **Load Time:** {result['load_time']}s\n"
        report += f"- **Questions Found:** {result['questions_found']}\n"
        report += f"- **Screenshots:** {len(result['screenshots'])}\n"

        if result["issues"]:
            report += f"\n**Issues:**\n"
            for issue in result["issues"]:
                report += f"- {issue}\n"

        report += f"\n**Screenshots:**\n"
        for screenshot in result["screenshots"]:
            filename = Path(screenshot).name
            report += f"- `{filename}`\n"

        report += "\n"

    report += f"""
---

## Screenshots Location

All screenshots saved to:
```
{screenshots_dir}
```

### Screenshot Naming Convention

- `[Subject]_[Age]_01_devlogin.png` - Dev login page
- `[Subject]_[Age]_02_subject_selected.png` - After subject selection
- `[Subject]_[Age]_03_question1.png` - First question loaded
- `[Subject]_[Age]_04_feedback.png` - Answer feedback
- `[Subject]_[Age]_05_question2.png` - Second question
- `[Subject]_[Age]_ERROR.png` - Error state (if encountered)

---

## Recommendations

1. **Review Screenshots:** Manually inspect all screenshots for:
   - Age-appropriate content and vocabulary
   - Proper widget rendering
   - Clean UI without errors
   - Appropriate question difficulty

2. **Performance:** If load times >8s, investigate:
   - Question generation delays
   - API response times
   - Database query optimization

3. **Content Quality:** For any issues found:
   - Fix placeholder content
   - Ensure widgets render properly
   - Validate answer choices are sensible

4. **Expand Testing:** After fixing issues, run full 60-combination automated test

---

## Next Steps

1. Open screenshot directory and review all images
2. Note any visual issues not caught by automated checks
3. Fix critical issues (question loading, performance)
4. Re-run this sample test to verify fixes
5. Run full 60-combination suite once samples pass
"""

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n\nReport saved to: {report_path}")
    print(f"Screenshots saved to: {screenshots_dir}")
    print(f"\nTo review:")
    print(f"  open {screenshots_dir}")


if __name__ == "__main__":
    asyncio.run(main())
