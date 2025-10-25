from typing import Callable, TypeVar
from agents.question_generator.main import run as generate_question
from agents.prompt_generator.main import run as generate_prompt
from agents.json_rebuilder.main import run as rebuild_json
from agents.image_generator.agent import generate_images 
from agents.prompts.client import new_question_prompt, new_images_prompt, rebuild_json_prompt
import glob 
import uuid
import json 
import asyncio
import requests
from pathlib import Path 

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

file_pattern = Path(__file__).parent.resolve() / "examples" / "*.json"
new_json_path = Path(__file__).parent.resolve() / "new"

screenshot_path = Path(__file__).parent.resolve() / "examples" / "screenshot"
screenshot_path.mkdir(parents=True, exist_ok=True)
 
T = TypeVar('T')

# load examples 
async def main():
    def process_response(response: str) -> str:
        response = response.strip()
        if response.startswith("```json"):
            response = response.removeprefix("```json")
        if response.endswith("```"):
            response = response.removesuffix("```")
        return response.strip()
        
    # helper function to run agents with formatted prompts
    async def run_agent(prompt: str, func: Callable[[str], T], **kwargs) -> T:
        prompt = prompt.format(**kwargs)
        response = await func(prompt)
        return response
    
    # generate questions 
    async def generate_questions(data: json, filename: str) -> json:
        try:
            print(f"Generating questions...")
            # call function which contains steps
            new_json = await run_agent(new_question_prompt, generate_question, data=data)
            prompts = await run_agent(new_images_prompt, generate_prompt, new_json=new_json)
            if isinstance(prompts, str):
                prompts = process_response(prompts)
                prompts = json.loads(prompts)
            prompts = [p["prompt"] for p in prompts["image_data"]]
            urls = generate_images(prompts,filename)
            response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, urls=urls)
            return process_response(response)
        except Exception as e:
            print(f"The following error occured: {e}")

    count = 2       
    url = f"http://localhost:8001/get-question-for-generation"
    api_response = requests.get(url)
    question = api_response.json()
    source_question_id = question.pop("_id")


    # get questions
    # selenium get id and screenshot  
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(f"http://localhost:3000/{source_question_id}")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".framework-perseus svg")))
        time.sleep(2)
        element = driver.find_element(By.CSS_SELECTOR, ".framework-perseus")
        filename = f"{str(screenshot_path)}/{str(uuid.uuid4())}.png"
        element.screenshot(filename)
        print("✅ Screenshot saved as", filename)
    finally:
        driver.quit()

    # use updated data for generation
    if question:
        response: None
        try:
            response = await generate_questions(question, filename)
        except Exception as e:
            print(f"Unable to load JSON: {e}")

        if response:
            url = f"http://localhost:8001/save-generated-question/{source_question_id}"
            try:
                response = requests.post(url, data=response)
            except Exception as e:
                print(f"Unable to save JSON: {e}")
        else:
            print(f"No response generated for {q.id}, skipping...\n")

if __name__ == "__main__":
    asyncio.run(main())
