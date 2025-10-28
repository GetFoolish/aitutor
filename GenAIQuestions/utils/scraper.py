from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time 
from pathlib import Path
import uuid
 
# ---- Setup headless Chrome ----
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-software-rasterizer")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--remote-debugging-port=9222")


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import uuid
import time
import os
import platform

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.binary_location = "/usr/bin/google-chrome"


    return webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)

def get_screenshot_sample(source_question_id: str):
    screenshot_path = Path(__file__).parent.parent.resolve() / "examples" / "screenshot"
    screenshot_path.mkdir(parents=True, exist_ok=True)

    driver = get_chrome_driver()
    try:
        # Detect WSL and use proper host resolution
        base_url = "http://localhost:3000"  # safer inside WSL
        driver.get(f"{base_url}/{source_question_id}")

        wait = WebDriverWait(driver, 40)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".framework-perseus")))
        print("Page loaded, taking screenshot...")
        time.sleep(1)
        element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
        filename = screenshot_path / f"{uuid.uuid4()}.png"
        element.screenshot(str(filename))
        return str(filename)
    except Exception as e:
        print("Unable to take screenshot:", e)
        return None
    finally:
        driver.quit()


    # 172.27.192.1