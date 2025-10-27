from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time 
from pathlib import Path
import uuid
 
# ---- Setup headless Chrome ----
chrome_options = Options()
chrome_options.add_argument("--headless")  # run without UI
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1280,1024")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)


screenshot_path = Path(__file__).parent.resolve() / "examples" / "screenshot"
screenshot_path.mkdir(parents=True, exist_ok=True)

def get_screenshot_sample(source_question_id: str):
    try:
        driver.get(f"http://localhost:3000/{source_question_id}")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".framework-perseus .svg")))
        time.sleep(2)
        element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
        # filename = f"{str(screenshot_path)}/{str(uuid.uuid4())}.png"
        filename = screenshot_path / f"{str(uuid.uuid4())}.png"
        element.screenshot(filename)
        driver.quit()
        return filename
    except Exception as e:
        print("Unable to take screenshot", e)