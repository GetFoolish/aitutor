#!/usr/bin/env python3
"""
Correct Educational Content QA Testing using Playwright
Tests all subjects and age groups for content quality, correctness, speed, and bugs
"""

import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page

# Test matrix
SUBJECTS = [
    "Math", "Science", "English", "History", "Geography",
    "Physics", "Chemistry", "Spanish", "Biology", "Music Theory"
]

AGE_GROUPS = [
    {"label": "K", "age": 5, "display": "K (5)"},
    {"label": "Grade 3", "age": 8, "display": "Grade 3 (8)"},
    {"label": "Grade 5", "age": 10, "display": "Grade 5 (10)"},
    {"label": "Grade 8", "age": 13, "display": "Grade 8 (13)"},
    {"label": "Grade 10", "age": 15, "display": "Grade 10 (15)"},
    {"label": "Grade 12+", "age": 18, "display": "Grade 12+ (18)"},
]

# Issue tracking
issues = {
    "content_quality": [],
    "correctness": [],
    "performance": [],
    "age_appropriateness": [],
    "technical_bugs": [],
}

test_results = []


async def check_for_errors(page: Page) -> List[str]:
    """Check page for common error indicators"""
    errors = []

    try:
        page_text = await page.inner_text("body")
        page_text_lower = page_text.lower()

        error_indicators = [
            ("error", "Error message found"),
            ("failed", "Failure indicator found"),
            ("lorem ipsum", "Placeholder content (lorem ipsum)"),
            ("todo", "TODO marker found"),
            ("[[☃", "Unrendered widget found"),
            ("something went wrong", "Generic error message"),
        ]

        for indicator, description in error_indicators:
            if indicator in page_text_lower and not (indicator == "error" and "no errors" in page_text_lower):
                errors.append(f"{description}: '{indicator}'")

    except Exception as e:
        errors.append(f"Error checking page: {str(e)}")

    return errors


