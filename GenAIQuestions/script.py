from typing import Callable, TypeVar
from agents.question_generator.main import run as generate_question
from agents.prompt_generator.main import run as generate_prompt
from agents.json_rebuilder.main import run as rebuild_json 
from agents.svg_generator.main import run as generate_svg
from agents.prompts.client import new_question_prompt, new_images_prompt, rebuild_json_prompt, new_svg_prompt
import uuid
import json 
import asyncio
import requests
import sys
from pathlib import Path 
from utils.scraper import get_screenshot_sample
from utils.image import upload_to_imagekit, process_svg

file_pattern = Path(__file__).parent.resolve() / "examples" / "*.json"
new_json_path = Path(__file__).parent.resolve() / "new" 


assets = Path(__file__).parent.parent.resolve() / "assets"
assets.mkdir(parents=True, exist_ok=True)
 
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
    
    async def process_and_upload_svg(svg):
        filepath = assets / f"{str(uuid.uuid4())}.png"
        filename = Path(filepath).stem
        await process_svg(svg,filepath)
        url = await upload_to_imagekit(filename, filepath)
        return url
    # helper function to run agents with formatted prompts
    async def run_agent(prompt: str, func: Callable[[str], T], **kwargs) -> T:
        prompt = prompt.format(**kwargs)
        response = await func(prompt)
        return response
    

    # generate questions 
    async def generate_questions(data: json, image_file: bytes, filename: str=None) -> json:
        try:
            print(f"Generating questions...")
            # call function which contains steps
            new_json = await run_agent(new_question_prompt, generate_question, data=data)
            prompts = await run_agent(new_images_prompt, generate_prompt, new_json=new_json, image_file=image_file)
            if isinstance(prompts, str):
                prompts = process_response(prompts)
                prompts = json.loads(prompts)
            for p in prompts["image_data"]:
                print(f"Generating SVG for prompt: {p['prompt']}")
                svg = await run_agent(new_svg_prompt, generate_svg, prompts=p["prompt"])
                p["original_url"] = await process_and_upload_svg(svg)
                print(f"Uploaded image to: {p['original_url']}")
            response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, prompts=prompts)
            return process_response(response)
        except Exception as e:
            print(f"The following error occured: {e}")

    # main entry point
    count = 0      
    try:
        url = f"http://localhost:8001/api/get-question-for-generation"
        print("Fetching question data...")
        api_response = requests.get(url)
        question = api_response.json()
        if "question" in question:
            # source_question_id = question.pop("_id")
            source_question_id = "68fc3eb527d6738d148b08ea"
        print(f"Processing question ID: {source_question_id}")

        filename = get_screenshot_sample(source_question_id)
        print(f"Screenshot saved at: {filename}")
        image_file = open(filename, "rb").read()
        if question: 
            response: None
            try:
                response = await generate_questions(question, filename, image_file)
            except Exception as e:
                print(f"Unable to load JSON: {e}")
            if response:
                url = f"http://localhost:8001/api/save-generated-question/{source_question_id}"
                try:
                    response = requests.post(url, data=response)
                    print(f"Saved generated question for {response}")
                except Exception as e:
                    print(f"Unable to save JSON: {e}")
            else:
                print(f"No response generated for {filename}, skipping...\n")
    except Exception as e:
        print(f"The following error occured in main loop: {e}")
        
if __name__ == "__main__":
    asyncio.run(main()) 
