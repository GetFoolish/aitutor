from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import uuid
import time
import os
import platform
import shutil

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
    
    # Try to find ChromeDriver automatically
    # First, check if chromedriver is in PATH (most common case)
    chromedriver_path = shutil.which("chromedriver")
    
    # Also check common Windows locations
    if not chromedriver_path:
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
            os.path.expanduser(r"~\AppData\Local\chromedriver\chromedriver.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break
    
    if chromedriver_path:
        # ChromeDriver found - use it
        print(f"Using ChromeDriver: {chromedriver_path}")
        return webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
    else:
        # ChromeDriver not found - let Selenium try to find it automatically
        # This will work if ChromeDriver is installed via webdriver-manager or in default locations
        print("ChromeDriver not found in PATH or common locations, trying automatic detection...")
        try:
            return webdriver.Chrome(options=chrome_options)
        except Exception as e:
            raise Exception(
                f"Could not find ChromeDriver. Please either:\n"
                f"1. Add ChromeDriver to your PATH (run: chromedriver --version to verify)\n"
                f"2. Install webdriver-manager: pip install webdriver-manager\n"
                f"3. Download ChromeDriver from: https://chromedriver.chromium.org/\n"
                f"Original error: {e}"
            )

def get_screenshot_sample(source_question_id: str):
    screenshot_path = Path(__file__).parent.parent.resolve() / "examples" / "screenshot"
    screenshot_path.mkdir(parents=True, exist_ok=True)

    driver = get_chrome_driver()
    try:
        base_url = "http://localhost:3000"
        print(f"Loading question page: {base_url}/{source_question_id}")
        driver.get(f"{base_url}/{source_question_id}")

        wait = WebDriverWait(driver, 40)
        
        # Wait for the main question container to be present
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".framework-perseus")))
        print("Page loaded, waiting for content to render...")
        
        # Wait for images and async content to load
        time.sleep(3)  # Initial wait for basic content
        
        # Wait for all images to load
        print("Waiting for images to load...")
        driver.execute_script("""
            return new Promise((resolve) => {
                const images = document.querySelectorAll('img');
                let loaded = 0;
                const total = images.length;
                
                if (total === 0) {
                    resolve();
                    return;
                }
                
                images.forEach(img => {
                    if (img.complete) {
                        loaded++;
                        if (loaded === total) resolve();
                    } else {
                        img.onload = () => {
                            loaded++;
                            if (loaded === total) resolve();
                        };
                        img.onerror = () => {
                            loaded++;
                            if (loaded === total) resolve();
                        };
                    }
                });
                
                // Timeout after 5 seconds
                setTimeout(resolve, 5000);
            });
        """)
        
        # Wait for SVG content to render
        time.sleep(2)
        
        # Verify that question content is actually present
        try:
            question_text = driver.execute_script("""
                const perseus = document.querySelector('.framework-perseus');
                if (!perseus) return '';
                return perseus.innerText || perseus.textContent || '';
            """)
            if question_text and len(question_text.strip()) > 10:
                print(f"✅ Question content detected ({len(question_text)} characters)")
            else:
                print("⚠️ Warning: Question content seems empty or very short")
        except Exception as text_check_error:
            print(f"Could not verify question text: {text_check_error}")
        
        # Scroll to top to ensure we capture from the beginning
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        
        # Find the question container - use the entire framework-perseus div
        element = None
        try:
            # Get the entire question container (this should contain all question content)
            element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
            print("Found .framework-perseus container")
        except Exception as e1:
            print(f"Could not find .framework-perseus: {e1}")
            try:
                # Fallback: try to find question-panel or main content area
                element = driver.find_element(By.CSS_SELECTOR, "[class*='question']")
                print("Found question container via fallback")
            except Exception as e2:
                print(f"Fallback failed: {e2}, using body")
                element = driver.find_element(By.TAG_NAME, "body")
        
        # Get element dimensions to ensure it's not too small
        element_size = element.size
        element_location = element.location
        
        print(f"Element size: {element_size['width']}x{element_size['height']}")
        print(f"Element location: {element_location}")
        
        # Scroll element into view to ensure it's fully visible
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", element)
        time.sleep(1)
        
        # Get the full height of the element (may be larger than viewport)
        element_full_height = driver.execute_script("""
            return Math.max(
                document.body.scrollHeight,
                document.body.offsetHeight,
                document.documentElement.clientHeight,
                document.documentElement.scrollHeight,
                document.documentElement.offsetHeight
            );
        """)
        
        element_actual_height = driver.execute_script("return arguments[0].scrollHeight;", element)
        viewport_height = driver.execute_script("return window.innerHeight;")
        
        print(f"Element height: {element_actual_height}px, Viewport: {viewport_height}px")
        
        # If element is taller than viewport, we need to take a full-page screenshot
        if element_actual_height > viewport_height * 0.8:  # Element is significantly taller
            print("⚠️ Question is longer than viewport, using full-page screenshot method...")
            # Set window size to accommodate full content
            driver.set_window_size(1920, max(2160, element_actual_height + 200))
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        
        # Take screenshot of the element
        filename = screenshot_path / f"{uuid.uuid4()}.png"
        
        try:
            element.screenshot(str(filename))
        except Exception as screenshot_error:
            print(f"Element screenshot failed: {screenshot_error}, trying viewport screenshot...")
            # Fallback to viewport screenshot
            driver.save_screenshot(str(filename))
        
        # Validate screenshot quality
        from PIL import Image
        import numpy as np
        
        img = Image.open(filename)
        width, height = img.size
        
        print(f"Initial screenshot: {width}x{height}")
        
        # Check if screenshot is too small (likely incomplete)
        if width < 200 or height < 200:
            print(f"⚠️ Screenshot too small ({width}x{height}), trying full viewport...")
            # Try full page screenshot
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            driver.save_screenshot(str(filename))
            img = Image.open(filename)
            width, height = img.size
            print(f"Viewport screenshot: {width}x{height}")
        
        # Validate content quality
        img_gray = img.convert('L')
        pixels = np.array(img_gray)
        variance = np.var(pixels)
        mean_brightness = np.mean(pixels)
        
        print(f"Screenshot stats: {width}x{height}, variance: {variance:.2f}, brightness: {mean_brightness:.2f}")
        
        # Check if image is blank or has very low content
        if variance < 50:  # Increased threshold for better detection
            print(f"⚠️ Screenshot appears blank/low content (variance: {variance:.2f})")
            # Retry with longer wait
            print("Retrying with longer wait time...")
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            try:
                element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
                element.screenshot(str(filename))
                img = Image.open(filename)
                img_gray = img.convert('L')
                pixels = np.array(img_gray)
                variance = np.var(pixels)
                width, height = img.size
                print(f"Retry screenshot: {width}x{height}, variance: {variance:.2f}")
            except Exception as retry_error:
                print(f"Retry failed: {retry_error}, using viewport")
                driver.save_screenshot(str(filename))
                img = Image.open(filename)
                img_gray = img.convert('L')
                pixels = np.array(img_gray)
                variance = np.var(pixels)
                width, height = img.size
        
        # Final validation
        if variance < 30:  # Still too low variance
            print(f"❌ Screenshot quality too low (variance: {variance:.2f}). May be incomplete.")
            # Don't fail completely, but warn
            print("⚠️ Proceeding with low-quality screenshot - may need manual review")
        elif width < 200 or height < 200:
            print(f"❌ Screenshot too small ({width}x{height}). May be incomplete.")
            return None
        
        print(f"✅ Screenshot saved: {filename} ({width}x{height}, variance: {variance:.2f})")
        return str(filename)
        
    except Exception as e:
        print(f"❌ Unable to take screenshot: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        driver.quit()


    # 172.27.192.1
