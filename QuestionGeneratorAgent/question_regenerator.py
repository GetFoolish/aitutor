"""
Question Regenerator - Rewrites questions with new numbers and generates new images.

This module:
1. Takes an existing question with images
2. Uses LLM to rewrite the question with different (easier) numbers
3. Uses image generation API to create new images matching the new numbers
4. Returns the complete rewritten question with new images

IMPORTANT: API calls require explicit user permission before execution.
"""

import json
import random
import base64
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from QuestionGeneratorAgent.logging_config import get_logger

logger = get_logger(__name__)


def safe_print(text: str):
    """Print text safely, replacing any problematic Unicode characters."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic characters with their representation
        print(text.encode('ascii', 'replace').decode('ascii'))


@dataclass
class RegeneratedQuestion:
    """A question that has been regenerated with new numbers and images."""
    original_file: str
    original_content: str
    original_images: List[Dict[str, Any]]
    original_answer: Any

    new_content: str
    new_images: List[Dict[str, Any]]  # Each has 'url' or 'base64', 'alt'
    new_answer: Any

    question_type: str
    changes_made: Dict[str, Any] = field(default_factory=dict)


class APIClient(ABC):
    """Base class for API clients."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._enabled = False

    def enable(self):
        """Enable API calls - requires explicit permission."""
        self._enabled = True
        logger.info(f"{self.__class__.__name__} API calls ENABLED")

    def disable(self):
        """Disable API calls."""
        self._enabled = False
        logger.info(f"{self.__class__.__name__} API calls DISABLED")

    @property
    def is_enabled(self) -> bool:
        return self._enabled


