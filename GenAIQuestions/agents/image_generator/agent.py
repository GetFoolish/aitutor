from typing import List
import os 
from time import sleep
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import uuid 
from pathlib import Path
from dotenv import load_dotenv 
from imagekitio import ImageKit 
from google import genai  
from google.genai import types
from PIL import Image
from io import BytesIO

BASE_URL=Path(__file__).resolve().parents[3]
USER_ID="sherlockED"
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

load_dotenv()

def upload_to_imagekit(image_name,image_path):
    #  Put essential values of keys [UrlEndpoint, PrivateKey, PublicKey]
    imagekit = ImageKit(
        private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
        public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
        url_endpoint=os.getenv("IMAGEKIT_URL_ENDPOINT")
    )
    upload = imagekit.upload_file(
            file=open(image_path,"rb"),
            file_name=image_name,
            options=UploadFileRequestOptions(
                response_fields=["is_private_file", "tags"],
                tags=["tag1", "tag2"]
            )
        )     
    image_url = imagekit.url({"path": upload.file_path})
    return image_url


def generate_images(prompts: List[str]) -> List[str]:
    """
    Function for generating images with Nano Banana.

    Args:
        prompts(List[str])  -> A list of prompts for each image needed

    Return:
        dict           -> of image data (alt and urls)

    Example:
        resp = generate_image(["6 identical cartoon flowers in a grid, no stem, same colors, no borders, background color #f0f0f0"])
        print(resp)
        ...

        Output:
        ['https://ik.imagekit.io/20z1p1q07/7c96b3c3-2209-455d-9a34-b2b037b59073.png']
    """
    client = genai.Client(
        api_key=GOOGLE_API_KEY
    )
    data = {}
    print("Generating images...")
    for i, prompt in enumerate(prompts):
        if prompt == prompts[i-1] and i != 0:
            data["url"].append(data["url"][-1]) # repeat the last url
            continue
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                ),
            )
            
            # Check if response has candidates and content
            if not response.candidates:
                print(f"No candidates in response for prompt: {prompt}")
                continue
                
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                print(f"No content parts in response for prompt: {prompt}")
                continue
            
            # Find the image part
            image_data = None
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                    break 
                if part.function_call:
                    print("Function call: {part.function_call.name}\nArgs: {part.function_call.args}")
                if part.text:
                    pass
            
            if not image_data:
                print(f"No image data found in response for prompt: {prompt}")
                # Print available parts for debugging
                print(f"Available parts: {[type(part).__name__ for part in candidate.content.parts]}")
                continue
            
            # Process the image
            image = Image.open(BytesIO(image_data))
            image_name = f"{str(uuid.uuid4())}.png"
            image_file = f"{str(BASE_URL)}/assets/{image_name}"
            image.save(image_file)
            sleep(2)
            
            url = upload_to_imagekit(image_name, image_file) 
            data["url"] = data.get("url", [])
            data["prompts"] = data.get("prompts", [])
            data["url"].append(url)
            data["prompts"].append(prompt)
            print(f"Successfully generated and uploaded image: {url}")
            
        except Exception as e:
            print(f"Error generating image for prompt '{prompt}': {e}")
            # Continue with next prompt instead of failing completely
            continue
            
    return data