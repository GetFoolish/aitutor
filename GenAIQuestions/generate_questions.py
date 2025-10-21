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

    for path in glob.glob(str(file_pattern)):
        source_name = Path(path).stem
        print(f"Loading source: {source_name}.json")
        response = None 
        new_json = new_json_path / f"{source_name}_generated.json"
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if data:
                    response = await generate_questions(data)
            except Exception as e:
                print(f"Unable to load JSON: {e}")

        if response:
            try:
                json_response = json.loads(response)
                with open(new_json, "w", encoding="utf-8") as f:
                    json.dump(json_response, f, indent=4)
                print(f"\nGeneration completed for: {new_json}\n")
            except Exception as e:
                print(f"Unable to save JSON {new_json}: {e}")
        else:
            print(f"No response generated for {path}, skipping...\n")

if __name__ == "__main__":
    asyncio.run(main())