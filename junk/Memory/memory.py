"""
Simple Gemini Text Generation
Reads conversation JSON and sends to LLM with single request
"""

import os
import json
from datetime import datetime
from google import genai
from google.genai import types

# API Key setup
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    # Fallback API key (replace with your own)
    api_key = "AIzaSyAqeEM31IrxFhB65dDWSYCtdu433Wg1NTw"

# Initialize Gemini client
client = genai.Client(api_key=api_key)

# Folder structure setup
BASE_DIR = "student"
LAST_CONV_FILE = os.path.join(
    BASE_DIR, "conversation", "last_conversation", "conversation.json"
)
CURRENT_MEMORY_DIR = os.path.join(BASE_DIR, "memory", "current_memory")
ALL_MEMORY_DIR = os.path.join(BASE_DIR, "memory", "all_memory")

# Create directories if they don't exist
os.makedirs(CURRENT_MEMORY_DIR, exist_ok=True)
os.makedirs(ALL_MEMORY_DIR, exist_ok=True)

# File paths
CURRENT_MEMORY_FILE = os.path.join(CURRENT_MEMORY_DIR, "memory.json")

# Base system instruction - will be enhanced with previous memory
BASE_SYSTEM_INSTRUCTION = """You are an AI tutor assistant. Remember ONLY these basic student details from conversation:
like what he likes and dislike and and language and all other accoridng to you
write like that Third person ex: "student is a 10th grade student who likes Physics and Math, enjoys Cricket and Space topics, prefers English for study."
"""


def load_conversation():
    """Load conversation from last_conversation folder"""
    try:
        if os.path.exists(LAST_CONV_FILE):
            with open(LAST_CONV_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both list format and dict format
                if isinstance(data, dict):
                    return data.get("conversation", []), data.get("memory", "")
                elif isinstance(data, list):
                    # List format - no memory key
                    return data, ""
        return [], ""
    except Exception as e:
        print(f"Error loading conversation: {e}")
        return [], ""


def load_previous_memory():
    """Load previous memory from current_memory folder"""
    try:
        if os.path.exists(CURRENT_MEMORY_FILE):
            with open(CURRENT_MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both dict format and direct string
                if isinstance(data, dict):
                    return data.get("memory", "")
                elif isinstance(data, str):
                    return data
        return ""
    except Exception as e:
        print(f"Error loading previous memory: {e}")
        return ""


def save_memory(memory):
    """Save memory to both current_memory and all_memory folders"""
    try:
        if not memory:
            return

        # Save to current_memory (overwrite - keeps only 1 latest)
        with open(CURRENT_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"memory": memory}, f, indent=2, ensure_ascii=False)

        # Save to all_memory (new file with timestamp - keeps all)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_memory_file = os.path.join(ALL_MEMORY_DIR, f"memory_{timestamp}.json")
        with open(all_memory_file, "w", encoding="utf-8") as f:
            json.dump({"memory": memory}, f, indent=2, ensure_ascii=False)

        print("✅ Memory saved to:")
        print(f"   - Current: {CURRENT_MEMORY_FILE}")
        print(f"   - All: {all_memory_file}")
    except Exception as e:
        print(f"Error saving memory: {e}")


def generate_response():
    """Generate response from Gemini with conversation context - SINGLE LLM REQUEST"""
    try:
        # Load conversation from last_conversation folder
        conversation, _ = load_conversation()

        # Load previous memory from current_memory folder
        previous_memory = load_previous_memory()

        # Build system instruction with previous memory
        system_instruction = BASE_SYSTEM_INSTRUCTION
        if previous_memory:
            system_instruction += f"""

Previous Memory: {previous_memory}

IMPORTANT: Update this previous memory with new information from the conversation. add and remove any information as needed. Keep it concise and in third person format."""

        # Prepare context with conversation history
        conversation_text = (
            json.dumps(conversation, ensure_ascii=False)
            if conversation
            else "No previous conversation"
        )

        # Create prompt with conversation
        full_prompt = f"""Conversation:
{conversation_text}
"""

        # Generate response - SINGLE LLM REQUEST
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=full_prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )

        # Get AI response - this becomes the new/updated memory
        ai_response = response.text

        # Save memory to both current_memory and all_memory folders
        save_memory(ai_response)

        # Print the memory
        print("=" * 60)
        if previous_memory:
            print("Previous Memory:")
            print(previous_memory)
            print("\n" + "=" * 60)
        print("New Memory:")
        print(ai_response)
        print("=" * 60)

        return ai_response

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == "__main__":
    generate_response()
