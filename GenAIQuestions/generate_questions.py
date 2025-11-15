from typing import Callable, TypeVar, Tuple, Optional, List
from agents.question_generator.main import run as generate_question
from agents.prompt_generator.main import run as generate_prompt
from agents.json_rebuilder.main import run as rebuild_json 
from agents.svg_generator.main import run as generate_svg
from agents.prompts.client import new_question_prompt, new_images_prompt, rebuild_json_prompt, new_svg_prompt
import uuid
import json 
import asyncio
import re
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

def process_response(response: str) -> str:
    response = response.strip()
    # Find the JSON block if it's wrapped in markdown code blocks
    if "```json" in response:
        # Extract everything between ```json and the closing ```
        start = response.find("```json") + len("```json")
        end = response.find("```", start)
        if end != -1:
            response = response[start:end]
    elif response.startswith("```") and response.endswith("```"):
        # Handle generic code blocks
        response = response.removeprefix("```").removesuffix("```")
    return response.strip()


def safe_parse_json(value) -> Optional[dict]:
    """
    Attempt to parse a JSON string (optionally wrapped in code fences) into a dict.
    Returns None if parsing fails.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            cleaned = process_response(value)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"⚠️ Could not parse generated JSON: {e}")
            print(f"   Raw snippet: {value[:200] if value else 'EMPTY'}")
    return None


def extract_image_urls(question_dict: Optional[dict]) -> List[str]:
    """Collect all candidate image URLs from a Perseus question JSON."""
    if not question_dict:
        return []

    urls: List[str] = []
    question_section = question_dict.get("question", {})
    images_dict = question_section.get("images", {})
    urls.extend(images_dict.keys())

    markdown_sources = [question_section.get("content", "")]
    widgets = question_section.get("widgets", {}) or {}
    for widget in widgets.values():
        markdown_sources.append(json.dumps(widget))

    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for source in markdown_sources:
        if not source:
            continue
        urls.extend(pattern.findall(source))

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for url in urls:
        if not url or url in seen:
            continue
        deduped.append(url)
        seen.add(url)
    return deduped


def fill_missing_original_urls(image_data: List[dict], question_dict: Optional[dict]) -> None:
    """
    Some prompts may miss the original_url. Use the question JSON to fill them so replacements work.
    """
    if not image_data or not question_dict:
        return

    missing_entries = [item for item in image_data if not item.get("original_url")]
    if not missing_entries:
        return

    candidate_urls = extract_image_urls(question_dict)
    if not candidate_urls:
        print("⚠️ Unable to determine original image URLs from question JSON.")
        return

    url_iter = iter(candidate_urls)
    for item in image_data:
        if item.get("original_url"):
            continue
        try:
            candidate_url = next(url_iter)
        except StopIteration:
            print("⚠️ Not enough candidate URLs to fill all missing entries.")
            break
        item["original_url"] = candidate_url
        print(f"🔗 Filled missing original_url with {candidate_url}")


# load examples 
async def main():
    async def process_and_upload_svg(svg):
        filepath = assets / f"{str(uuid.uuid4())}.png"
        filename = Path(filepath).stem
        await process_svg(svg,filepath)
        url = await upload_to_imagekit(filename, filepath)
        return url
    # helper function to run agents with formatted prompts with retry logic for rate limits
    async def run_agent(prompt: str, func: Callable[[str], T], **kwargs) -> T:
        prompt = prompt.format(**kwargs)
        max_retries = 3
        retry_delay = 5  # Start with 5 seconds
        
        for attempt in range(max_retries):
            try:
                response = await func(prompt)
                return response
            except Exception as e:
                error_msg = str(e)
                # Check if it's a rate limit error (429)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                        print(f"⚠️ Rate limit error (429) on attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Rate limit error after {max_retries} attempts. Giving up.")
                        raise Exception(f"Rate limit error (429) after {max_retries} retries. Please wait 10-15 minutes before trying again.")
                else:
                    # Not a rate limit error, re-raise immediately
                    raise
    
    # generate questions 
    async def generate_questions(data: json, image_file: bytes) -> Tuple[json, dict]:
        cost_tracking = {
            "question_generator": {"cost": 0.0, "tokens": {"input": 0, "output": 0}},
            "prompt_generator": {"cost": 0.0, "tokens": {"input": 0, "output": 0}},
            "svg_generator": {"cost": 0.0, "tokens": {"input": 0, "output": 0}, "count": 0},
            "json_rebuilder": {"cost": 0.0, "tokens": {"input": 0, "output": 0}},
            "total_cost": 0.0
        }
        try:
            print(f"Generating questions...")
            # call function which contains steps
            new_json = await run_agent(new_question_prompt, generate_question, data=data)
            parsed_new_question = safe_parse_json(new_json)
            # TODO: Extract actual token usage from agent responses when available
            # For now, using estimated costs based on Gemini 2.0 Flash pricing
            # Input: $0.075 per 1M tokens, Output: $0.30 per 1M tokens
            cost_tracking["question_generator"]["cost"] = 0.001  # Placeholder
            prompts = await run_agent(new_images_prompt, generate_prompt, new_json=new_json, image_file=image_file)
            cost_tracking["prompt_generator"]["cost"] = 0.001  # Placeholder

            processed_prompts = {}
            if isinstance(prompts, str):
                try:
                    processed_prompts = process_response(prompts)
                    print(f"DEBUG - Processed prompts string: {processed_prompts[:200] if processed_prompts else 'EMPTY'}")  # Show first 200 chars
                    processed_prompts = json.loads(processed_prompts)
                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError when parsing prompts: {e}")
                    print(f"DEBUG - Raw prompts response: {prompts[:500] if prompts else 'EMPTY'}")  # Show first 500 chars
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

            # Ensure every image entry knows which original URL it should replace
            fill_missing_original_urls(image_data, parsed_new_question)

            if len(image_data) > 0:
                print(f"Entering loop for image generation. Number of images: {len(image_data)}")
                import asyncio
                for i, p in enumerate(image_data):
                    # Add a check for 'prompt' key in each item
                    if "prompt" in p and p["prompt"]:
                        try:
                            # Add delay between requests to avoid rate limiting (429 errors)
                            if i > 0:
                                print(f"Waiting 3 seconds before next request to avoid rate limits...")
                                await asyncio.sleep(3)
                            
                            print(f"🎨 Generating SVG {i+1}/{len(image_data)} with prompt: {p['prompt'][:100]}...")
                            svg = await run_agent(new_svg_prompt, generate_svg, prompts=p["prompt"])
                            
                            if not svg or len(svg.strip()) < 50:
                                print(f"⚠️ SVG generation returned empty or very short content. Skipping.")
                                continue
                            
                            cost_tracking["svg_generator"]["cost"] += 0.001  # Placeholder cost per SVG
                            cost_tracking["svg_generator"]["count"] += 1
                            
                            print(f"📝 Processing and uploading SVG...")
                            new_url = await process_and_upload_svg(svg)
                            
                            if not new_url or not new_url.startswith("http"):
                                print(f"⚠️ Invalid image URL received: {new_url}. Skipping.")
                                continue
                            
                            # Store both original_url (to find what to replace) and new_url (what to replace with)
                            p["new_url"] = new_url
                            if "original_url" not in p:
                                print(f"⚠️ Warning: original_url not found in image_data item: {p}")
                            else:
                                print(f"✅ Image ready: {p['original_url'][:50]}... -> {new_url[:50]}...")
                        except Exception as svg_error:
                            error_msg = str(svg_error)
                            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                                print(f"⚠️ Rate limit error (429) for image {i+1}/{len(image_data)}. Skipping this image.")
                                print("   This is a temporary Google API limit. Wait a few minutes and try again.")
                                # Skip this image but continue with others
                                continue
                            else:
                                print(f"Error generating SVG for image {i+1}: {svg_error}")
                                # Continue with next image instead of failing completely
                                continue
                    else:
                        print(f"Skipping SVG generation for item due to missing or empty 'prompt' key: {p}")
                
                # Update processed_prompts with the potentially modified image_data
                processed_prompts["image_data"] = image_data
                
                # Count successful image replacements
                images_with_urls = [p for p in image_data if "new_url" in p and p["new_url"]]
                print(f"📊 Image Summary: {len(images_with_urls)}/{len(image_data)} images successfully generated and uploaded")
                
                if len(images_with_urls) == 0:
                    print("⚠️ No images were successfully generated. The question will have missing images.")
                
                response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, prompts=processed_prompts)
                cost_tracking["json_rebuilder"]["cost"] = 0.001  # Placeholder
            else:
                print("No image data found or prompts is empty, skipping SVG generation loop.")
                # Pass an empty JSON object for prompts when no image data is found
                response = await run_agent(rebuild_json_prompt, rebuild_json, new_json=new_json, prompts=json.dumps({}))
                cost_tracking["json_rebuilder"]["cost"] = 0.001  # Placeholder
            
            # Calculate total cost
            cost_tracking["total_cost"] = (
                cost_tracking["question_generator"]["cost"] +
                cost_tracking["prompt_generator"]["cost"] +
                cost_tracking["svg_generator"]["cost"] +
                cost_tracking["json_rebuilder"]["cost"]
            )
            
            return process_response(response), cost_tracking
        except Exception as e:
            print(f"The following error occured: {e}")
            import traceback
            traceback.print_exc()
            return None, None  # Return None tuple on error

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
        if not filename:
            print(f"Error: Failed to capture screenshot for question {source_question_id}")
            raise Exception(f"Screenshot capture failed for question {source_question_id}")
        
        print(f"Screenshot saved at: {filename}")
        image_file = open(filename, "rb").read()
        if question: 
            response = None
            cost_tracking = None
            try:
                response, cost_tracking = await generate_questions(data=question, image_file=image_file)
            except Exception as e:
                print(f"Error during question generation: {e}")
                import traceback
                traceback.print_exc()
                response = None
                cost_tracking = None
            
            if response:
                url = f"http://localhost:8001/api/save-generated-question/{source_question_id}"
                try:
                    # Include cost tracking in the request
                    import json as json_lib
                    data_to_send = json_lib.loads(response) if isinstance(response, str) else response
                    if cost_tracking:
                        data_to_send["generation_cost"] = cost_tracking["total_cost"]
                        data_to_send["cost_breakdown"] = cost_tracking
                        data_to_send["tokens_used"] = {
                            "question_generator": cost_tracking["question_generator"]["tokens"],
                            "prompt_generator": cost_tracking["prompt_generator"]["tokens"],
                            "svg_generator": cost_tracking["svg_generator"]["tokens"],
                            "json_rebuilder": cost_tracking["json_rebuilder"]["tokens"]
                        }
                    api_response = requests.post(url, json=data_to_send)
                    print(f"Saved generated question. Cost: ${cost_tracking['total_cost']:.4f} USD" if cost_tracking else "Saved generated question")
                    print(f"API Response: {api_response.status_code}")
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

