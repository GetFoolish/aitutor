#!/usr/bin/env python3
"""
CORRECTED Educational Content QA - Ready to Run
Uses correct /app/dev-login route
Tests 10 sample subject/age combinations with screenshots
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Sample test matrix
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

screenshots_dir = Path("/Users/gaganarora/Desktop/my projects/aitutor/qa_screenshots_final")
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
        # CORRECTED: Navigate to /app/dev-login (not /dev-login)
        await page.goto("http://localhost:5173/app/dev-login", wait_until="domcontentloaded")
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

        # Wait for navigation
        try:
            await page.wait_for_url("**/assessment/**", timeout=20000)
        except:
            print(f"  Warning: Did not navigate to assessment URL")

        await page.wait_for_timeout(4000)

        result["load_time"] = round(asyncio.get_event_loop().time() - start_time, 2)
        print(f"  Load time: {result['load_time']}s")

        # Take screenshot of first question
        screenshot_path = screenshots_dir / f"{subject}_{age}_03_question1.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        result["screenshots"].append(str(screenshot_path))

        # Get page content
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

        # Try to interact with question
        try:
            choices = await page.query_selector_all("button[class*='choice'], li[role='button']")
            if len(choices) > 0:
                await choices[0].click()
                await page.wait_for_timeout(500)

                submit_button = await page.query_selector("button:has-text('Submit')")
                if submit_button:
                    await submit_button.click()
                    await page.wait_for_timeout(2000)

                    # Take screenshot of feedback
                    screenshot_path = screenshots_dir / f"{subject}_{age}_04_feedback.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    result["screenshots"].append(str(screenshot_path))

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

        try:
            screenshot_path = screenshots_dir / f"{subject}_{age}_ERROR.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            result["screenshots"].append(str(screenshot_path))
        except:
            pass

    return result


async def main():
    print("=" * 80)
    print("EDUCATIONAL CONTENT QA - CORRECTED VERSION")
    print("=" * 80)
    print(f"Testing {len(TEST_SAMPLES)} subject/age combinations")
    print(f"Screenshots will be saved to: {screenshots_dir}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 1024})
        page = await context.new_page()

        for i, sample in enumerate(TEST_SAMPLES, 1):
            print(f"\n[{i}/{len(TEST_SAMPLES)}]", end="")
            result = await test_sample(page, sample["subject"], sample["age"], sample["preset"])
            results.append(result)
            await page.wait_for_timeout(1000)

        await browser.close()

    # Save results
    results_file = screenshots_dir.parent / "educational_qa_final_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "samples_tested": len(TEST_SAMPLES),
            "results": results
        }, f, indent=2)

    print(f"\n\nResults saved to: {results_file}")
    print(f"Screenshots saved to: {screenshots_dir}")

    # Generate summary
    total_issues = sum(len(r["issues"]) for r in results)
    tests_with_issues = sum(1 for r in results if r["issues"])
    total_questions = sum(r["questions_found"] for r in results)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests run: {len(results)}")
    print(f"Tests with issues: {tests_with_issues}/{len(results)}")
    print(f"Total issues: {total_issues}")
    print(f"Questions loaded: {total_questions}/{len(results)*2}")
    print(f"\nTo review screenshots:")
    print(f"  open {screenshots_dir}")


if __name__ == "__main__":
    asyncio.run(main())
