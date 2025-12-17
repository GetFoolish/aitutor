import os
import json
import time
import requests
import base64
import io
import random
import re
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from PIL import Image
from app.utils.websocket_manager import manager


# ✅ NEW SDK IMPORT
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# ✅ Setup Logging
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../', 'logs'))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'questionbankgenerator.log')

# Create logger
logger = logging.getLogger('question_generator')
logger.setLevel(logging.INFO)

# Create rotating file handler (max 10MB per file, keep 5 backup files)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Create console handler for backward compatibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("="*80)
logger.info("Question Generator Agent Started")
logger.info(f"Log file: {LOG_FILE}")
logger.info("="*80)

# Configuration
UPLOAD_TO_AZURE = False
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
API_BASE_URL = os.getenv("API_BASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MAX_QUESTIONS = int(os.getenv("MAX_QUESTIONS", 5))
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", 1.5))

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", 256))

# Pricing Configuration (USD per token/image)
# Gemini 2.5 Flash pricing: https://ai.google.dev/pricing
GEMINI_TEXT_INPUT_COST_PER_1M = float(os.getenv("GEMINI_TEXT_INPUT_COST_PER_1M", 0.075))  # $0.075 per 1M input tokens
GEMINI_TEXT_OUTPUT_COST_PER_1M = float(os.getenv("GEMINI_TEXT_OUTPUT_COST_PER_1M", 0.30))  # $0.30 per 1M output tokens
# Gemini 3 Pro Image Preview pricing (estimated, adjust based on actual pricing)
GEMINI_IMAGE_COST_PER_IMAGE = float(os.getenv("GEMINI_IMAGE_COST_PER_IMAGE", 0.04))  # $0.04 per image (estimated)

# Azure setup
blob_service_client = None
if UPLOAD_TO_AZURE and AZURE_CONNECTION_STRING:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    except Exception as e:
        logger.error(f"Error connecting to Azure: {e}")

# Initialize New GenAI Client
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    logger.info("Google GenAI Client initialized successfully")
else:
    logger.warning("GOOGLE_API_KEY not found in .env file")

# Folders
OUTPUT_FOLDER = "./new_questions"
LOCAL_ASSETS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../', 'frontend', 'public', 'assets'))

# API Endpoints
GET_QUESTION_URL = f"{API_BASE_URL}/get-question-for-generation"
SAVE_QUESTION_URL = f"{API_BASE_URL}/save-generated-question"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PROMPT_TEMPLATE = """
You are an expert educational content creator specializing in K-12 math and science education. Your task is to regenerate questions while maintaining the exact same structure and educational quality.

CRITICAL REQUIREMENTS:

1. **Language**: ALL content must be in ENGLISH ONLY. Never use Chinese, Japanese, or any other language characters.

2. **Structure Preservation**:
   - Keep the exact JSON structure - do not add or remove fields
   - Maintain all nested objects and arrays exactly as they are
   - Preserve all widget types (numeric-input, expression, radio, etc.)
   - Keep all technical fields like "type", "options", "widget" unchanged

3. **Content Variation**:
   - Create new variations with different numbers, scenarios, or contexts
   - Maintain the same difficulty level and learning objectives
   - Change the actual values but keep the mathematical concept the same
   - Example: If original uses 2+3, you could use 4+5, but not suddenly switch to multiplication

4. **Image Generation Prompts (CRITICAL)**:
   - For EVERY image URL or reference, you MUST provide detailed "alt" text
   - Alt text must describe EXACTLY what should be in the image
   - Use clear, specific English descriptions
   - Include all details: numbers, labels, colors, arrangements

   GOOD Examples:
   - "Grid of 24 blue circles arranged in 6 rows with 4 circles in each row, evenly spaced on white background"
   - "Number line from 35 to 45 with tick marks at every whole number, number 40 prominently labeled and highlighted in red"
   - "Three apples and two oranges arranged in a horizontal line, clearly separated"

   BAD Examples:
   - "image of circles" (too vague)
   - "[[画像を生成 1]]" (NEVER use non-English text)
   - "a diagram" (not specific enough)

5. **Hints Quality**:
   - Write ALL hints in clear, simple English
   - Hints must be progressive and build on each other
   - Each hint should be more specific than the previous one
   - Never use placeholder text or foreign language characters

   Hint Structure:
   - First hint: Gentle guidance (e.g., "Think about what operation you need to use")
   - Middle hints: More specific (e.g., "Try dividing 24 by 4 to find how many groups")
   - Final hint: Nearly complete solution (e.g., "When you divide 24 into groups of 4, you get 6 groups. This is the answer.")

   If hints need images, provide detailed alt text in English

6. **Widget Placeholders**:
   - Keep widgets as they are: [[☃ numeric-input 1]], [[☃ expression 1]], etc.
   - NEVER replace widgets with foreign language text
   - NEVER write [[画像を生成]] or similar - use proper "alt" text in the image object

7. **Consistency Check**:
   - All numbers in the question must match with hints and answers
   - If question asks about 24 items, hints should reference 24 items
   - Answer choices should include the correct answer based on the question

8. **Educational Value**:
   - Question must be age-appropriate and clear
   - Mathematical concepts must be accurate
   - Language should be simple and direct
   - Avoid ambiguous phrasing

EXAMPLE OF GOOD REGENERATION:
Original: "How many rows if you have 20 apples in groups of 5?"
Regenerated: "If you have 30 oranges and arrange them in groups of 6, how many groups will you have?"
(Same concept of division, different numbers, clear and specific)

Now regenerate this question following ALL the above guidelines. Use ONLY English language:

{{json}}
"""

# --- Functions ---

def create_placeholder_image() -> bytes:
    """Fallback Blue Image"""
    img = Image.new('RGB', (256, 256), color=(73, 109, 137))
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="PNG")
    return output_buffer.getvalue()

