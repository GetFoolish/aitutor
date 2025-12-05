import os
import sys
import json
import asyncio
import traceback
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import httpx

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

TEACHING_ASSISTANT_API_URL = os.getenv("TEACHING_ASSISTANT_API_URL", "http://localhost:8002")
SAMPLE_CONVERSATIONS_PATH = project_root / "Memory_Brief" / "sample_conversations_for_testing"
SESSION_FILES = [
    "session_1_intro.md",
    "session_2_post_test.md",
    "session_3_emotional.md",
    "session_4_deep_personal_connection.md",
    "session_5_testing_sentient_feel.md",
]

# Mode constants
MODE_AUTOMATIC = "automatic"
MODE_INTERACTIVE_MIXED = "interactive_mixed"

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

def parse_conversation_file(filepath: Path) -> List[Dict[str, str]]:
    """Parse conversation file and return all turns in sequence (both AI and Student messages)"""
    turns = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    speaker = data.get("speaker", "")
                    text = data.get("text", "")
                    if speaker and text:
                        # Normalize speaker names: "AI" -> "AI", "Student" -> "Student"
                        if speaker == "AI":
                            turns.append({"speaker": "AI", "text": text})
                        elif speaker == "Student":
                            turns.append({"speaker": "Student", "text": text})
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
    except Exception as e:
        print(f"⚠️  Error reading file {filepath}: {e}")
    return turns

async def read_user_input(prompt: str = "") -> str:
    """Read user input asynchronously from terminal"""
    if prompt:
        print(prompt, end="", flush=True)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input)

