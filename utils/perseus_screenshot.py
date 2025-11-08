"""
Perseus Question Screenshot Utility
Adapted from Isreal's work for macOS
Captures visual representation of rendered Perseus questions using Selenium
"""

import os
import time
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from loguru import logger


def get_chrome_driver():
    """Initialize Chrome driver with headless options for macOS"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--disable-extensions")

    # macOS-specific: Point to Chrome binary
    chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # Use webdriver-manager to automatically handle ChromeDriver
    service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=chrome_options)


def capture_perseus_question(
    perseus_content: dict,
    output_path: str | Path,
    dash_api_url: str = "http://localhost:8000",
    frontend_url: str = "http://localhost:3000"
) -> str | None:
    """
    Capture a screenshot of a rendered Perseus question.

    Args:
        perseus_content: The Perseus question content (full JSON with question, answerArea, etc.)
        output_path: Path where screenshot will be saved
        dash_api_url: URL of the Dash API backend
        frontend_url: URL of the React frontend

    Returns:
        Path to the saved screenshot, or None if failed
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    driver = None
    temp_id = None

    try:
        # Step 1: Store question temporarily in backend
        logger.info("Storing question temporarily for rendering...")
        response = requests.post(
            f"{dash_api_url}/store-temp-question",
            json=perseus_content,
            timeout=10
        )
        response.raise_for_status()
        temp_id = response.json()["temp_id"]
        logger.info(f"Question stored with temp_id: {temp_id}")

        # Step 2: Initialize headless browser
        logger.info("Initializing headless Chrome browser...")
        driver = get_chrome_driver()

        # Step 3: Navigate to the question render page
        render_url = f"{frontend_url}/question-render/{temp_id}"
        logger.info(f"Navigating to: {render_url}")
        driver.get(render_url)

        # Step 4: Wait for Perseus to finish rendering
        wait = WebDriverWait(driver, 30)
        logger.info("Waiting for Perseus question to render...")

        # Wait for the framework-perseus container
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "framework-perseus")))

        # Additional wait for any dynamic content (images, LaTeX, etc.)
        time.sleep(2)

        logger.info("Question rendered successfully")

        # Step 5: Find the element to screenshot
        try:
            # Try to capture just the Perseus content area
            element = driver.find_element(By.CLASS_NAME, "framework-perseus")
        except Exception as e:
            logger.warning(f"Could not find .framework-perseus, capturing full page: {e}")
            # Fallback to body
            element = driver.find_element(By.TAG_NAME, "body")

        # Step 6: Take screenshot
        logger.info(f"Capturing screenshot to: {output_path}")
        element.screenshot(str(output_path))

        logger.info(f"✓ Screenshot saved successfully: {output_path}")
        return str(output_path)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to communicate with backend: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None
    finally:
        # Cleanup
        if driver:
            driver.quit()
            logger.debug("Browser closed")

        # Clean up temporary question storage
        if temp_id:
            try:
                requests.delete(f"{dash_api_url}/delete-temp-question/{temp_id}", timeout=5)
                logger.debug(f"Temp question {temp_id} cleaned up")
            except Exception as e:
                logger.warning(f"Failed to clean up temp question: {e}")


if __name__ == "__main__":
    # Test the screenshotter
    from db.perseus_repository import get_random_questions

    print("Testing Perseus screenshot capture...")
    questions = get_random_questions(1)

    if questions:
        test_output = Path(__file__).parent.parent / "test_screenshot.png"
        result = capture_perseus_question(
            perseus_content=questions[0],
            output_path=test_output
        )

        if result:
            print(f"✓ Test successful! Screenshot saved to: {result}")
        else:
            print("✗ Test failed")
    else:
        print("No questions found in database")