def upload_or_save_image(container_name: str, blob_name: str, buffer_data: bytes) -> str:
    if UPLOAD_TO_AZURE and blob_service_client:
        try:
            container_client = blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(buffer_data, content_settings=ContentSettings(content_type='image/png'))
            return blob_client.url
        except Exception as e:
            pass # Fallback to local

    # Save locally
    if not os.path.exists(LOCAL_ASSETS_PATH):
        os.makedirs(LOCAL_ASSETS_PATH, exist_ok=True)
        
    local_file_path = os.path.join(LOCAL_ASSETS_PATH, blob_name)
    with open(local_file_path, "wb") as f:
        f.write(buffer_data)
        
    return f"/assets/{blob_name}"

def generate_json_with_ai(prompt: str) -> tuple[str, Dict]:
    """
    Generate JSON with AI and return the text plus cost/token metadata.
    Returns: (response_text, metadata_dict)
    """
    try:
        # Calls Gemini 2.5 Flash for Text
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt
        )

        # Extract token usage from response
        usage_metadata = response.usage_metadata if hasattr(response, 'usage_metadata') else None
        input_tokens = usage_metadata.prompt_token_count if usage_metadata else 0
        output_tokens = usage_metadata.candidates_token_count if usage_metadata else 0

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * GEMINI_TEXT_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * GEMINI_TEXT_OUTPUT_COST_PER_1M
        total_cost = input_cost + output_cost

        metadata = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
        }

        logger.info(f"Text generation: {input_tokens} input + {output_tokens} output tokens = ${total_cost:.6f}")

        return response.text, metadata
    except Exception as e:
        raise Exception(f"Gemini Text Gen failed: {e}")

def generate_image_with_gemini(prompt_text: str) -> tuple[bytes, float]:
    """
    Generates image using the NEW Google GenAI SDK with Byte Handling Fix.
    Returns: (image_bytes, cost)
    """
    try:
        # Enhanced prompt with better instructions for educational content
        enhanced_prompt = f"""Generate an educational illustration based on this description:

{prompt_text}

Requirements:
- Simple, clear, and easy to understand for students
- Clean white or light background
- Bold lines and clear labels if any
- Professional educational diagram style
- Appropriate for K-12 education
- Size: 256x256 pixels
- High quality, detailed but not cluttered"""

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=enhanced_prompt)
                    ]
                )
            ]
        )

        cost = GEMINI_IMAGE_COST_PER_IMAGE

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    # 🟢 CRITICAL FIX HERE:
                    # Check if data is already bytes or string
                    raw_data = part.inline_data.data

                    if isinstance(raw_data, bytes):
                        # Use directly if bytes (New SDK behavior)
                        image_bytes = raw_data
                    else:
                        # Decode if string (Base64)
                        image_bytes = base64.b64decode(raw_data)

                    # Resize using Pillow
                    image = Image.open(io.BytesIO(image_bytes))
                    image = image.resize((256, 256), Image.Resampling.LANCZOS)

                    output_buffer = io.BytesIO()
                    image.save(output_buffer, format="PNG")
                    logger.info(f"Image generation: ${cost:.4f}")
                    return output_buffer.getvalue(), cost

        logger.warning("No inline image data found in response")
        return create_placeholder_image(), 0.0

    except Exception as e:
        logger.error(f"Gemini Image Gen failed: {e}")
        return create_placeholder_image(), 0.0

