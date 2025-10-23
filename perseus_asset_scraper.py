from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ---- Setup headless Chrome ----
chrome_options = Options()
chrome_options.add_argument("--headless")  # run without UI
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1280,1024")
chrome_options.add_argument("--no-sandbox")

# If chromedriver is in PATH, no need to specify executable_path
driver = webdriver.Chrome(options=chrome_options)

for i in range(5):
    try:
        driver.get("http://localhost:3000")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".framework-perseus svg")))
        time.sleep(2)
        element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
        element.screenshot("output.png")
        print("✅ Screenshot saved as output.png")
    finally:
        driver.quit()
