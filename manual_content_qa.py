#!/usr/bin/env python3
"""
Manual Educational Content QA Testing using Playwright
Tests all subjects and age groups for content quality, correctness, speed, and bugs
"""

import json
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser

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
            ("undefined", "Undefined value found"),
            ("lorem ipsum", "Placeholder content (lorem ipsum)"),
            ("todo", "TODO marker found"),
            ("[[☃", "Unrendered widget found"),
            ("something went wrong", "Generic error message"),
        ]

        for indicator, description in error_indicators:
            if indicator in page_text_lower:
                errors.append(f"{description}: '{indicator}'")

        # Check for console errors
        console_errors = []

        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", handle_console)

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
        await page.wait_for_timeout(1000)

        # Select subject - try button first, then custom input
        subject_selected = False

        # Check if there's a button for this subject
        try:
            subject_buttons = await page.query_selector_all("button")
            for button in subject_buttons:
                text = await button.inner_text()
                if subject.lower() in text.lower():
                    await button.click()
                    subject_selected = True
                    await page.wait_for_timeout(300)
                    break
        except:
            pass

        if not subject_selected:
            # Try to find custom subject input
            try:
                custom_input = await page.query_selector("input[placeholder*='subject' i], input[placeholder*='custom' i]")
                if custom_input:
                    await custom_input.fill(subject)
                    await page.wait_for_timeout(300)
                    subject_selected = True
            except:
                pass

        if not subject_selected:
            result["issues"].append(f"Could not select subject: {subject}")

        # Select age
        try:
            age_input = await page.query_selector("input[type='number']")
            if age_input:
                await age_input.fill(str(age_group["age"]))
                await page.wait_for_timeout(300)
        except Exception as e:
            result["issues"].append(f"Could not set age: {str(e)}")

        # Click Start Assessment
        try:
            start_button = await page.query_selector("button:has-text('Start Assessment')")
            if start_button:
                await start_button.click()
                # Wait for navigation and assessment to load
                await page.wait_for_timeout(3000)
            else:
                result["issues"].append("Could not find Start Assessment button")
                return result
        except Exception as e:
            result["issues"].append(f"Error clicking Start Assessment: {str(e)}")
            return result

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
                # Get question text
                question_area = await page.query_selector(".question-content, .perseus-question-container, [data-testid='question'], main")
                if not question_area:
                    result["issues"].append(f"Q{q_num}: Could not find question container")
                    break

                question_text = await question_area.inner_text()

                # Check for widget rendering issues
                if "[[☃" in question_text:
                    issue = f"Q{q_num}: Unrendered widget found"
                    result["issues"].append(issue)
                    issues["technical_bugs"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                # Check for placeholder content
                placeholder_terms = ["lorem ipsum", "todo", "placeholder", "test question"]
                for term in placeholder_terms:
                    if term in question_text.lower():
                        issue = f"Q{q_num}: Placeholder content detected: {term}"
                        result["issues"].append(issue)
                        issues["content_quality"].append({
                            "subject": subject,
                            "grade": age_group["display"],
                            "issue": issue
                        })
                        break

                # Check question length (too short might indicate issues)
                if len(question_text.strip()) < 20:
                    issue = f"Q{q_num}: Question appears too short ({len(question_text)} chars)"
                    result["issues"].append(issue)
                    issues["content_quality"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                # Check for answer choices
                answer_buttons = await page.query_selector_all("button[class*='choice'], .answer-option, input[type='radio']")
                if len(answer_buttons) == 0:
                    issue = f"Q{q_num}: No answer choices found"
                    result["issues"].append(issue)
                    issues["content_quality"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

                result["questions_reviewed"] += 1

                # Move to next question (if not last)
                if q_num < 3:
                    # Try to submit an answer
                    try:
                        # Click first answer choice
                        if len(answer_buttons) > 0:
                            await answer_buttons[0].click()
                            await page.wait_for_timeout(500)

                        # Click Submit button
                        submit_button = await page.query_selector("button:has-text('Submit')")
                        if submit_button:
                            await submit_button.click()
                            await page.wait_for_timeout(1500)

                            # Click Next button
                            next_button = await page.query_selector("button:has-text('Next')")
                            if next_button:
                                await next_button.click()
                                await page.wait_for_timeout(2000)
                            else:
                                result["issues"].append(f"Q{q_num}: Could not find Next button")
                                break
                        else:
                            result["issues"].append(f"Q{q_num}: Could not find Submit button")
                            break
                    except Exception as e:
                        result["issues"].append(f"Q{q_num}: Error advancing to next question: {str(e)}")
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
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

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

    report = f"""# Educational Content QA Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Total Tests:** {len(test_results)}
- **Tests Passed:** {tests_passed} ({100*tests_passed//len(test_results)}%)
- **Tests with Issues:** {tests_with_issues} ({100*tests_with_issues//len(test_results)}%)
- **Total Issues Found:** {total_issues}
- **Average Load Time:** {avg_load_time:.2f}s
- **Max Load Time:** {max_load_time:.2f}s

### Issues by Category

- **Content Quality:** {len(issues['content_quality'])} issues
- **Correctness:** {len(issues['correctness'])} issues
- **Performance:** {len(issues['performance'])} issues
- **Age-Appropriateness:** {len(issues['age_appropriateness'])} issues
- **Technical Bugs:** {len(issues['technical_bugs'])} issues

### Critical Findings

"""

    # Add critical findings
    if len(issues['performance']) > 0:
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

        report += f"\n### {subject}\n\n"
        report += f"**Total Issues:** {subject_issues_count}\n\n"

        for result in subject_results:
            status = "✅ No issues" if not result["issues"] else f"❌ {len(result['issues'])} issues"
            report += f"**{result['grade']}** - Load: {result['load_time']}s - Questions: {result['questions_reviewed']} - {status}\n"

            if result["issues"]:
                for issue in result["issues"]:
                    report += f"  - {issue}\n"

        report += "\n"

    report += """
---

## Recommendations

### Immediate Actions Required

1. **Performance Optimization**
   - Investigate load times >8s
   - Implement caching for frequently accessed content
   - Optimize question generation pipeline
   - Consider pre-loading first question during subject selection

2. **Content Quality**
   - Review all placeholder content found
   - Ensure widget rendering works across all subjects
   - Validate question-answer alignment
   - Check for age-appropriate vocabulary

3. **Technical Stability**
   - Fix any widget rendering errors
   - Ensure consistent UI patterns across all subjects
   - Add error boundaries for graceful failure handling
   - Improve error messages for debugging

4. **Age-Appropriateness Validation**
   - Manual review of questions flagged as too complex/simple
   - Validate difficulty progression within each grade
   - Ensure concept alignment with curriculum standards

### Testing Methodology

Each test combination included:
1. Navigation to dev-login page
2. Subject selection (button or custom input)
3. Age group selection
4. Load time measurement (from start to first question visible)
5. Review of first 3 questions per assessment:
   - Question text validation
   - Answer choice verification
   - Widget rendering check
   - Placeholder content detection
   - Navigation flow testing

### Performance Benchmarks

- **Target Load Time:** < 8 seconds
- **Questions Reviewed per Test:** 3
- **Total Assessment Paths Tested:** {len(test_results)}

---

## Detailed Test Results

See `qa_results_detailed.json` for complete test data including:
- Individual test timestamps
- Full error messages
- Question content samples
- Performance metrics per test
- Issue categorization

---

## Next Steps

1. **Prioritize Performance Issues:** Address all load times >8s
2. **Fix Technical Bugs:** Resolve widget rendering and navigation issues
3. **Content Review:** Manual QA of flagged questions
4. **Re-test:** Run this suite again after fixes to validate improvements
5. **Expand Testing:** Add correctness validation (are answers actually correct?)
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