def replace_image_urls_with_generated_images(obj: Any, container_name: str = "inventory") -> tuple[Any, Dict]:
    """
    Replace image URLs with generated images and track costs.
    Returns: (modified_obj, cost_stats)
    """
    total_images = 0
    total_image_cost = 0.0

    def replace_recursive(obj: Any) -> Any:
        nonlocal total_images, total_image_cost

        if isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = replace_recursive(obj[i])
            return obj

        elif isinstance(obj, dict):
            new_obj = obj.copy()

            for key, value in obj.items():
                # Content with images object
                if key == "content" and "images" in obj:
                    content_str = obj["content"]
                    for url, img_data in obj["images"].items():
                        if url in content_str and "alt" in img_data:
                            try:
                                logger.info(f"Generating image with alt text: {img_data['alt'][:100]}...")
                                buffer, cost = generate_image_with_gemini(img_data["alt"])
                                total_images += 1
                                total_image_cost += cost
                                blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                                new_url = upload_or_save_image(container_name, blob_name, buffer)
                                content_str = content_str.replace(url, new_url)
                                logger.info(f"Successfully generated and saved image: {blob_name}")
                            except Exception as e:
                                logger.error(f"Failed to generate image: {e}")
                                pass
                    new_obj["content"] = content_str

                # Content with Markdown images
                elif key == "content" and "alt" in obj:
                    content_str = obj["content"]
                    markdown_img_regex = r"!\[(.*?)\]\((web\+graphie:\/\/.*?)\)"
                    matches = re.findall(markdown_img_regex, content_str)
                    for match in matches:
                        try:
                            logger.info(f"Generating markdown image with alt: {obj['alt'][:100]}...")
                            buffer, cost = generate_image_with_gemini(obj["alt"])
                            total_images += 1
                            total_image_cost += cost
                            blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                            new_url = upload_or_save_image(container_name, blob_name, buffer)
                            content_str = content_str.replace(match[1], new_url)
                            logger.info(f"Successfully generated markdown image: {blob_name}")
                        except Exception as e:
                            logger.error(f"Failed to generate markdown image: {e}")
                            pass
                    new_obj["content"] = content_str
                    continue

                # Background Image
                elif key == "backgroundImage" and isinstance(value, dict) and "url" in value and "alt" in obj:
                    try:
                        logger.info(f"Generating background image with alt: {obj['alt'][:100]}...")
                        buffer, cost = generate_image_with_gemini(obj["alt"])
                        total_images += 1
                        total_image_cost += cost
                        blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                        new_url = upload_or_save_image(container_name, blob_name, buffer)
                        new_obj[key] = {**value, "url": new_url}
                        logger.info(f"Successfully generated background image: {blob_name}")
                    except Exception as e:
                        logger.error(f"Failed to generate background image: {e}")
                        pass

                # Image URL
                elif key == "imageUrl" and "imageAlt" in obj:
                    try:
                        logger.info(f"Generating imageUrl with alt: {obj['imageAlt'][:100]}...")
                        buffer, cost = generate_image_with_gemini(obj["imageAlt"])
                        total_images += 1
                        total_image_cost += cost
                        blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                        new_url = upload_or_save_image(container_name, blob_name, buffer)
                        new_obj[key] = new_url
                        logger.info(f"Successfully generated imageUrl: {blob_name}")
                    except Exception as e:
                        logger.error(f"Failed to generate imageUrl: {e}")
                        pass

                else:
                    new_obj[key] = replace_recursive(value)

            return new_obj
        return obj

    modified_obj = replace_recursive(obj)

    cost_stats = {
        "images_generated": total_images,
        "total_cost": round(total_image_cost, 6)
    }

    logger.info(f"Image generation complete: {total_images} images generated, total cost: ${total_image_cost:.6f}")

    return modified_obj, cost_stats

def fetch_question_from_api() -> Optional[Dict]:
    try:
        logger.info("Fetching question from API...")
        response = requests.get(GET_QUESTION_URL)
        if response.status_code == 200:
            question = response.json()
            if question and "question" in question:
                source_question_id = question.get("_id")
                if "_id" in question:
                    del question["_id"]
                logger.info(f"Fetched question ID: {source_question_id}")
                return {"sourceQuestionId": source_question_id, "questionData": question}
        logger.warning(f"Failed to fetch question, status code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch question: {e}", exc_info=True)
        return None