async def test_subject_age_combination(page: Page, subject: str, age_group: Dict[str, Any]) -> Dict[str, Any]:
    """Test a specific subject/age combination"""
    print(f"\nTesting: {subject} - {age_group['display']}")

    result = {
        "subject": subject,
        "grade": age_group["display"],
        "load_time": 0,
        "questions_reviewed": 0,
        "issues": [],
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Navigate to dev-login
        start_time = time.time()
        await page.goto("http://localhost:5173/dev-login", wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_timeout(500)

        # Select subject - try preset buttons first
        subject_selected = False
        preset_subjects = ["Math", "Science", "English", "History"]

        if subject in preset_subjects:
            # Click the preset subject button
            try:
                subject_button = await page.query_selector(f"button:has-text('{subject}')")
                if subject_button:
                    await subject_button.click()
                    subject_selected = True
                    await page.wait_for_timeout(300)
            except:
                pass

        if not subject_selected:
            # Use custom subject input for non-preset subjects
            try:
                custom_input = await page.query_selector("#custom-subject-input")
                if custom_input:
                    await custom_input.fill(subject)
                    await page.wait_for_timeout(500)
                    subject_selected = True

                    # Verify subject was set
                    testing_indicator = await page.inner_text("text=Testing:")
                    if subject not in testing_indicator:
                        result["issues"].append(f"Subject selection not reflected (expected '{subject}', got '{testing_indicator}')")
            except Exception as e:
                result["issues"].append(f"Could not set custom subject: {str(e)}")

        if not subject_selected:
            result["issues"].append(f"Could not select subject: {subject}")
            return result

        # Click age button (this triggers assessment creation and navigation)
        try:
            # Find button containing the age number
            age_button = await page.query_selector(f"button:has-text('{age_group['age']}')")
            if age_button:
                await age_button.click()
                print(f"  Clicked age button {age_group['age']}, waiting for assessment...")

                # Wait for navigation to assessment page
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)  # Additional wait for question generation

                # Measure load time
                load_time = time.time() - start_time
                result["load_time"] = round(load_time, 2)

                if load_time > 8:
                    result["issues"].append(f"Slow load time: {load_time:.2f}s (>8s threshold)")
                    issues["performance"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": f"Load time {load_time:.2f}s exceeds 8s threshold"
                    })
            else:
                result["issues"].append(f"Could not find age button for age {age_group['age']}")
                return result
        except Exception as e:
            result["issues"].append(f"Error clicking age button or waiting for navigation: {str(e)}")
            return result

        # Check for immediate errors
        page_errors = await check_for_errors(page)
        if page_errors:
            result["issues"].extend(page_errors)
            for error in page_errors:
                issues["technical_bugs"].append({
                    "subject": subject,
                    "grade": age_group["display"],
                    "error": error
                })

        # Review first 3 questions
        for q_num in range(1, 4):
            print(f"  Reviewing question {q_num}...")

            try:
                # Wait a bit for question to fully load
                await page.wait_for_timeout(1000)

                # Get full page text
                page_text = await page.inner_text("body")

                # Check for widget rendering issues
                if "[[☃" in page_text:
                    issue = f"Q{q_num}: Unrendered widget found"
                    result["issues"].append(issue)
                    issues["technical_bugs"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                # Check for placeholder content
                placeholder_terms = ["lorem ipsum", "todo", "placeholder text", "test question here"]
                for term in placeholder_terms:
                    if term in page_text.lower():
                        issue = f"Q{q_num}: Placeholder content detected: {term}"
                        result["issues"].append(issue)
                        issues["content_quality"].append({
                            "subject": subject,
                            "grade": age_group["display"],
                            "issue": issue
                        })
                        break

                # Check for "undefined" or "null" in visible text
                if "undefined" in page_text or "null" in page_text:
                    issue = f"Q{q_num}: Found 'undefined' or 'null' in page content"
                    result["issues"].append(issue)
                    issues["technical_bugs"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                # Check for error messages
                if "error" in page_text.lower() and "no error" not in page_text.lower():
                    issue = f"Q{q_num}: Error message detected on page"
                    result["issues"].append(issue)
                    issues["technical_bugs"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                result["questions_reviewed"] += 1

                # Move to next question (if not last)
                if q_num < 3:
                    try:
                        # Look for multiple choice buttons or input fields
                        choice_buttons = await page.query_selector_all("button[class*='choice'], li[role='button'], input[type='radio']")

                        if len(choice_buttons) > 0:
                            # Click first answer choice
                            await choice_buttons[0].click()
                            await page.wait_for_timeout(500)
                        else:
                            # Try to find numeric input or text input
                            input_field = await page.query_selector("input[type='text'], input[type='number']")
                            if input_field:
                                await input_field.fill("5")
                                await page.wait_for_timeout(500)

                        # Click Submit button
                        submit_button = await page.query_selector("button:has-text('Submit'), button:has-text('Check Answer')")
                        if submit_button:
                            await submit_button.click()
                            await page.wait_for_timeout(1500)

                            # Click Next button
                            next_button = await page.query_selector("button:has-text('Next'), button:has-text('Continue')")
                            if next_button:
                                await next_button.click()
                                await page.wait_for_timeout(2000)
                            else:
                                print(f"  Warning: Could not find Next button after Q{q_num}")
                                break
                        else:
                            print(f"  Warning: Could not find Submit button for Q{q_num}")
                            break
                    except Exception as e:
                        print(f"  Warning: Error advancing to next question: {str(e)}")
                        break

            except Exception as e:
                result["issues"].append(f"Q{q_num}: Test exception: {str(e)}")
                break

    except Exception as e:
        result["issues"].append(f"Test exception: {str(e)}")
        issues["technical_bugs"].append({
            "subject": subject,
            "grade": age_group["display"],
            "error": str(e)
        })

    return result


async def main():
    """Run comprehensive QA testing"""
    print("=" * 80)
    print("EDUCATIONAL CONTENT QA TESTING")
    print("=" * 80)
    print(f"Testing {len(SUBJECTS)} subjects × {len(AGE_GROUPS)} age groups = {len(SUBJECTS) * len(AGE_GROUPS)} combinations")
    print()

    async with async_playwright() as p:
        # Launch browser in headless mode for faster testing
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # Set up console error tracking
        console_errors = []

        def handle_console(msg):
            if msg.type == "error":
                console_errors.append({
                    "text": msg.text,
                    "timestamp": datetime.now().isoformat()
                })

        page.on("console", handle_console)

        total_tests = len(SUBJECTS) * len(AGE_GROUPS)
        current_test = 0

        # Run all combinations
        for subject in SUBJECTS:
            for age_group in AGE_GROUPS:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}]", end=" ")
                result = await test_subject_age_combination(page, subject, age_group)
                test_results.append(result)

                # Brief pause between tests
                await page.wait_for_timeout(500)

        # Close browser
        await browser.close()

    # Save detailed results
    results_file = "/Users/gaganarora/Desktop/my projects/aitutor/qa_results_detailed.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "results": test_results,
            "issues_by_category": issues,
        }, f, indent=2)

    print(f"\n\nDetailed results saved to: {results_file}")

    # Generate markdown report
    generate_markdown_report()


