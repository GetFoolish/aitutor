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
from utils.image import clean_png_files
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

            processed_prompts = {} 
            if isinstance(prompts, str):
                try:
                    processed_prompts = process_response(prompts)
                    processed_prompts = json.loads(processed_prompts)
                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError when parsing prompts: {e}")
                    processed_prompts = {} # Ensure processed_prompts is a dict on error
            elif isinstance(prompts, dict):
                processed_prompts = prompts
            else:
                print(f"Prompts is neither string nor dict, type: {type(prompts)}")
                processed_prompts = {} # Ensure processed_prompts is a dict if unexpected type
            image_data = processed_prompts.get("image_data", [])
            if not isinstance(image_data, list):
                print(f"Warning: 'image_data' is not a list. Type: {type(image_data)}. Treating as empty.")
                image_data = []

            if len(image_data) > 0:
                print(f"Entering loop for image generation. Number of images: {len(image_data)}")
                for p in image_data:
                    # Add a check for 'prompt' key in each item
                    if "prompt" in p and p["prompt"]:
                        svg = await run_agent(new_svg_prompt, generate_svg, prompts=p["prompt"])
                        p["original_url"] = await process_and_upload_svg(svg)
                    else:
                        print(f"Skipping SVG generation for item due to missing or empty 'prompt' key: {p}")
                
                # Update processed_prompts with the potentially modified image_data
                processed_prompts["image_data"] = image_data
                response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, prompts=processed_prompts)
            else:
                print("No image data found or prompts is empty, skipping SVG generation loop.")
                # Pass an empty JSON object for prompts when no image data is found
                response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, prompts=json.dumps({}))
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
            source_question_id = question.pop("_id")
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
    finally:
        # Clean up generated PNG files
        print("Cleaning up temporary PNG files...")
        cleanup_results = clean_png_files()
        print(f"Cleanup complete: Deleted {cleanup_results['deleted_count']} files, freed {cleanup_results['freed_bytes']} bytes.")
        
if __name__ == "__main__":
    asyncio.run(main())

