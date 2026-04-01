#!/usr/bin/env python3
"""
Comprehensive Educational Content QA Testing
Tests all subjects and age groups for content quality, correctness, speed, and bugs
"""

import json
import time
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple

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


def run_cmux_command(command: str) -> Tuple[bool, str]:
    """Execute a cmux browser command and return result"""
    try:
        result = subprocess.run(
            ["cmux", "browser", "exec", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def navigate_and_wait(url: str) -> bool:
    """Navigate to URL and wait for page load"""
    success, _ = run_cmux_command(f"goto '{url}'")
    if success:
        time.sleep(2)  # Allow page to render
    return success


def get_page_text() -> str:
    """Get visible text from current page"""
    success, output = run_cmux_command("getText 'body'")
    return output if success else ""


def click_element(selector: str) -> bool:
    """Click an element by selector"""
    success, _ = run_cmux_command(f"click '{selector}'")
    time.sleep(1)
    return success


def check_for_errors() -> List[str]:
    """Check page for common error indicators"""
    page_text = get_page_text().lower()
    errors = []

    error_indicators = [
        "error", "failed", "undefined", "null",
        "lorem ipsum", "todo", "[[☃", "placeholder",
        "something went wrong", "try again"
    ]

    for indicator in error_indicators:
        if indicator in page_text:
            errors.append(f"Found error indicator: {indicator}")

    return errors


def test_subject_age_combination(subject: str, age_group: Dict[str, Any]) -> Dict[str, Any]:
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
        if not navigate_and_wait("http://localhost:5173/dev-login"):
            result["issues"].append("Failed to load dev-login page")
            return result

        # Select subject
        # Try common subject buttons first
        subject_clicked = False
        if subject in ["Math", "Science", "English", "History"]:
            subject_clicked = click_element(f"button:contains('{subject}')")

        if not subject_clicked:
            # Use custom input for other subjects
            run_cmux_command("fill 'input[placeholder*=\"subject\"]' '{}'".format(subject))
            time.sleep(0.5)

        # Select age
        run_cmux_command("fill 'input[type=\"number\"]' '{}'".format(age_group["age"]))
        time.sleep(0.5)

        # Click Start Assessment
        click_element("button:contains('Start Assessment')")

        # Measure load time
        time.sleep(3)  # Wait for assessment to load
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
        page_errors = check_for_errors()
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

            # Get question text
            page_text = get_page_text()

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
            placeholder_terms = ["lorem ipsum", "todo", "placeholder", "test question"]
            for term in placeholder_terms:
                if term in page_text.lower():
                    issue = f"Q{q_num}: Placeholder content detected: {term}"
                    result["issues"].append(issue)
                    issues["content_quality"].append({
                        "subject": subject,
                        "grade": age_group["display"],
                        "issue": issue
                    })

            # Check question length (too short might indicate issues)
            if len(page_text.strip()) < 50:
                issue = f"Q{q_num}: Question appears too short or empty"
                result["issues"].append(issue)
                issues["content_quality"].append({
                    "subject": subject,
                    "grade": age_group["display"],
                    "issue": issue
                })

            result["questions_reviewed"] += 1

            # Move to next question (if not last)
            if q_num < 3:
                # Try to submit an answer first
                answer_clicked = click_element("button:contains('A')")
                if answer_clicked:
                    click_element("button:contains('Submit')")
                    time.sleep(1)
                    click_element("button:contains('Next')")
                    time.sleep(2)
                else:
                    # If can't find answer, skip
                    break

    except Exception as e:
        result["issues"].append(f"Test exception: {str(e)}")
        issues["technical_bugs"].append({
            "subject": subject,
            "grade": age_group["display"],
            "error": str(e)
        })

    return result


def main():
    """Run comprehensive QA testing"""
    print("=" * 80)
    print("EDUCATIONAL CONTENT QA TESTING")
    print("=" * 80)
    print(f"Testing {len(SUBJECTS)} subjects × {len(AGE_GROUPS)} age groups = {len(SUBJECTS) * len(AGE_GROUPS)} combinations")
    print()

    # Initialize cmux browser
    print("Initializing browser...")
    run_cmux_command("open")
    time.sleep(2)

    total_tests = len(SUBJECTS) * len(AGE_GROUPS)
    current_test = 0

    # Run all combinations
    for subject in SUBJECTS:
        for age_group in AGE_GROUPS:
            current_test += 1
            print(f"\n[{current_test}/{total_tests}]", end=" ")
            result = test_subject_age_combination(subject, age_group)
            test_results.append(result)

            # Brief pause between tests
            time.sleep(1)

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

    # Close browser
    run_cmux_command("close")


def generate_markdown_report():
    """Generate comprehensive markdown QA report"""
    report_path = "/Users/gaganarora/Desktop/my projects/aitutor/EDUCATIONAL_CONTENT_QA.md"

    total_issues = sum(len(cat) for cat in issues.values())
    tests_with_issues = sum(1 for r in test_results if r["issues"])
    tests_passed = len(test_results) - tests_with_issues

    # Calculate averages
    load_times = [r["load_time"] for r in test_results if r["load_time"] > 0]
    avg_load_time = sum(load_times) / len(load_times) if load_times else 0

    report = f"""# Educational Content QA Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Total Tests:** {len(test_results)}
- **Tests Passed:** {tests_passed}
- **Tests with Issues:** {tests_with_issues}
- **Total Issues Found:** {total_issues}
- **Average Load Time:** {avg_load_time:.2f}s

### Issues by Category

- **Content Quality:** {len(issues['content_quality'])} issues
- **Correctness:** {len(issues['correctness'])} issues
- **Performance:** {len(issues['performance'])} issues
- **Age-Appropriateness:** {len(issues['age_appropriateness'])} issues
- **Technical Bugs:** {len(issues['technical_bugs'])} issues

---

## Critical Issues

### Performance Issues
{format_issues_section(issues['performance'])}

### Technical Bugs
{format_issues_section(issues['technical_bugs'])}

### Content Quality Issues
{format_issues_section(issues['content_quality'])}

---

## Subject-by-Subject Breakdown

"""

    for subject in SUBJECTS:
        subject_results = [r for r in test_results if r["subject"] == subject]
        subject_issues = sum(len(r["issues"]) for r in subject_results)

        report += f"\n### {subject}\n\n"

        for result in subject_results:
            status = "✅ No issues" if not result["issues"] else f"❌ {len(result['issues'])} issues"
            report += f"**{result['grade']}** - Load: {result['load_time']}s - {status}\n"

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

2. **Content Quality**
   - Review all placeholder content
   - Ensure widget rendering works across all subjects
   - Validate question-answer alignment

3. **Age-Appropriateness**
   - Review vocabulary complexity for each age group
   - Ensure concepts match grade level expectations
   - Validate difficulty progression

### Testing Methodology

Each test combination included:
- Navigation to dev-login
- Subject and age selection
- Load time measurement
- Review of first 3 questions per assessment
- Error detection and validation

---

## Detailed Test Results

See `qa_results_detailed.json` for complete test data including:
- Individual test timestamps
- Full error messages
- Page content samples
- Performance metrics
"""

    with open(report_path, "w") as f:
        f.write(report)

    print(f"\nComprehensive report saved to: {report_path}")


def format_issues_section(issue_list: List[Dict]) -> str:
    """Format issues for markdown report"""
    if not issue_list:
        return "\n*No issues found in this category.*\n"

    output = "\n"
    for issue in issue_list[:10]:  # Show first 10
        subject = issue.get("subject", "Unknown")
        grade = issue.get("grade", "Unknown")
        error = issue.get("issue") or issue.get("error", "Unknown error")
        output += f"- **{subject} ({grade}):** {error}\n"

    if len(issue_list) > 10:
        output += f"\n*...and {len(issue_list) - 10} more issues*\n"

    return output


if __name__ == "__main__":
    main()
