import os
import json
import time
import requests
import base64
import io
import random
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from PIL import Image

# ✅ NEW SDK IMPORT
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_TO_AZURE = False
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
API_BASE_URL = os.getenv("API_BASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Azure setup
blob_service_client = None
if UPLOAD_TO_AZURE and AZURE_CONNECTION_STRING:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    except Exception as e:
        print(f"Error connecting to Azure: {e}")

# Initialize New GenAI Client
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)
else:
    print("⚠️ Warning: GOOGLE_API_KEY not found in .env file")

# Folders
OUTPUT_FOLDER = "./new_questions"
LOCAL_ASSETS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'public', 'assets'))

# API Endpoints
GET_QUESTION_URL = f"{API_BASE_URL}/get-question-for-generation"
SAVE_QUESTION_URL = f"{API_BASE_URL}/save-generated-question"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

PROMPT_TEMPLATE = """
we need to regenerate the questions in a new way but the structure must remain the same.
You can change the values.

We are using images and widgets, so please add detailed alt texts suitable for image-generation prompts.
Do not add any extra unnecessary information. Here is the JSON file; rewrite it in a new way.

If the JSON has choices questions, then you can add an "alt" key inside their objects.

Always make sure alt text is based on the exact requirement — it should guide the AI clearly on what type of image to generate.
You can add more detailed alt text because these are image prompts for AI, so make them richer and more descriptive.

Do thorough research and create high-quality image-generation prompts that clearly help the AI understand what kind of image to produce.

Please also modify the questions slightly — create new variations but keep the structure exactly the same.

Make sure image size should be **256x256** for all images.

The images are appearing too large, so ensure that image descriptions always reflect accurate proportions based on the required size.

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

def generate_json_with_ai(prompt: str) -> str:
    try:
        # Calls Gemini 2.5 Flash for Text
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        raise Exception(f"Gemini Text Gen failed: {e}")

def generate_image_with_gemini(prompt_text: str) -> bytes:
    """
    Generates image using the NEW Google GenAI SDK with Byte Handling Fix
    """
    try:
        response = client.models.generate_content(
            model='gemini-3-pro-image-preview',
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=f"{prompt_text}. Image size: 256x256 pixels, high quality, detailed.")
                    ]
                )
            ]
        )

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
                    return output_buffer.getvalue()

        print("⚠️ No inline image data found in response.")
        return create_placeholder_image()

    except Exception as e:
        print(f"⚠️ Gemini Image Gen failed: {e}")
        return create_placeholder_image()

def replace_image_urls_with_generated_images(obj: Any, container_name: str = "inventory") -> Any:
    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_image_urls_with_generated_images(obj[i], container_name)
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
                            buffer = generate_image_with_gemini(img_data["alt"])
                            blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                            new_url = upload_or_save_image(container_name, blob_name, buffer)
                            content_str = content_str.replace(url, new_url)
                        except Exception:
                            pass
                new_obj["content"] = content_str

            # Content with Markdown images
            elif key == "content" and "alt" in obj:
                content_str = obj["content"]
                markdown_img_regex = r"!\[(.*?)\]\((web\+graphie:\/\/.*?)\)"
                matches = re.findall(markdown_img_regex, content_str)
                for match in matches:
                    try:
                        buffer = generate_image_with_gemini(obj["alt"])
                        blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                        new_url = upload_or_save_image(container_name, blob_name, buffer)
                        content_str = content_str.replace(match[1], new_url)
                    except Exception:
                        pass
                new_obj["content"] = content_str
                continue

            # Background Image
            elif key == "backgroundImage" and isinstance(value, dict) and "url" in value and "alt" in obj:
                try:
                    buffer = generate_image_with_gemini(obj["alt"])
                    blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                    new_url = upload_or_save_image(container_name, blob_name, buffer)
                    new_obj[key] = {**value, "url": new_url}
                except Exception:
                    pass

            # Image URL
            elif key == "imageUrl" and "imageAlt" in obj:
                try:
                    buffer = generate_image_with_gemini(obj["imageAlt"])
                    blob_name = f"{int(time.time()*1000)}-{random.random()}.png"
                    new_url = upload_or_save_image(container_name, blob_name, buffer)
                    new_obj[key] = new_url
                except Exception:
                    pass

            else:
                new_obj[key] = replace_image_urls_with_generated_images(value, container_name)
        
        return new_obj
    return obj

def fetch_question_from_api() -> Optional[Dict]:
    try:
        print("Fetching question from API...")
        response = requests.get(GET_QUESTION_URL)
        if response.status_code == 200:
            question = response.json()
            if question and "question" in question:
                source_question_id = question.get("_id")
                if "_id" in question:
                    del question["_id"]
                print(f"Fetched question ID: {source_question_id}")
                return {"sourceQuestionId": source_question_id, "questionData": question}
        return None
    except Exception as e:
        print(f"Failed to fetch: {e}")
        return None

def save_question_to_api(source_question_id, generated_data):
    try:
        url = f"{SAVE_QUESTION_URL}/{source_question_id}"
        print(f"Saving generated question ID: {source_question_id}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=generated_data, headers=headers)
        print(f"✅ Question saved. Status: {response.status_code}")
    except Exception as e:
        print(f"Failed to save: {e}")

def process_question_from_api(fetched_question):
    source_question_id = fetched_question["sourceQuestionId"]
    question_data = fetched_question["questionData"]

    try:
        question_json = json.dumps(question_data, indent=2)
        prompt = PROMPT_TEMPLATE.replace("{{json}}", question_json)

        print("Generating new question text...")
        response_text = generate_json_with_ai(prompt)
        
        cleaned = response_text.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(cleaned)
            print("Generated valid JSON. Processing images...")

            new_data = replace_image_urls_with_generated_images(parsed)

            # STATUS FIELD (Important for Frontend)
            new_data["status"] = "pending_approval"
            new_data["human_approved"] = False

            save_question_to_api(source_question_id, new_data)

            output_path = os.path.join(OUTPUT_FOLDER, f"question_{source_question_id}.json")
            with open(output_path, "w") as f:
                json.dump(new_data, f, indent=2)
            print(f"Local backup saved: {output_path}")

        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")

    except Exception as err:
        print(f"Error: {err}")

def main():
    MAX_QUESTIONS = 10
    processed = 0

    while processed < MAX_QUESTIONS:
        print(f"\n▶️ Fetching question {processed + 1} of {MAX_QUESTIONS}")
        fetched_question = fetch_question_from_api()

        if not fetched_question or not fetched_question.get("questionData"):
            print("❌ No more questions.")
            break

        question_json = json.dumps(fetched_question["questionData"])

        if "https" in question_json or "web+" in question_json:
            print("✔️ Valid question found...")
            process_question_from_api(fetched_question)
            processed += 1
        else:
            print("⚠️ Invalid question, skipping...")
            time.sleep(1.5)
            continue

        time.sleep(1.5)

    print(f"\n🎉 DONE! Processed {processed} questions.")

if __name__ == "__main__":
    main()