def save_question_to_api(source_question_id, generated_data, cost_metadata=None):
    try:
        # Add cost metadata to the generated data if provided
        if cost_metadata:
            generated_data["generation_cost"] = cost_metadata.get("total_cost", 0.0)
            generated_data["cost_breakdown"] = cost_metadata.get("cost_breakdown", {})
            generated_data["tokens_used"] = cost_metadata.get("tokens_used", {})

        url = f"{SAVE_QUESTION_URL}/{source_question_id}"
        logger.info(f"Saving generated question ID: {source_question_id}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=generated_data, headers=headers)
        logger.info(f"Question saved successfully. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to save question: {e}", exc_info=True)

def process_question_from_api(fetched_question):
    source_question_id = fetched_question["sourceQuestionId"]
    question_data = fetched_question["questionData"]

    try:
        question_json = json.dumps(question_data, indent=2)
        prompt = PROMPT_TEMPLATE.replace("{{json}}", question_json)

        logger.info("Generating new question text with AI...")
        response_text, text_metadata = generate_json_with_ai(prompt)

        cleaned = response_text.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(cleaned)
            logger.info("Generated valid JSON. Processing images...")

            new_data, image_cost_stats = replace_image_urls_with_generated_images(parsed)

            # STATUS FIELD (Important for Frontend)
            new_data["status"] = "pending_approval"
            new_data["human_approved"] = False

            # Aggregate all costs
            total_cost = text_metadata["total_cost"] + image_cost_stats["total_cost"]

            cost_metadata = {
                "total_cost": round(total_cost, 6),
                "cost_breakdown": {
                    "text_generation": {
                        "model": TEXT_MODEL,
                        "cost": text_metadata["total_cost"],
                        "input_cost": text_metadata["input_cost"],
                        "output_cost": text_metadata["output_cost"]
                    },
                    "image_generation": {
                        "model": IMAGE_MODEL,
                        "cost": image_cost_stats["total_cost"],
                        "images_count": image_cost_stats["images_generated"]
                    }
                },
                "tokens_used": {
                    "input_tokens": text_metadata["input_tokens"],
                    "output_tokens": text_metadata["output_tokens"],
                    "total_tokens": text_metadata["total_tokens"]
                }
            }

            logger.info(f"Total generation cost: ${total_cost:.6f} (Text: ${text_metadata['total_cost']:.6f}, Images: ${image_cost_stats['total_cost']:.6f})")

            save_question_to_api(source_question_id, new_data, cost_metadata)

            output_path = os.path.join(OUTPUT_FOLDER, f"question_{source_question_id}.json")
            with open(output_path, "w") as f:
                json.dump(new_data, f, indent=2)
            logger.info(f"Local backup saved: {output_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")

    except Exception as err:
        logger.error(f"Error processing question: {err}", exc_info=True)

async def generate_new_questions(limit: int = 0):
    env_limit = int(os.getenv("MAX_QUESTIONS", 1))
    max_questions = limit if limit > 0 else env_limit
    processed = 0

    logger.info(f"Starting question generation batch. Max questions: {max_questions}")
    await manager.broadcast({"status": "starting", "total": max_questions})

    while processed < max_questions:
        logger.info(f"Fetching question {processed + 1} of {max_questions}")
        await manager.broadcast({"status": "fetching", "current": processed + 1, "total": max_questions})

        fetched_question = await asyncio.to_thread(fetch_question_from_api)
        if not fetched_question or not fetched_question.get("questionData"):
            logger.warning("No more questions available to process")
            await manager.broadcast({"status": "done", "message": "No more questions to process."})
            break

        question_json = json.dumps(fetched_question["questionData"])
        if "https" in question_json or "web+" in question_json:
            logger.info(f"Valid question found. Processing question {processed + 1}...")
            await manager.broadcast({"status": "processing", "current": processed + 1, "total": max_questions})
            await asyncio.to_thread(process_question_from_api, fetched_question)
            processed += 1
            logger.info(f"Successfully processed question {processed}/{max_questions}")
            await manager.broadcast({"status": "processed", "current": processed, "total": max_questions})
        else:
            logger.warning("Invalid question (no images/URLs), skipping...")
            await manager.broadcast({"status": "skipping", "current": processed + 1, "total": max_questions})
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    logger.info(f"Question generation batch completed! Processed {processed}/{max_questions} questions")
    await manager.broadcast({"status": "done", "processed": processed, "total": max_questions})

if __name__ == "__main__":
    asyncio.run(generate_new_questions())