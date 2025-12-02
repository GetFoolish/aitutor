import os
import sys
import json
import asyncio
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

from google import genai
from google.genai import types
import httpx

MODEL = os.getenv("GEMINI_MODEL_SIMULATOR", "models/gemini-2.0-flash-exp")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """You are "Adam," an expert AI Tutor. Your persona is that of an incredibly patient, empathetic, and encouraging mentor. Your primary mission is to guide students to discover answers for themselves, fostering critical thinking and genuine understanding. You must **NEVER** give away the direct answer to a problem."""

CONFIG = types.LiveConnectConfig(
    response_modalities=["TEXT"],
    system_instruction=types.Content(parts=[types.Part.from_text(text=SYSTEM_INSTRUCTION)], role="user"),
)

TEACHING_ASSISTANT_API_URL = os.getenv("TEACHING_ASSISTANT_API_URL", "http://localhost:8002")
SAMPLE_CONVERSATIONS_PATH = project_root / "Memory_Brief" / "sample_conversations_for_testing"
SESSION_FILES = [
    "session_1_intro.md",
    "session_2_post_test.md",
    "session_3_emotional.md",
    "session_4_deep_personal_connection.md",
    "session_5_testing_sentient_feel.md",
]

async def send_memory_event(endpoint: str, data: dict, api_url: str = None, max_retries: int = 2):
    url = api_url or TEACHING_ASSISTANT_API_URL
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{url}/memory/{endpoint}", json=data)
                if response.is_success:
                    if attempt > 0:
                        print(f"✅ Memory event succeeded on retry {attempt + 1}: {endpoint}")
                    return True
                else:
                    error_msg = f"⚠️  Memory event failed: {endpoint} - HTTP {response.status_code}"
                    if attempt < max_retries:
                        print(f"{error_msg}, retrying...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        print(f"{error_msg} (no more retries)")
                        return False
        except httpx.TimeoutException:
            if attempt < max_retries:
                print(f"⏳ Memory event timeout (attempt {attempt + 1}/{max_retries + 1}): {endpoint}, retrying in 2s...")
                await asyncio.sleep(2)
                continue
            else:
                print(f"❌ Memory event timeout after {max_retries + 1} attempts: {endpoint}")
                return False
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️  Memory event error (attempt {attempt + 1}/{max_retries + 1}): {endpoint} - {e}, retrying...")
                await asyncio.sleep(1)
                continue
            else:
                print(f"❌ Failed to send memory event after {max_retries + 1} attempts: {endpoint} - {e}")
                return False
    return False

class ConversationStorage:
    def __init__(self, user_id: str = "simulator_user"):
        self.user_id = user_id
        self.session: Optional[Dict[str, Any]] = None
        self.user_buffer = ""
        self.adam_buffer = ""
        self.last_user_turn_text = ""

    def start_session(self) -> str:
        timestamp = datetime.utcnow()
        random_suffix = os.urandom(3).hex()
        session_id = f"sess_{timestamp.strftime('%Y%m%d_%H%M%S')}_{random_suffix}"
        self.session = {
            "session_id": session_id,
            "user_id": self.user_id,
            "start_time": timestamp.isoformat() + "Z",
            "end_time": None,
            "turns": []
        }
        self.user_buffer = ""
        self.adam_buffer = ""
        self.last_user_turn_text = ""
        print(f"📝 Conversation session started: {session_id} for user: {self.user_id}")
        return session_id

    def add_user_text(self, text: str):
        if not self.session or not text:
            return
        self.user_buffer += text

    def add_adam_text(self, text: str):
        if not self.session or not text:
            return
        self.adam_buffer += text

    def flush_user_turn(self) -> Optional[str]:
        if not self.session or not self.user_buffer.strip():
            return None
        user_text = self.user_buffer.strip()
        timestamp = datetime.utcnow().isoformat() + "Z"
        self.session["turns"].append({"speaker": "user", "text": user_text, "timestamp": timestamp})
        self.last_user_turn_text = user_text
        print(f"🎤 User turn saved: {user_text[:50]}...")
        self.user_buffer = ""
        return timestamp

    def flush_adam_turn(self) -> Optional[str]:
        if not self.session or not self.adam_buffer.strip():
            return None
        adam_text = self.adam_buffer.strip()
        timestamp = datetime.utcnow().isoformat() + "Z"
        self.session["turns"].append({"speaker": "adam", "text": adam_text, "timestamp": timestamp})
        print(f"🤖 Adam turn saved: {adam_text[:50]}...")
        self.adam_buffer = ""
        return timestamp

    def end_session(self) -> Optional[str]:
        if not self.session:
            return None
        if self.user_buffer.strip():
            self.flush_user_turn()
        if self.adam_buffer.strip():
            self.flush_adam_turn()
        end_time = datetime.utcnow().isoformat() + "Z"
        self.session["end_time"] = end_time
        session_id = self.session["session_id"]
        print(f"💾 Conversation ended: {session_id}")
        self.session = None
        return session_id

def parse_conversation_file(filepath: Path) -> list[str]:
    student_messages = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("speaker") == "Student":
                        student_messages.append(data.get("text", ""))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
    except Exception as e:
        print(f"⚠️  Error reading file {filepath}: {e}")
    return student_messages

class AutomatedSimulator:
    def __init__(self, user_id: str = "simulator_user", conversations_path: Path = None, session_files: list[str] = None, memory_api_url: str = None):
        self.user_id = user_id
        self.conversation_storage = ConversationStorage(user_id=user_id)
        self.gemini_session = None
        self.conversations_path = conversations_path or SAMPLE_CONVERSATIONS_PATH
        self.session_files = session_files or SESSION_FILES
        self.current_adam_response = ""
        self.response_received = asyncio.Event()
        self.memory_api_url = memory_api_url or TEACHING_ASSISTANT_API_URL

    async def wait_for_ai_response(self):
        self.response_received.clear()
        await self.response_received.wait()

    async def receive_text_loop(self):
        while True:
            try:
                turn = self.gemini_session.receive()
                self.current_adam_response = ""
                async for response in turn:
                    if text := response.text:
                        print(f"Adam > {text}", end="", flush=True)
                        self.current_adam_response += text
                        self.conversation_storage.add_adam_text(text)
                if self.current_adam_response.strip():
                    adam_timestamp = self.conversation_storage.flush_adam_turn()
                    if adam_timestamp and self.conversation_storage.last_user_turn_text:
                        await send_memory_event('turn', {
                            "session_id": self.conversation_storage.session["session_id"],
                            "user_id": self.user_id,
                            "user_text": self.conversation_storage.last_user_turn_text,
                            "adam_text": self.current_adam_response.strip(),
                            "timestamp": adam_timestamp
                        }, api_url=self.memory_api_url)
                print()
                self.response_received.set()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\nError receiving response: {e}")
                self.response_received.set()
                break

    async def send_message(self, text: str):
        self.conversation_storage.add_user_text(text)
        user_timestamp = self.conversation_storage.flush_user_turn()
        print(f"You > {text}")
        if user_timestamp and self.conversation_storage.session:
            await send_memory_event('retrieval/user-turn', {
                "session_id": self.conversation_storage.session["session_id"],
                "user_id": self.user_id,
                "user_text": text,
                "adam_text": "",
                "timestamp": user_timestamp
            }, api_url=self.memory_api_url)
        await self.gemini_session.send(input=text, end_of_turn=True)
        await self.wait_for_ai_response()

    async def run_simulation(self):
        try:
            async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
                self.gemini_session = session
                session_id = self.conversation_storage.start_session()
                await send_memory_event('session/start', {
                    "session_id": session_id,
                    "user_id": self.user_id
                }, api_url=self.memory_api_url)
                print("\n" + "="*60)
                print("Automated Conversation Simulator with Memory Integration")
                print(f"Processing {len(self.session_files)} session files")
                print(f"Memory API: {TEACHING_ASSISTANT_API_URL}")
                print("="*60 + "\n")
                receive_task = asyncio.create_task(self.receive_text_loop())
                print("📤 Initializing session with dummy message...")
                await self.send_message(".")
                await asyncio.sleep(1)
                for session_file in self.session_files:
                    filepath = self.conversations_path / session_file
                    if not filepath.exists():
                        print(f"⚠️  Skipping {session_file} - file not found")
                        continue
                    print(f"\n📂 Processing: {session_file}")
                    print("-" * 60)
                    student_messages = parse_conversation_file(filepath)
                    if not student_messages:
                        print(f"⚠️  No student messages found in {session_file}")
                        continue
                    print(f"Found {len(student_messages)} student messages\n")
                    for i, student_msg in enumerate(student_messages, 1):
                        print(f"\n[Message {i}/{len(student_messages)}]")
                        await self.send_message(student_msg)
                        await asyncio.sleep(1)
                    print(f"\n✅ Completed: {session_file}")
                    print("-" * 60)
                print("\n💾 Ending session...")
                end_time = datetime.utcnow().isoformat() + "Z"
                session_id = self.conversation_storage.end_session()
                if session_id:
                    await send_memory_event('session/end', {
                        "session_id": session_id,
                        "user_id": self.user_id,
                        "end_time": end_time
                    }, api_url=self.memory_api_url)
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                print("\n✅ Simulation completed successfully!")
                print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")
        except Exception as e:
            print(f"\n❌ Error in simulation: {e}")
            traceback.print_exc()
        finally:
            if self.conversation_storage.session:
                end_time = datetime.utcnow().isoformat() + "Z"
                session_id = self.conversation_storage.end_session()
                if session_id:
                    await send_memory_event('session/end', {
                        "session_id": session_id,
                        "user_id": self.user_id,
                        "end_time": end_time
                    }, api_url=self.memory_api_url)

if __name__ == "__main__":
    simulator = AutomatedSimulator()
    asyncio.run(simulator.run_simulation())
