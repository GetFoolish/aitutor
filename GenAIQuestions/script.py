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

file_pattern = Path(__file__).parent.resolve() / "examples" / "*.json"
new_json_path = Path(__file__).parent.resolve() / "new"
 
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
    async def generate_questions(data: json) -> json:
        try:
            print(f"Generating questions...")
            # call function which contains steps
            new_json = await run_agent(new_question_prompt, generate_question, data=data)
            prompts = await run_agent(new_images_prompt, generate_prompt, new_json=new_json)
            if isinstance(prompts, str):
                prompts = process_response(prompts)
                prompts = json.loads(prompts)
            prompts = [p["prompt"] for p in prompts["image_data"]]
            urls = generate_images(prompts)
            response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, urls=urls)
            return process_response(response)
        except Exception as e:
            print(f"The following error occured: {e}")

    count = 2       
    url = f"http://localhost:8001/get-question-for-generation"
    api_response = requests.get(url)
    questions = api_response.json()

    # get questions
    # selenium get id and screenshot  
    # use updated data for generation

    for q in questions:
        source_question_id = q.id
        response: None
        try:
            response = await generate_questions(q)
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