class OpenRouterClient(APIClient):
    """Client for OpenRouter API - handles text generation."""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://openrouter.ai/api/v1/chat/completions")
        self.model = "anthropic/claude-3-haiku"

    def generate_text(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Generate text using OpenRouter. Returns None if disabled."""
        if not self._enabled:
            logger.warning("OpenRouter API calls are DISABLED. Call enable() first with user permission.")
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Clean the API key - remove "Bearer " prefix if user included it
        clean_key = self.api_key.strip()
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:]

        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Question Regenerator"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        safe_print("\n" + "=" * 60)
        safe_print("[OPENROUTER PROMPT]")
        safe_print("=" * 60)
        safe_print(f"Model: {self.model}")
        if system_prompt:
            safe_print(f"\nSYSTEM:\n{system_prompt[:500]}...")
        safe_print(f"\nUSER:\n{prompt[:500]}...")
        safe_print("=" * 60)

        logger.debug(f"OpenRouter request to {self.model}")

        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        response_text = result['choices'][0]['message']['content']

        safe_print("\n[OPENROUTER RESPONSE]")
        safe_print("-" * 60)
        safe_print(f"{response_text[:500]}...")
        safe_print("-" * 60 + "\n")

        return response_text

    def generate_image_prompt(self, original_alt: str, new_count: int, item_type: str) -> Optional[str]:
        """Generate an image generation prompt based on the original alt text."""
        if not self._enabled:
            return None

        prompt = f"""Create a simple, clear image generation prompt for an educational math image.

Original image description: {original_alt}
New count needed: {new_count}
Item type: {item_type}

Generate a prompt for DALL-E that will create a simple, child-friendly educational image showing exactly {new_count} {item_type}.
The image should be:
- Simple and clear
- Suitable for elementary math education
- Easy to count
- Similar style to the original (educational, clean)

Return ONLY the image prompt, nothing else."""

        return self.generate_text(prompt)


class ImageGeneratorClient(APIClient):
    """Client for image generation using Nano Banana (Gemini 2.5 Flash Image) via OpenRouter."""

    def __init__(self, api_key: str):
        # Nano Banana uses chat completions endpoint for image generation
        super().__init__(api_key, "https://openrouter.ai/api/v1/chat/completions")
        self.model = "google/gemini-2.5-flash-image-preview"  # Nano Banana

    def generate_image(self, prompt: str, size: str = "256x256") -> Optional[str]:
        """Generate an image from prompt using Nano Banana. Returns base64 image data or URL."""
        if not self._enabled:
            logger.warning("Image generation API calls are DISABLED. Call enable() first with user permission.")
            return None

        # Clean the API key
        clean_key = self.api_key.strip()
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:]

        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Question Regenerator"
        }

        # Nano Banana generates images via chat completions with image output
        # Content must be an array with type/text objects
        payload = {
            "model": self.model,
            "modalities": ["text", "image"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Generate an image: {prompt}"
                        }
                    ]
                }
            ]
        }

        logger.info(f"Generating image with Nano Banana: {prompt[:100]}...")

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Nano Banana response keys: {result.keys()}")

            # Extract image from response - check the message
            message = result.get('choices', [{}])[0].get('message', {})
            logger.debug(f"Message keys: {message.keys()}")

            # Check for 'images' field directly in message (OpenRouter Nano Banana format)
            if 'images' in message:
                images = message['images']
                logger.debug(f"Found {len(images)} images in message")
                if images and len(images) > 0:
                    img = images[0]
                    # img can be {"type": "image_url", "image_url": {"url": "data:..."}}
                    if isinstance(img, dict):
                        if img.get('type') == 'image_url':
                            url = img.get('image_url', {}).get('url', '')
                            if url:
                                logger.info(f"Got image URL (length: {len(url)})")
                                return url
                        # Or it might be direct data
                        if 'url' in img:
                            return img['url']
                        if 'data' in img:
                            mime = img.get('mime_type', 'image/png')
                            return f"data:{mime};base64,{img['data']}"
                    elif isinstance(img, str):
                        return img

            # Fallback: check content array
            content = message.get('content', [])
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        if part.get('type') == 'image_url':
                            return part.get('image_url', {}).get('url', '')
                        if part.get('type') == 'image' or 'inline_data' in part:
                            inline = part.get('inline_data', part.get('image', {}))
                            if isinstance(inline, dict) and 'data' in inline:
                                mime = inline.get('mime_type', 'image/png')
                                return f"data:{mime};base64,{inline['data']}"
            elif isinstance(content, str) and content.startswith('data:image'):
                return content

            # If no image found, return placeholder
            logger.warning(f"No image extracted from API response")
            return self._generate_placeholder_svg(prompt)

        except requests.exceptions.HTTPError as e:
            logger.error(f"Image generation HTTP error: {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            return self._generate_placeholder_svg(prompt)
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return self._generate_placeholder_svg(prompt)

    def _generate_placeholder_svg(self, prompt: str) -> str:
        """Generate a placeholder SVG for testing."""
        # Extract count from prompt if possible
        import re
        count_match = re.search(r'(\d+)', prompt)
        count = int(count_match.group(1)) if count_match else 5

        # Create simple SVG with circles representing items
        circles = ""
        cols = min(count, 5)
        for i in range(count):
            row = i // cols
            col = i % cols
            x = 30 + col * 40
            y = 30 + row * 40
            circles += f'<circle cx="{x}" cy="{y}" r="15" fill="#4CAF50" stroke="#2E7D32" stroke-width="2"/>'

        height = 60 + ((count - 1) // cols) * 40
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="{height}" viewBox="0 0 220 {height}">
            <rect width="100%" height="100%" fill="#f5f5f5"/>
            {circles}
            <text x="110" y="{height - 10}" text-anchor="middle" font-size="12" fill="#666">Count: {count}</text>
        </svg>'''

        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


class QuestionRegenerator:
    """
    Regenerates questions with new numbers and images.

    IMPORTANT: API calls are disabled by default.
    Call enable_apis() with explicit user permission before using.
    """

    def __init__(self, openrouter_key: str):
        self.text_client = OpenRouterClient(openrouter_key)
        self.image_client = ImageGeneratorClient(openrouter_key)
        self._apis_enabled = False

        logger.info("QuestionRegenerator initialized (APIs DISABLED)")

    def enable_apis(self):
        """Enable API calls - REQUIRES EXPLICIT USER PERMISSION."""
        self.text_client.enable()
        self.image_client.enable()
        self._apis_enabled = True
        logger.warning("APIs ENABLED - will make real API calls!")

    def disable_apis(self):
        """Disable API calls."""
        self.text_client.disable()
        self.image_client.disable()
        self._apis_enabled = False
        logger.info("APIs DISABLED")

    def regenerate_question(self, question_data: Dict[str, Any],
                           target_difficulty: str = "easier") -> Optional[RegeneratedQuestion]:
        """
        Regenerate a question with new numbers and images.

        Args:
            question_data: Original question JSON
            target_difficulty: "easier", "same", or "harder"

        Returns:
            RegeneratedQuestion or None if APIs disabled
        """
        if not self._apis_enabled:
            logger.warning("APIs are disabled. Call enable_apis() with user permission first.")
            return self._generate_preview(question_data, target_difficulty)

        # Extract original info
        question = question_data.get('question', {})
        content = question.get('content', '')
        widgets = question.get('widgets', {})

        # Get images and answers
        images = []
        answers = {}
        for name, widget in widgets.items():
            if widget.get('type') == 'image':
                opts = widget.get('options', {})
                images.append({
                    'name': name,
                    'alt': opts.get('alt', ''),
                    'url': opts.get('backgroundImage', {}).get('url', '')
                })
            elif widget.get('type') == 'numeric-input':
                ans_list = widget.get('options', {}).get('answers', [])
                for ans in ans_list:
                    if ans.get('status') == 'correct':
                        answers[name] = ans.get('value')

        # Detect question type and generate new numbers
        q_type = self._detect_question_type(images, content)
        new_numbers = self._generate_new_numbers(q_type, answers, target_difficulty)

        # Use LLM to rewrite question text
        new_content = self._rewrite_question_text(content, images, new_numbers)

        # Generate new images
        new_images = self._generate_new_images(images, new_numbers, q_type)

        return RegeneratedQuestion(
            original_file=question_data.get('_file_name', 'unknown'),
            original_content=content,
            original_images=images,
            original_answer=answers,
            new_content=new_content,
            new_images=new_images,
            new_answer=new_numbers.get('answer'),
            question_type=q_type,
            changes_made=new_numbers
        )

    def _generate_preview(self, question_data: Dict[str, Any],
                         target_difficulty: str) -> RegeneratedQuestion:
        """Generate a preview without making API calls."""
        question = question_data.get('question', {})
        content = question.get('content', '')
        widgets = question.get('widgets', {})

        images = []
        answers = {}
        for name, widget in widgets.items():
            if widget.get('type') == 'image':
                opts = widget.get('options', {})
                images.append({
                    'name': name,
                    'alt': opts.get('alt', ''),
                    'url': opts.get('backgroundImage', {}).get('url', '')
                })
            elif widget.get('type') == 'numeric-input':
                ans_list = widget.get('options', {}).get('answers', [])
                for ans in ans_list:
                    if ans.get('status') == 'correct':
                        answers[name] = ans.get('value')

        q_type = self._detect_question_type(images, content)
        new_numbers = self._generate_new_numbers(q_type, answers, target_difficulty)

        # Preview: show what WOULD be generated
        preview_content = f"[PREVIEW - APIs DISABLED]\n\nOriginal: {content[:200]}...\n\nWould rewrite with: {new_numbers}"

        preview_images = []
        for img in images:
            preview_images.append({
                'name': img['name'],
                'alt': f"[WOULD GENERATE: {new_numbers.get('per_group', '?')} items]",
                'url': self.image_client._generate_placeholder_svg(f"{new_numbers.get('per_group', 5)} items")
            })

        return RegeneratedQuestion(
            original_file=question_data.get('_file_name', 'unknown'),
            original_content=content,
            original_images=images,
            original_answer=answers,
            new_content=preview_content,
            new_images=preview_images,
            new_answer=new_numbers.get('answer'),
            question_type=q_type,
            changes_made=new_numbers
        )

    def _detect_question_type(self, images: List[Dict], content: str) -> str:
        """Detect the type of question."""
        image_text = " ".join(img.get('alt', '').lower() for img in images)

        if any(word in image_text for word in ['thousands', 'hundreds', 'tens', 'ones', 'block']):
            return 'place_value'
        elif any(word in image_text for word in ['group', 'seals', 'monkeys', 'sheep', 'birds']):
            return 'counting'
        return 'other'

    def _generate_new_numbers(self, q_type: str, original_answers: Dict,
                             difficulty: str) -> Dict[str, Any]:
        """Generate new numbers based on difficulty."""

        # Get original values
        original_values = list(original_answers.values())

        if q_type == 'counting':
            # For counting: reduce the number of items per group
            if difficulty == "easier":
                per_group = random.randint(2, 4)  # Easier: 2-4 items
                num_groups = random.randint(2, 4)  # Fewer groups
            else:
                per_group = random.randint(5, 9)
                num_groups = random.randint(4, 7)

            return {
                'per_group': per_group,
                'num_groups': num_groups,
                'answer': per_group * num_groups,
                'item_answer': per_group
            }

        elif q_type == 'place_value':
            if difficulty == "easier":
                # Easier: smaller numbers, fewer place values
                thousands = random.randint(1, 3)
                hundreds = random.randint(0, 2)
                tens = random.randint(0, 3)
                ones = random.randint(0, 5)
            else:
                thousands = random.randint(1, 9)
                hundreds = random.randint(0, 9)
                tens = random.randint(0, 9)
                ones = random.randint(0, 9)

            answer = thousands * 1000 + hundreds * 100 + tens * 10 + ones
            return {
                'thousands': thousands,
                'hundreds': hundreds,
                'tens': tens,
                'ones': ones,
                'answer': answer
            }

        return {'answer': original_values[0] if original_values else 0}

    def _rewrite_question_text(self, original_content: str,
                               images: List[Dict], new_numbers: Dict) -> str:
        """Use LLM to rewrite the question text with new numbers."""
        if not self.text_client.is_enabled:
            return f"[WOULD REWRITE]\n{original_content}"

        system_prompt = """You are rewriting educational math questions.
Keep the same structure and format, but change the numbers to match the new values provided.
Keep all [[☃ widget]] placeholders exactly as they are.
Return ONLY the rewritten question content, nothing else."""

        prompt = f"""Rewrite this question with the new numbers:

Original question:
{original_content}

New numbers to use:
{json.dumps(new_numbers, indent=2)}

Image descriptions (for context):
{json.dumps([img.get('alt', '') for img in images], indent=2)}

Rewrite the question to use these new numbers while keeping the same format and all [[☃ ...]] placeholders."""

        result = self.text_client.generate_text(prompt, system_prompt)
        return result if result else original_content

    def _generate_new_images(self, original_images: List[Dict],
                            new_numbers: Dict, q_type: str) -> List[Dict]:
        """Generate new images matching the new numbers.

        Generates ONE SVG image and reuses it for all image slots.
        """
        new_images = []

        if not original_images:
            return new_images

        # Handle place value questions differently
        if q_type == 'place_value':
            thousands = new_numbers.get('thousands', 0)
            hundreds = new_numbers.get('hundreds', 0)
            tens = new_numbers.get('tens', 0)
            ones = new_numbers.get('ones', 0)

            single_image_url = self._generate_place_value_svg(thousands, hundreds, tens, ones)
            alt_text = f"{thousands} thousands, {hundreds} hundreds, {tens} tens, {ones} ones"

            for img in original_images:
                new_images.append({
                    'name': img['name'],
                    'alt': alt_text,
                    'url': single_image_url
                })
            return new_images

        # For counting questions: get count and item type
        count = new_numbers.get('per_group', new_numbers.get('answer', 5))
        first_alt = original_images[0].get('alt', '').lower()
        item = 'items'
        for word in ['seals', 'monkeys', 'sheep', 'birds', 'fish', 'apples']:
            if word in first_alt:
                item = word
                break

        # Generate SVG directly (no API call needed for images)
        single_image_url = self._generate_animal_svg(count, item)

        # Reuse the same image for all slots
        for img in original_images:
            new_images.append({
                'name': img['name'],
                'alt': f"{count} {item}",
                'url': single_image_url
            })

        return new_images

    def _generate_animal_svg(self, count: int, animal: str) -> str:
        """Generate an SVG with the specified number of animals."""
        # Simple animal shapes
        animals = {
            'seals': '<ellipse cx="25" cy="20" rx="20" ry="12" fill="#5BA3C0"/><circle cx="35" cy="15" r="6" fill="#5BA3C0"/><circle cx="37" cy="13" r="1.5" fill="#333"/><ellipse cx="10" cy="25" rx="8" ry="4" fill="#5BA3C0" transform="rotate(-30 10 25)"/>',
            'monkeys': '<circle cx="25" cy="18" r="12" fill="#8B4513"/><circle cx="25" cy="22" r="8" fill="#DEB887"/><circle cx="22" cy="18" r="2" fill="#333"/><circle cx="28" cy="18" r="2" fill="#333"/><ellipse cx="25" cy="24" rx="3" ry="2" fill="#8B4513"/><circle cx="12" cy="15" r="5" fill="#DEB887"/><circle cx="38" cy="15" r="5" fill="#DEB887"/>',
            'sheep': '<ellipse cx="25" cy="22" rx="18" ry="12" fill="#F5F5F5"/><circle cx="25" cy="22" r="10" fill="#FFF"/><circle cx="30" cy="12" r="8" fill="#FFF"/><circle cx="32" cy="10" r="2" fill="#333"/><rect x="18" y="32" width="4" height="8" fill="#333"/><rect x="28" y="32" width="4" height="8" fill="#333"/>',
            'birds': '<ellipse cx="25" cy="20" rx="15" ry="10" fill="#FFD700"/><circle cx="35" cy="15" r="7" fill="#FFD700"/><circle cx="37" cy="13" r="2" fill="#333"/><polygon points="42,15 50,15 42,18" fill="#FF6B00"/><path d="M 10 20 Q 5 15 10 25" fill="#FFD700"/>',
            'fish': '<ellipse cx="25" cy="20" rx="18" ry="10" fill="#FF6B6B"/><polygon points="5,20 -5,10 -5,30" fill="#FF6B6B"/><circle cx="35" cy="17" r="3" fill="#333"/><path d="M 15 15 Q 20 20 15 25" stroke="#FF8888" fill="none" stroke-width="2"/>',
            'apples': '<circle cx="25" cy="22" r="15" fill="#FF4444"/><ellipse cx="25" cy="8" rx="3" ry="5" fill="#228B22"/><rect x="23" y="5" width="4" height="8" fill="#8B4513"/>',
            'items': '<circle cx="25" cy="20" r="15" fill="#4CAF50"/>'
        }

        shape = animals.get(animal, animals['items'])

        # Calculate layout
        cols = min(count, 4)
        rows = (count + cols - 1) // cols
        cell_width = 60
        cell_height = 50
        width = cols * cell_width + 20
        height = rows * cell_height + 20

        # Build SVG
        items_svg = ""
        for i in range(count):
            row = i // cols
            col = i % cols
            x = 10 + col * cell_width
            y = 10 + row * cell_height
            items_svg += f'<g transform="translate({x},{y})">{shape}</g>'

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
{items_svg}
</svg>'''

        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    def _generate_place_value_svg(self, thousands: int, hundreds: int, tens: int, ones: int) -> str:
        """Generate an SVG showing place value blocks (base-10 blocks).

        - Thousands: large 3D cubes (green)
        - Hundreds: flat squares (blue)
        - Tens: vertical rods (orange)
        - Ones: small unit cubes (yellow)
        """
        items_svg = ""
        x_offset = 10

        # Thousands blocks (large 3D cubes) - green
        for i in range(thousands):
            x = x_offset + i * 55
            # 3D cube effect
            items_svg += f'''<g transform="translate({x}, 10)">
                <polygon points="0,15 25,0 50,15 25,30" fill="#2E7D32"/>
                <polygon points="0,15 0,55 25,70 25,30" fill="#388E3C"/>
                <polygon points="25,30 25,70 50,55 50,15" fill="#4CAF50"/>
                <line x1="0" y1="15" x2="0" y2="55" stroke="#1B5E20" stroke-width="1"/>
                <line x1="25" y1="30" x2="25" y2="70" stroke="#1B5E20" stroke-width="1"/>
                <line x1="50" y1="15" x2="50" y2="55" stroke="#1B5E20" stroke-width="1"/>
            </g>'''
        if thousands > 0:
            x_offset += thousands * 55 + 15

        # Hundreds blocks (flat squares) - blue
        for i in range(hundreds):
            row = i // 3
            col = i % 3
            x = x_offset + col * 45
            y = 10 + row * 45
            items_svg += f'''<g transform="translate({x}, {y})">
                <rect width="40" height="40" fill="#1976D2" stroke="#0D47A1" stroke-width="1"/>
                <line x1="0" y1="10" x2="40" y2="10" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="20" x2="40" y2="20" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="30" x2="40" y2="30" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
                <line x1="10" y1="0" x2="10" y2="40" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
                <line x1="20" y1="0" x2="20" y2="40" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
                <line x1="30" y1="0" x2="30" y2="40" stroke="#0D47A1" stroke-width="0.5" opacity="0.5"/>
            </g>'''
        if hundreds > 0:
            cols_used = min(hundreds, 3)
            x_offset += cols_used * 45 + 15

        # Tens blocks (vertical rods) - orange
        for i in range(tens):
            x = x_offset + i * 12
            items_svg += f'''<g transform="translate({x}, 10)">
                <rect width="10" height="60" fill="#FF9800" stroke="#E65100" stroke-width="1"/>
                <line x1="0" y1="6" x2="10" y2="6" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="12" x2="10" y2="12" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="18" x2="10" y2="18" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="24" x2="10" y2="24" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="30" x2="10" y2="30" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="36" x2="10" y2="36" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="42" x2="10" y2="42" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="48" x2="10" y2="48" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
                <line x1="0" y1="54" x2="10" y2="54" stroke="#E65100" stroke-width="0.5" opacity="0.5"/>
            </g>'''
        if tens > 0:
            x_offset += tens * 12 + 15

        # Ones blocks (small unit cubes) - yellow
        for i in range(ones):
            row = i // 5
            col = i % 5
            x = x_offset + col * 14
            y = 50 + row * 14
            items_svg += f'''<rect x="{x}" y="{y}" width="12" height="12" fill="#FDD835" stroke="#F9A825" stroke-width="1"/>'''

        # Calculate total width
        total_width = x_offset + (min(ones, 5) * 14 if ones > 0 else 0) + 20
        total_width = max(total_width, 100)  # Minimum width
        height = 100

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" viewBox="0 0 {total_width} {height}">
<rect width="100%" height="100%" fill="white"/>
{items_svg}
</svg>'''

        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# Convenience function
def create_regenerator(api_key: str) -> QuestionRegenerator:
    """Create a QuestionRegenerator instance. APIs are disabled by default."""
    return QuestionRegenerator(api_key)