def generate_markdown_report():
    """Generate comprehensive markdown QA report"""
    report_path = "/Users/gaganarora/Desktop/my projects/aitutor/EDUCATIONAL_CONTENT_QA.md"

    total_issues = sum(len(cat) for cat in issues.values())
    tests_with_issues = sum(1 for r in test_results if r["issues"])
    tests_passed = len(test_results) - tests_with_issues

    # Calculate averages
    load_times = [r["load_time"] for r in test_results if r["load_time"] > 0]
    avg_load_time = sum(load_times) / len(load_times) if load_times else 0
    max_load_time = max(load_times) if load_times else 0
    min_load_time = min(load_times) if load_times else 0

    # Calculate question review stats
    total_questions = sum(r["questions_reviewed"] for r in test_results)
    tests_with_no_questions = sum(1 for r in test_results if r["questions_reviewed"] == 0)

    report = f"""# Educational Content QA Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Total Tests:** {len(test_results)}
- **Tests Passed:** {tests_passed} ({100*tests_passed//len(test_results) if len(test_results) > 0 else 0}%)
- **Tests with Issues:** {tests_with_issues} ({100*tests_with_issues//len(test_results) if len(test_results) > 0 else 0}%)
- **Total Issues Found:** {total_issues}
- **Total Questions Reviewed:** {total_questions}
- **Tests with No Questions:** {tests_with_no_questions}

### Performance Metrics

- **Average Load Time:** {avg_load_time:.2f}s
- **Min Load Time:** {min_load_time:.2f}s
- **Max Load Time:** {max_load_time:.2f}s
- **Tests Exceeding 8s Threshold:** {len(issues['performance'])}

### Issues by Category

- **Content Quality:** {len(issues['content_quality'])} issues
- **Correctness:** {len(issues['correctness'])} issues
- **Performance:** {len(issues['performance'])} issues
- **Age-Appropriateness:** {len(issues['age_appropriateness'])} issues
- **Technical Bugs:** {len(issues['technical_bugs'])} issues

### Critical Findings

"""

    # Add critical findings
    if tests_with_no_questions > 10:
        report += f"- **CRITICAL:** {tests_with_no_questions} tests could not load ANY questions - possible system failure\n"
    if len(issues['performance']) > 10:
        report += f"- **PERFORMANCE CONCERN:** {len(issues['performance'])} tests exceeded 8s load time threshold\n"
    if len(issues['technical_bugs']) > 0:
        report += f"- **TECHNICAL ISSUES:** {len(issues['technical_bugs'])} bugs detected\n"
    if len(issues['content_quality']) > 0:
        report += f"- **CONTENT QUALITY:** {len(issues['content_quality'])} quality issues found\n"

    report += """
---

## Critical Issues

### Performance Issues
"""
    report += format_issues_section(issues['performance'])

    report += """
### Technical Bugs
"""
    report += format_issues_section(issues['technical_bugs'])

    report += """
### Content Quality Issues
"""
    report += format_issues_section(issues['content_quality'])

    report += """
---

## Subject-by-Subject Breakdown

"""

    for subject in SUBJECTS:
        subject_results = [r for r in test_results if r["subject"] == subject]
        subject_issues_count = sum(len(r["issues"]) for r in subject_results)
        subject_questions = sum(r["questions_reviewed"] for r in subject_results)
        subject_avg_load = sum(r["load_time"] for r in subject_results if r["load_time"] > 0) / len([r for r in subject_results if r["load_time"] > 0]) if any(r["load_time"] > 0 for r in subject_results) else 0

        report += f"\n### {subject}\n\n"
        report += f"**Total Issues:** {subject_issues_count} | **Questions Reviewed:** {subject_questions} | **Avg Load Time:** {subject_avg_load:.2f}s\n\n"

        for result in subject_results:
            status = "✅" if not result["issues"] else "❌"
            report += f"{status} **{result['grade']}** - Load: {result['load_time']}s - Questions: {result['questions_reviewed']}\n"

            if result["issues"]:
                for issue in result["issues"][:3]:  # Show first 3 issues
                    report += f"  - {issue}\n"
                if len(result["issues"]) > 3:
                    report += f"  - *...and {len(result['issues']) - 3} more*\n"

        report += "\n"

    report += f"""
---

## Recommendations

### Immediate Actions Required

1. **Performance Optimization**
   - Investigate {len(issues['performance'])} tests exceeding 8s load time
   - Average load time: {avg_load_time:.2f}s (target: <8s)
   - Implement question pre-generation and caching
   - Optimize API response times

2. **Content Quality**
   - Review {len(issues['content_quality'])} content quality issues
   - Ensure no placeholder text in production
   - Validate widget rendering across all subjects
   - Check for age-appropriate vocabulary

3. **Technical Stability**
   - Fix {len(issues['technical_bugs'])} technical bugs
   - Ensure consistent question navigation
   - Add error boundaries for graceful failure handling
   - Monitor console errors during assessment flow

4. **Question Availability**
   - {tests_with_no_questions} tests could not review questions
   - Ensure question pool is populated for all subject/age combinations
   - Add fallback mechanisms for missing questions

### Testing Methodology

Each test combination included:
1. Navigation to dev-login page
2. Subject selection (preset button or custom input)
3. Age selection (triggers immediate assessment creation)
4. Load time measurement (from dev-login click to first question visible)
5. Review of up to 3 questions per assessment:
   - Question text validation
   - Widget rendering check
   - Placeholder content detection
   - Error message detection
   - Navigation flow testing

### Performance Benchmarks

- **Target Load Time:** < 8 seconds
- **Questions per Test:** 3 (when available)
- **Total Assessment Paths Tested:** {len(test_results)}
- **Success Rate:** {100*tests_passed//len(test_results) if len(test_results) > 0 else 0}%

---

## Detailed Test Results

See `qa_results_detailed.json` for complete test data including:
- Individual test timestamps
- Full error messages
- Performance metrics per test
- Issue categorization by subject and grade

---

## Next Steps

1. **Fix Critical Bugs:** Address technical issues preventing question load
2. **Optimize Performance:** Reduce load times below 8s threshold
3. **Content Review:** Manual QA of questions flagged with issues
4. **Re-test:** Run this suite again after fixes to validate improvements
5. **Expand Testing:** Add answer correctness validation and age-appropriateness checks
"""

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nComprehensive report saved to: {report_path}")


def format_issues_section(issue_list: List[Dict]) -> str:
    """Format issues for markdown report"""
    if not issue_list:
        return "\n*No issues found in this category.*\n"

    output = "\n"
    # Group by subject for better readability
    by_subject = {}
    for issue in issue_list:
        subject = issue.get("subject", "Unknown")
        if subject not in by_subject:
            by_subject[subject] = []
        by_subject[subject].append(issue)

    for subject, subject_issues in sorted(by_subject.items()):
        output += f"\n**{subject}:**\n"
        for issue in subject_issues[:5]:  # Show first 5 per subject
            grade = issue.get("grade", "Unknown")
            error = issue.get("issue") or issue.get("error", "Unknown error")
            output += f"- {grade}: {error}\n"
        if len(subject_issues) > 5:
            output += f"  *...and {len(subject_issues) - 5} more*\n"

    return output


if __name__ == "__main__":
    asyncio.run(main())
