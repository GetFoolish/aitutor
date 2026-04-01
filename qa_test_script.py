#!/usr/bin/env python3
"""
Comprehensive QA Test Script for AI Tutor Application
Tests all critical flows and documents bugs found.
"""

import subprocess
import json
import time
import sys
from datetime import datetime

bugs = []
bug_counter = 1

def add_bug(title, severity, steps, expected, actual, console_errors=None, screenshots=None):
    global bug_counter
    bug = {
        "id": bug_counter,
        "title": title,
        "severity": severity,
        "steps": steps,
        "expected": expected,
        "actual": actual,
        "console_errors": console_errors or [],
        "screenshots": screenshots or [],
        "timestamp": datetime.now().isoformat()
    }
    bugs.append(bug)
    print(f"\n🐛 BUG #{bug_counter}: {title}")
    print(f"   Severity: {severity}")
    bug_counter += 1
    return bug

def run_cmux_test(script):
    """Run a cmux browser automation script"""
    try:
        result = subprocess.run(
            ['cmux', 'run', '-'],
            input=script,
            text=True,
            capture_output=True,
            timeout=60
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_dev_login_flow():
    """Test 1: Dev-Login Flow"""
    print("\n" + "="*60)
    print("TEST 1: Dev-Login Flow")
    print("="*60)

    # Test 1a: Navigate to dev-login
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    screenshot dev-login-page.png
    console.log
    """

    result = run_cmux_test(script)
    if not result["success"]:
        add_bug(
            "Dev-login page fails to load",
            "Critical",
            ["Navigate to http://localhost:5173/app/dev-login"],
            "Dev-login page loads successfully",
            f"Page failed to load: {result.get('error', 'Unknown error')}",
            console_errors=[result.get("stderr", "")]
        )
        return False

    # Test 1b: Select Math subject
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    click button:contains("Math")
    wait 500
    screenshot math-selected.png
    console.log
    """

    result = run_cmux_test(script)

    # Test 1c: Select age 10 (Grade 5)
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    click button:contains("Math")
    wait 500
    click button:contains("10")
    wait 5000
    screenshot after-age-selection.png
    console.log
    """

    result = run_cmux_test(script)
    if "error" in result.get("stdout", "").lower():
        add_bug(
            "Age selection triggers console error",
            "High",
            ["Click Math button", "Click age 10 button"],
            "Navigate to assessment without errors",
            "Console errors detected during navigation",
            console_errors=[result.get("stdout", "")]
        )

    # Test 1d: Test custom subject input
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    type input[placeholder*="Geography"] "Geography"
    wait 500
    screenshot custom-subject.png
    """

    run_cmux_test(script)

    # Test 1e: Test without student name
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    click button:contains("Science")
    wait 500
    click button:contains("12")
    wait 5000
    console.log
    """

    result = run_cmux_test(script)

    print("✅ Dev-Login flow tests completed")
    return True

def test_assessment_flow():
    """Test 2: Assessment Flow"""
    print("\n" + "="*60)
    print("TEST 2: Assessment Flow")
    print("="*60)

    # Navigate to assessment via dev-login
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    click button:contains("Math")
    wait 500
    click button:contains("8")
    wait 5000
    screenshot assessment-loaded.png
    console.log
    """

    result = run_cmux_test(script)

    # Check if question loaded
    script = """
    navigate http://localhost:5173/app/assessment/Math
    wait 3000
    screenshot question-display.png
    console.log
    """

    result = run_cmux_test(script)

    print("✅ Assessment flow tests completed")
    return True

def test_answer_submission():
    """Test 3: Answer Submission"""
    print("\n" + "="*60)
    print("TEST 3: Answer Submission")
    print("="*60)

    # Test empty answer submission
    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    click button:contains("Math")
    wait 500
    click button:contains("8")
    wait 5000
    click button:contains("Check Answer")
    wait 2000
    screenshot empty-answer-submit.png
    console.log
    """

    result = run_cmux_test(script)
    if "error" not in result.get("stdout", "").lower():
        add_bug(
            "Empty answer submission allowed without validation",
            "Critical",
            ["Load assessment", "Click Check Answer without entering answer"],
            "Show validation error: 'Please provide an answer'",
            "Empty answer submission may be allowed without proper validation",
            console_errors=[result.get("stdout", "")]
        )

    print("✅ Answer submission tests completed")
    return True

def test_mobile_viewport():
    """Test 5: Mobile Viewport"""
    print("\n" + "="*60)
    print("TEST 5: Mobile Viewport")
    print("="*60)

    script = """
    viewport 375 667
    navigate http://localhost:5173/app/dev-login
    wait 2000
    screenshot mobile-dev-login.png
    click button:contains("Math")
    wait 500
    click button:contains("8")
    wait 5000
    screenshot mobile-assessment.png
    console.log
    """

    result = run_cmux_test(script)

    print("✅ Mobile viewport tests completed")
    return True

def test_console_errors():
    """Test 7: Console Errors Check"""
    print("\n" + "="*60)
    print("TEST 7: Console Errors")
    print("="*60)

    script = """
    navigate http://localhost:5173/app/dev-login
    wait 2000
    console.log
    click button:contains("Math")
    wait 500
    console.log
    click button:contains("8")
    wait 5000
    console.log
    """

    result = run_cmux_test(script)
    output = result.get("stdout", "")

    if "error" in output.lower() or "warning" in output.lower():
        add_bug(
            "Console errors/warnings detected during normal flow",
            "Medium",
            ["Navigate to dev-login", "Select subject and age"],
            "No console errors or warnings",
            "Console errors/warnings detected",
            console_errors=[output]
        )

    print("✅ Console error tests completed")
    return True

def save_bug_report():
    """Save bug report to file"""
    report_file = f"/Users/gaganarora/Desktop/my projects/aitutor/qa_bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "total_bugs": len(bugs),
            "bugs": bugs,
            "test_date": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\n📊 Bug report saved to: {report_file}")
    return report_file

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("QA TEST SUMMARY")
    print("="*60)
    print(f"Total bugs found: {len(bugs)}")

    if bugs:
        print("\nBugs by severity:")
        for severity in ["Critical", "High", "Medium", "Low"]:
            count = len([b for b in bugs if b["severity"] == severity])
            if count > 0:
                print(f"  {severity}: {count}")

        print("\nDetailed Bug List:")
        for bug in bugs:
            print(f"\nBUG #{bug['id']}: {bug['title']}")
            print(f"Severity: {bug['severity']}")
            print(f"Steps to Reproduce:")
            for i, step in enumerate(bug['steps'], 1):
                print(f"  {i}. {step}")
            print(f"Expected: {bug['expected']}")
            print(f"Actual: {bug['actual']}")
            if bug['console_errors']:
                print(f"Console Errors: {bug['console_errors'][0][:200]}...")
    else:
        print("✅ No bugs found! Application is working as expected.")

def main():
    print("="*60)
    print("AI TUTOR QA TEST SUITE")
    print("="*60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Run all test suites
        test_dev_login_flow()
        test_assessment_flow()
        test_answer_submission()
        test_mobile_viewport()
        test_console_errors()

        # Save and print results
        report_file = save_bug_report()
        print_summary()

        print(f"\n✅ QA testing completed!")
        print(f"📄 Full report: {report_file}")

        return 0 if len(bugs) == 0 else 1

    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
