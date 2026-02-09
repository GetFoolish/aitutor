import os
import sys
import json
import asyncio
import traceback
import argparse
import aiohttp
import websockets
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

# Import JWT utilities
from services.AuthService.jwt_utils import create_jwt_token

# Configuration
TEACHING_ASSISTANT_API_URL = os.getenv("TEACHING_ASSISTANT_API_URL", "http://localhost:8002")
TEACHING_ASSISTANT_WS_URL = os.getenv("TEACHING_ASSISTANT_WS_URL", "ws://localhost:8002")
SAMPLE_CONVERSATIONS_PATH = Path(__file__).parent / "Memory" / "Memory_Brief" / "sample_conversations_for_testing"
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

def generate_jwt_token(user_id: str) -> str:
    """Generate JWT token for simulator user"""
    user_data = {
        "user_id": user_id,
        "email": f"{user_id}@simulator.local",
        "name": f"Simulator User {user_id}",
        "google_id": ""
    }
    return create_jwt_token(user_data)

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
                 session_files: list[str] = None, mode: str = MODE_AUTOMATIC,
                 delay_between_files: int = 60):
        self.user_id = user_id
        self.conversations_path = conversations_path or SAMPLE_CONVERSATIONS_PATH
        self.session_files = session_files or SESSION_FILES
        self.mode = mode
        self.delay_between_files = delay_between_files
        self.jwt_token = generate_jwt_token(user_id)
        self.websocket = None
        self.session_id = None
        self.api_url = TEACHING_ASSISTANT_API_URL
        self.ws_url = TEACHING_ASSISTANT_WS_URL

    async def start_session(self) -> bool:
        """Start a new session via HTTP API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.jwt_token}"}
                async with session.post(
                    f"{self.api_url}/session/start",
                    headers=headers,
                    json={}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.session_id = data.get("session_info", {}).get("session_id")
                        print(f"✅ Session started: {self.session_id} for user: {self.user_id}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to start session: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Error starting session: {e}")
            return False

    async def end_session(self) -> bool:
        """End the current session via HTTP API"""
        if not self.session_id:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.jwt_token}"}
                async with session.post(
                    f"{self.api_url}/session/end",
                    headers=headers,
                    json={"interrupt_audio": False}
                ) as response:
                    if response.status == 200:
                        print(f"✅ Session ended: {self.session_id}")
                        self.session_id = None
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Failed to end session: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ Error ending session: {e}")
            return False

    async def connect_websocket(self) -> bool:
        """Connect to TeachingAssistant WebSocket"""
        try:
            ws_url = f"{self.ws_url}/ws/feed?token={self.jwt_token}"
            print(f"🌐 Connecting to WebSocket: {ws_url}")
            self.websocket = await websockets.connect(ws_url)
            print("✅ WebSocket connected")
            return True
        except Exception as e:
            print(f"❌ Failed to connect WebSocket: {e}")
            return False

    async def disconnect_websocket(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            try:
                await self.websocket.close()
                print("🔌 WebSocket disconnected")
            except Exception:
                pass
            self.websocket = None

    async def send_transcript(self, text: str, speaker: str):
        """Send transcript message via WebSocket"""
        if not self.websocket:
            print("⚠️  WebSocket not connected, skipping message")
            return
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        message = {
            "type": "transcript",
            "timestamp": timestamp,
            "data": {
                "transcript": text,
                "speaker": speaker
            }
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            speaker_label = "USER" if speaker == "user" else "TUTOR"
            print(f"📤 Sent transcript [{speaker_label}]: {text[:50]}...")
        except Exception as e:
            print(f"❌ Failed to send transcript: {e}")

    async def process_turn(self, user_text: str, adam_text: str):
        """Process a single conversation turn: send user and tutor transcripts"""
        # Send user transcript
        if user_text.strip():
            await self.send_transcript(user_text, "user")
            # Wait for memory processing
            await asyncio.sleep(3)
        
        # Send tutor (Adam) transcript
        if adam_text.strip():
            await self.send_transcript(adam_text, "tutor")
            # Small delay between turns
            await asyncio.sleep(1)

    async def run_automatic_mode(self):
        """Mode 1: Automatic - Process all files sequentially with delay between files"""
        print("\n" + "="*60)
        print("Mode: AUTOMATIC - Processing files sequentially")
        print(f"Processing {len(self.session_files)} session files")
        print(f"Delay between files: {self.delay_between_files} seconds")
        print(f"API URL: {self.api_url}")
        print("="*60 + "\n")
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                continue
            
            # Start a new session for each file
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            if not await self.start_session():
                print(f"⚠️  Failed to start session for {session_file}, skipping")
                continue
            
            if not await self.connect_websocket():
                print(f"⚠️  Failed to connect WebSocket for {session_file}, skipping")
                await self.end_session()
                continue
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                await self.end_session()
                await self.disconnect_websocket()
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
                await self.end_session()
                await self.disconnect_websocket()
                continue
            
            print(f"Found {len(turn_pairs)} conversation turns\n")
            
            for turn_idx, (user_text, adam_text) in enumerate(turn_pairs, 1):
                print(f"\n[Turn {turn_idx}/{len(turn_pairs)}]")
                print(f"User > {user_text[:100]}...")
                print(f"Adam > {adam_text[:100]}...")
                
                await self.process_turn(user_text, adam_text)
            
            print(f"\n✅ Completed: {session_file}")
            print("-" * 60)
            
            # End session and disconnect WebSocket for this file
            await self.end_session()
            await self.disconnect_websocket()
            
            # Wait before processing next file (except for last file)
            if file_idx < len(self.session_files):
                print(f"\n⏳ Waiting {self.delay_between_files} seconds before next file...")
                await asyncio.sleep(self.delay_between_files)
        
        print("\n✅ Automatic simulation completed successfully!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_interactive_mode_mixed(self):
        """Mode 2MIXED: Interactive - Adam from JSON, User from terminal OR JSON (Enter to use JSON)"""
        print("\n" + "="*60)
        print("Mode: INTERACTIVE MIXED - Adam from JSON, User from Terminal or JSON")
        print(f"API URL: {self.api_url}")
        print("="*60 + "\n")
        print("Instructions:")
        print("- Adam's responses will come from the conversation files")
        print("- User's text from JSON will be shown as a suggestion")
        print("- Press Enter to use the JSON text, or type your own response")
        print("- Type 'quit' or 'exit' to end the session\n")
        
        user_quit = False  # Track if user wants to quit
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                continue
            
            # Start a new session for each file
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            if not await self.start_session():
                print(f"⚠️  Failed to start session for {session_file}, skipping")
                continue
            
            if not await self.connect_websocket():
                print(f"⚠️  Failed to connect WebSocket for {session_file}, skipping")
                await self.end_session()
                continue
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                await self.end_session()
                await self.disconnect_websocket()
                continue
            
            # Group turns into pairs (User, Adam)
            turn_pairs = []
            i = 0
            
            if turns and turns[0]["speaker"] == "AI":
                i = 1
            
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
                await self.end_session()
                await self.disconnect_websocket()
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
                    user_quit = True
                    break  # Break out of turn loop
                
                # If empty input (just Enter), use JSON text; otherwise use typed text
                if not user_input.strip():
                    user_text = json_user_text
                    print(f"Using JSON text: {user_text[:100]}...")
                else:
                    user_text = user_input.strip()
                    print(f"Using custom text: {user_text[:100]}...")
                
                await self.process_turn(user_text, adam_text)
            
            # End session and disconnect WebSocket for this file
            await self.end_session()
            await self.disconnect_websocket()
            
            # Check if user quit
            if user_quit:
                print(f"\n👋 Session ended by user")
                break  # Break out of file loop
            
            # Only show completion message if not quit
            if not user_quit:
                print(f"\n✅ Completed: {session_file}")
                print("-" * 60)
            
            # Ask if user wants to continue to next file (only if not quit)
            if file_idx < len(self.session_files) and not user_quit:
                continue_choice = await read_user_input("\nContinue to next file? (y/n): ")
                if continue_choice.lower().strip() not in ['y', 'yes']:
                    break
        
        print("\n✅ Interactive mixed mode completed!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_simulation(self):
        """Main simulation runner - routes to appropriate mode"""
        try:
            # Check if TeachingAssistant API is accessible
            print(f"\n⏳ Checking TeachingAssistant API at {self.api_url}...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.api_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            print("✅ TeachingAssistant API is accessible")
                        else:
                            print(f"⚠️  TeachingAssistant API returned status {response.status}")
            except Exception as e:
                print(f"⚠️  Warning: Could not connect to TeachingAssistant API: {e}")
                print("   Make sure TeachingAssistant is running: python services/TeachingAssistant/api.py")
                return
            
            # Run the simulation
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
            # Clean up any remaining connections
            if self.session_id:
                await self.end_session()
            await self.disconnect_websocket()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Tutor Conversation Simulator (WebSocket-based)")
    parser.add_argument(
        "--mode",
        type=str,
        choices=[MODE_AUTOMATIC, MODE_INTERACTIVE_MIXED],
        default=MODE_AUTOMATIC,
        help=f"Simulation mode: {MODE_AUTOMATIC} (automatic), {MODE_INTERACTIVE_MIXED} (Adam from JSON, User from terminal OR JSON)"
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
        "--clean",
        action="store_true",
        help="Clear all existing memories (Pinecone + local) for the user before starting simulation"
    )

    args = parser.parse_args()

    # Handle --clean flag before starting simulation
    if args.clean:
        print(f"\n🧹 Cleaning all memories for user: {args.user_id}")
        print("=" * 60)

        # Import and initialize MemoryStore to clear data
        from services.TeachingAssistant.Memory.vector_store import MemoryStore

        try:
            store = MemoryStore(user_id=args.user_id)
            success = store.clear_all_memories(args.user_id)
            if success:
                print(f"✅ Successfully cleared all memories for user: {args.user_id}")
            else:
                print(f"⚠️ Some errors occurred while clearing memories")
        except Exception as e:
            print(f"❌ Error clearing memories: {e}")

        print("=" * 60 + "\n")

    simulator = AutomatedSimulator(
        user_id=args.user_id,
        mode=args.mode,
        delay_between_files=args.delay
    )

    asyncio.run(simulator.run_simulation())