class AutomatedSimulator:
    def __init__(self, user_id: str = "simulator_user", conversations_path: Path = None, 
                 session_files: list[str] = None, memory_api_url: str = None, mode: str = MODE_AUTOMATIC,
                 delay_between_files: int = 60):
        self.user_id = user_id
        self.conversation_storage = ConversationStorage(user_id=user_id)
        self.conversations_path = conversations_path or SAMPLE_CONVERSATIONS_PATH
        self.session_files = session_files or SESSION_FILES
        self.memory_api_url = memory_api_url or TEACHING_ASSISTANT_API_URL
        self.mode = mode
        self.delay_between_files = delay_between_files
        self.previous_adam_text = ""  # Track previous Adam response for conversation history

    async def process_turn(self, user_text: str, adam_text: str):
        """Process a single conversation turn: send memory events and update storage"""
        # Add user text to storage
        self.conversation_storage.add_user_text(user_text)
        user_timestamp = self.conversation_storage.flush_user_turn()
        
        # Send retrieval/user-turn event (triggers memory retrieval - TA-light and TA-deep)
        # Pass previous Adam text to maintain conversation history context
        if user_timestamp and self.conversation_storage.session:
            await send_memory_event('retrieval/user-turn', {
                "session_id": self.conversation_storage.session["session_id"],
                "user_id": self.user_id,
                "user_text": user_text,
                "adam_text": self.previous_adam_text,  # Pass previous Adam text for conversation context
                "timestamp": user_timestamp
            }, api_url=self.memory_api_url)
        
        # Longer delay for memory processing (TA-light and TA-deep retrieval)
        # This ensures the retrieval completes before we continue
        await asyncio.sleep(2)
        
        # Add Adam text to storage
        self.conversation_storage.add_adam_text(adam_text)
        adam_timestamp = self.conversation_storage.flush_adam_turn()
        
        # Update previous Adam text for next turn's conversation history
        self.previous_adam_text = adam_text
        
        # Send turn event (complete conversation turn)
        if adam_timestamp and self.conversation_storage.last_user_turn_text:
            await send_memory_event('turn', {
                "session_id": self.conversation_storage.session["session_id"],
                "user_id": self.user_id,
                "user_text": self.conversation_storage.last_user_turn_text,
                "adam_text": adam_text,
                "timestamp": adam_timestamp
            }, api_url=self.memory_api_url)
        
        # Small delay between turns
        await asyncio.sleep(1)

    async def run_automatic_mode(self):
        """Mode 1: Automatic - Process all files sequentially with delay between files"""
        # Reset previous Adam text for new session
        self.previous_adam_text = ""
        session_id = self.conversation_storage.start_session()
        await send_memory_event('session/start', {
            "session_id": session_id,
            "user_id": self.user_id
        }, api_url=self.memory_api_url)
        
        print("\n" + "="*60)
        print("Mode: AUTOMATIC - Processing files sequentially")
        print(f"Processing {len(self.session_files)} session files")
        print(f"Delay between files: {self.delay_between_files} seconds")
        print(f"Memory API: {TEACHING_ASSISTANT_API_URL}")
        print("="*60 + "\n")
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                continue
            
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                continue
            
            # Group turns into pairs (User, Adam)
            # Conversation format: alternates between AI and Student
            # A turn is: User speaks, then Adam responds
            turn_pairs = []
            i = 0
            
            # Skip initial AI message if conversation starts with AI (it's just greeting)
            # We'll pair Student messages with the following AI responses
            if turns and turns[0]["speaker"] == "AI":
                i = 1  # Skip first AI message, start from first Student message
            
            # Process turns: Student message pairs with next AI message
            while i < len(turns):
                if turns[i]["speaker"] == "Student":
                    user_text = turns[i]["text"]
                    # Look for next AI message as Adam's response
                    if i + 1 < len(turns) and turns[i + 1]["speaker"] == "AI":
                        adam_text = turns[i + 1]["text"]
                        turn_pairs.append((user_text, adam_text))
                        i += 2
                    else:
                        # Student message without AI response, use empty Adam text
                        turn_pairs.append((user_text, ""))
                        i += 1
                elif turns[i]["speaker"] == "AI":
                    # Unpaired AI message (shouldn't happen after skipping first), skip it
                    i += 1
                else:
                    i += 1
            
            if not turn_pairs:
                print(f"⚠️  No valid turn pairs found in {session_file}")
                continue
            
            print(f"Found {len(turn_pairs)} conversation turns\n")
            
            for turn_idx, (user_text, adam_text) in enumerate(turn_pairs, 1):
                print(f"\n[Turn {turn_idx}/{len(turn_pairs)}]")
                print(f"User > {user_text[:100]}...")
                print(f"Adam > {adam_text[:100]}...")
                
                await self.process_turn(user_text, adam_text)
            
            print(f"\n✅ Completed: {session_file}")
            print("-" * 60)
            
            # Wait before processing next file (except for last file)
            if file_idx < len(self.session_files):
                print(f"\n⏳ Waiting {self.delay_between_files} seconds before next file...")
                await asyncio.sleep(self.delay_between_files)
        
        # End session
        print("\n💾 Ending session...")
        end_time = datetime.utcnow().isoformat() + "Z"
        session_id = self.conversation_storage.end_session()
        if session_id:
            await send_memory_event('session/end', {
                "session_id": session_id,
                "user_id": self.user_id,
                "end_time": end_time
            }, api_url=self.memory_api_url)
        
        print("\n✅ Automatic simulation completed successfully!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_interactive_mode_mixed(self):
        """Mode 2MIXED: Interactive - Adam from JSON, User from terminal OR JSON (Enter to use JSON)"""
        # Reset previous Adam text for new session
        self.previous_adam_text = ""
        session_id = self.conversation_storage.start_session()
        await send_memory_event('session/start', {
            "session_id": session_id,
            "user_id": self.user_id
        }, api_url=self.memory_api_url)
        
        print("\n" + "="*60)
        print("Mode: INTERACTIVE MIXED - Adam from JSON, User from Terminal or JSON")
        print(f"Memory API: {TEACHING_ASSISTANT_API_URL}")
        print("="*60 + "\n")
        print("Instructions:")
        print("- Adam's responses will come from the conversation files")
        print("- User's text from JSON will be shown as a suggestion")
        print("- Press Enter to use the JSON text, or type your own response")
        print("- Type 'quit' or 'exit' to end the session\n")
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                continue
            
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                continue
            
            # Group turns into pairs (User, Adam)
            turn_pairs = []
            i = 0
            
            # Skip initial AI message if conversation starts with AI
            if turns and turns[0]["speaker"] == "AI":
                i = 1
            
            # Process turns: Student message pairs with next AI message
            while i < len(turns):
                if turns[i]["speaker"] == "Student":
                    user_text = turns[i]["text"]
                    if i + 1 < len(turns) and turns[i + 1]["speaker"] == "AI":
                        adam_text = turns[i + 1]["text"]
                        turn_pairs.append((user_text, adam_text))
                        i += 2
                    else:
                        turn_pairs.append((user_text, ""))
                        i += 1
                elif turns[i]["speaker"] == "AI":
                    i += 1
                else:
                    i += 1
            
            if not turn_pairs:
                print(f"⚠️  No valid turn pairs found in {session_file}")
                continue
            
            print(f"Found {len(turn_pairs)} conversation turns\n")
            
            for turn_idx, (json_user_text, adam_text) in enumerate(turn_pairs, 1):
                print(f"\n[Turn {turn_idx}/{len(turn_pairs)}]")
                print(f"Adam > {adam_text}")
                print(f"JSON User > {json_user_text[:100]}...")
                
                # Get user input: Enter to use JSON, or type custom response
                user_input = await read_user_input("\nPress Enter to use JSON text, or type your own response: ")
                
                if user_input.lower().strip() in ['quit', 'exit', 'q']:
                    print("\n👋 Ending session...")
                    break
                
                # If empty input (just Enter), use JSON text; otherwise use typed text
                if not user_input.strip():
                    user_text = json_user_text
                    print(f"Using JSON text: {user_text[:100]}...")
                else:
                    user_text = user_input.strip()
                    print(f"Using custom text: {user_text[:100]}...")
                
                await self.process_turn(user_text, adam_text)
            
            print(f"\n✅ Completed: {session_file}")
            print("-" * 60)
            
            # Ask if user wants to continue to next file
            if file_idx < len(self.session_files):
                continue_choice = await read_user_input("\nContinue to next file? (y/n): ")
                if continue_choice.lower().strip() not in ['y', 'yes']:
                    break
        
        # End session
        print("\n💾 Ending session...")
        end_time = datetime.utcnow().isoformat() + "Z"
        session_id = self.conversation_storage.end_session()
        if session_id:
            await send_memory_event('session/end', {
                "session_id": session_id,
                "user_id": self.user_id,
                "end_time": end_time
            }, api_url=self.memory_api_url)
        
        print("\n✅ Interactive mixed mode completed!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_simulation(self):
        """Main simulation runner - routes to appropriate mode"""
        try:
            if self.mode == MODE_AUTOMATIC:
                await self.run_automatic_mode()
            elif self.mode == MODE_INTERACTIVE_MIXED:
                await self.run_interactive_mode_mixed()
            else:
                print(f"❌ Unknown mode: {self.mode}")
                print(f"Available modes: {MODE_AUTOMATIC}, {MODE_INTERACTIVE_MIXED}")
        except KeyboardInterrupt:
            print("\n\n⚠️  Simulation interrupted by user")
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
    parser = argparse.ArgumentParser(description="AI Tutor Conversation Simulator")
    parser.add_argument(
        "--mode",
        type=str,
        choices=[MODE_AUTOMATIC, MODE_INTERACTIVE_MIXED],
        default=MODE_AUTOMATIC,
        help=f"Simulation mode: {MODE_AUTOMATIC} (automatic), {MODE_INTERACTIVE_MIXED} (Adam from JSON, User from terminal OR JSON - Enter to use JSON, type to use custom)"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="simulator_user",
        help="User ID for the simulation (default: simulator_user)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=60,
        help="Delay in seconds between files in automatic mode (default: 60)"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help=f"Teaching Assistant API URL (default: {TEACHING_ASSISTANT_API_URL})"
    )
    
    args = parser.parse_args()
    
    simulator = AutomatedSimulator(
        user_id=args.user_id,
        mode=args.mode,
        delay_between_files=args.delay,
        memory_api_url=args.api_url
    )
    
    asyncio.run(simulator.run_simulation())
