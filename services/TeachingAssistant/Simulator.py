import os
import sys
import json
import asyncio
import traceback
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from dotenv import load_dotenv
import websockets
import logging

# Suppress websockets library errors for HTTP requests (expected behavior)
websockets_logger = logging.getLogger('websockets.server')
websockets_logger.setLevel(logging.CRITICAL)  # Suppress all websockets logging

# Patch traceback and sys.excepthook to suppress HTTP POST handshake errors
_original_print_exception = traceback.print_exception
_original_excepthook = sys.excepthook

def _filtered_print_exception(exc_type, exc_value, exc_traceback, file=None, chain=True):
    """Filter out websockets HTTP POST handshake errors"""
    if exc_type is websockets.exceptions.InvalidMessage:
        error_msg = str(exc_value)
        if "did not receive a valid HTTP request" in error_msg or "unsupported HTTP method" in error_msg:
            # Suppress these errors - they're expected for HTTP POST requests
            return
    # Call original for all other exceptions
    _original_print_exception(exc_type, exc_value, exc_traceback, file, chain)

def _filtered_excepthook(exc_type, exc_value, exc_traceback):
    """Filter out websockets HTTP POST handshake errors from sys.excepthook"""
    if exc_type is websockets.exceptions.InvalidMessage:
        error_msg = str(exc_value)
        if "did not receive a valid HTTP request" in error_msg or "unsupported HTTP method" in error_msg:
            # Suppress these errors - they're expected for HTTP POST requests
            return
    # Call original for all other exceptions
    _original_excepthook(exc_type, exc_value, exc_traceback)

# Apply the patches
traceback.print_exception = _filtered_print_exception
sys.excepthook = _filtered_excepthook

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

SIMULATOR_WS_PORT = int(os.getenv("SIMULATOR_WS_PORT", "8767"))
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

# Message sequencing (same as server.js)
message_sequence_counter = 0

def generate_message_id():
    """Generate unique message ID (same format as server.js)"""
    global message_sequence_counter
    timestamp = int(datetime.utcnow().timestamp() * 1000)
    random = os.urandom(4).hex()
    message_sequence_counter += 1
    return f"msg_{timestamp}_{message_sequence_counter}_{random}"

async def broadcast_to_teaching_assistant(event: dict, clients: Set):
    """Broadcast event to all connected TeachingAssistant clients (same format as server.js)"""
    global message_sequence_counter
    
    if not clients:
        print("⚠️  No TeachingAssistant clients connected, message not sent")
        return
    
    # Generate message_id (this increments message_sequence_counter)
    message_id = generate_message_id()
    # Sequence uses the value after increment (same as server.js: sequence = messageSequenceCounter after generateMessageId)
    sequence = message_sequence_counter
    
    enriched_event = {
        **event,
        "message_id": message_id,
        "sequence": sequence,
        "server_timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Calculate checksum (must match context.py validator format)
    try:
        # Match context.py validator: separators=(',', ':') - no spaces
        message_without_checksum = json.dumps(enriched_event, separators=(',', ':'), ensure_ascii=False, sort_keys=False)
        checksum = hashlib.sha256(message_without_checksum.encode('utf-8')).digest().hex()
        enriched_event["checksum"] = checksum
        message = json.dumps(enriched_event, separators=(',', ':'), ensure_ascii=False, sort_keys=False)
    except Exception as error:
        print(f"❌ Failed to serialize message {message_id}: {error}")
        return
    
    dead_clients = []
    success_count = 0
    failure_count = 0
    
    async def send_to_client(client):
        try:
            await client.send(message)
            return True
        except Exception as error:
            print(f"❌ Failed to send message {message_id} (seq: {sequence}) to client: {error}")
            return False
    
    for client in clients:
        try:
            # Try to send message (non-blocking) - this will fail if connection is closed
            asyncio.create_task(send_to_client(client))
            success_count += 1
        except Exception as error:
            # Connection is likely closed or invalid
            print(f"❌ Failed to queue message {message_id} (seq: {sequence}) to client: {error}")
            dead_clients.append(client)
            failure_count += 1
    
    for client in dead_clients:
        clients.discard(client)
    
    if success_count > 0:
        event_type = event.get('type', 'unknown')
        print(f"📤 Broadcast message {message_id} (seq: {sequence}, type: {event_type}) - Success: {success_count}, Failed: {failure_count}")
        
        # Log text preview (same as server.js)
        if event_type == 'text' and event.get('data', {}).get('text'):
            text = event['data']['text']
            text_preview = text[:50] + ('...' if len(text) > 50 else '')
            print(f"   └─ Text preview: \"{text_preview}\"")

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
                 session_files: list[str] = None, ws_port: int = None, mode: str = MODE_AUTOMATIC,
                 delay_between_files: int = 60):
        self.user_id = user_id
        self.conversation_storage = ConversationStorage(user_id=user_id)
        self.conversations_path = conversations_path or SAMPLE_CONVERSATIONS_PATH
        self.session_files = session_files or SESSION_FILES
        self.ws_port = ws_port or SIMULATOR_WS_PORT
        self.mode = mode
        self.delay_between_files = delay_between_files
        self.previous_adam_text = ""
        self.ta_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.ws_server = None

    async def handle_ta_connection(self, websocket, *args):
        """Handle TeachingAssistant WebSocket connection - compatible with different websockets versions"""
        # Extract path from arguments or websocket object
        path = None
        
        # Try to get path from arguments first
        if args and len(args) > 0:
            path = args[0]
        
        # If not in arguments, try to get from websocket object
        if path is None:
            try:
                if hasattr(websocket, 'path'):
                    path = websocket.path
                elif hasattr(websocket, 'request') and hasattr(websocket.request, 'path'):
                    path = websocket.request.path
                elif hasattr(websocket, 'request_headers'):
                    path = getattr(websocket, 'path', '/')
            except Exception:
                path = '/'
        
        # Default fallback
        if path is None:
            path = '/'
        
        # Only accept connections to /ta path
        if path != "/ta":
            print(f"⚠️  Rejected connection to path: {path} (expected /ta)")
            try:
                await websocket.close(code=1008, reason="Path must be /ta")
            except Exception:
                pass
            return
        
        self.ta_clients.add(websocket)
        print(f"✅ TeachingAssistant client connected (total: {len(self.ta_clients)})")
        try:
            # Keep connection alive by listening for messages (even if we don't process them)
            # This prevents the connection from closing immediately
            async for message in websocket:
                # TeachingAssistant doesn't send messages to simulator, but we need to listen
                # to keep the connection alive. Just ignore any messages received.
                pass
        except websockets.exceptions.ConnectionClosed:
            # Connection closed normally
            pass
        except Exception as e:
            print(f"⚠️  WebSocket connection error: {e}")
        finally:
            self.ta_clients.discard(websocket)
            print(f"🔌 TeachingAssistant client disconnected (remaining: {len(self.ta_clients)})")

    async def start_websocket_server(self):
        """Start WebSocket server for TeachingAssistant to connect"""
        print(f"🌐 Starting WebSocket server on ws://localhost:{self.ws_port}/ta")
        
        # Start WebSocket server
        # Note: HTTP POST requests (injection attempts) will cause handshake errors
        # These are expected and can be ignored - the simulator doesn't need to handle injections
        self.ws_server = await websockets.serve(
            self.handle_ta_connection,
            "localhost",
            self.ws_port
        )
        
        print(f"✅ WebSocket server started on ws://localhost:{self.ws_port}/ta")
        print(f"⚠️  Note: HTTP POST errors (injection attempts) are expected and can be ignored")
        if self.ws_port == 8767:
            print(f"   TeachingAssistant will connect automatically (default port matches)")
        else:
            print(f"   Configure TeachingAssistant with TUTOR_WS_URL=ws://localhost:{self.ws_port}/ta")

    async def stop_websocket_server(self):
        """Stop WebSocket server"""
        if self.ws_server:
            self.ws_server.close()
            await self.ws_server.wait_closed()
        print("🔌 WebSocket server stopped")

    async def _end_session_for_file(self, session_id: str):
        """Helper method to end a session and wait for Pinecone indexing"""
        if not session_id:
            return
        
        print("\n💾 Ending session...")
        end_time = datetime.utcnow().isoformat() + "Z"
        ended_session_id = self.conversation_storage.end_session()
        if ended_session_id:
            await broadcast_to_teaching_assistant({
                "type": "session_end",
                "data": {
                    "session_id": ended_session_id,
                    "user_id": self.user_id,
                    "timestamp": end_time
                }
            }, self.ta_clients)
            
            # Wait for Pinecone to index memories before starting next session
            print("\n⏳ Waiting 5 seconds for Pinecone to index memories...")
            await asyncio.sleep(5)

    async def process_turn(self, user_text: str, adam_text: str):
        """Process a single conversation turn: send WebSocket events (same format as server.js)"""
        # Add user text to storage
        self.conversation_storage.add_user_text(user_text)
        user_timestamp = self.conversation_storage.flush_user_turn()
        
        # Send user text event (same format as server.js)
        if user_timestamp and self.conversation_storage.session:
            session_id = self.conversation_storage.session["session_id"]
            await broadcast_to_teaching_assistant({
                "type": "text",
                "data": {
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "text": user_text,
                    "speaker": "user",
                    "timestamp": user_timestamp
                }
            }, self.ta_clients)
        
        # Wait for memory processing
        await asyncio.sleep(2)
        
        # Add Adam text to storage
        self.conversation_storage.add_adam_text(adam_text)
        adam_timestamp = self.conversation_storage.flush_adam_turn()
        
        # Update previous Adam text for next turn
        self.previous_adam_text = adam_text
        
        # Send Adam text event (same format as server.js)
        if adam_timestamp and self.conversation_storage.session:
            session_id = self.conversation_storage.session["session_id"]
            await broadcast_to_teaching_assistant({
                "type": "text",
                "data": {
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "text": adam_text,
                    "speaker": "adam",
                    "interrupted": False,
                    "timestamp": adam_timestamp
                }
            }, self.ta_clients)
        
        # Small delay between turns
        await asyncio.sleep(1)

    async def run_automatic_mode(self):
        """Mode 1: Automatic - Process all files sequentially with delay between files"""
        self.previous_adam_text = ""
        
        print("\n" + "="*60)
        print("Mode: AUTOMATIC - Processing files sequentially")
        print(f"Processing {len(self.session_files)} session files")
        print(f"Delay between files: {self.delay_between_files} seconds")
        print(f"WebSocket server: ws://localhost:{self.ws_port}/ta")
        print("="*60 + "\n")
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            # Start a NEW session for each file
            session_id = self.conversation_storage.start_session()
            
            # Send session_start event (same format as server.js)
            await broadcast_to_teaching_assistant({
                "type": "session_start",
                "data": {
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }, self.ta_clients)
            
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                await self._end_session_for_file(session_id)
                continue
            
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                await self._end_session_for_file(session_id)
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
                await self._end_session_for_file(session_id)
                continue
            
            print(f"Found {len(turn_pairs)} conversation turns\n")
            
            for turn_idx, (user_text, adam_text) in enumerate(turn_pairs, 1):
                print(f"\n[Turn {turn_idx}/{len(turn_pairs)}]")
                print(f"User > {user_text[:100]}...")
                print(f"Adam > {adam_text[:100]}...")
                
                await self.process_turn(user_text, adam_text)
            
            print(f"\n✅ Completed: {session_file}")
            print("-" * 60)
            
            # End session for this file
            await self._end_session_for_file(session_id)
            
            # Wait before processing next file (except for last file)
            if file_idx < len(self.session_files):
                print(f"\n⏳ Waiting {self.delay_between_files} seconds before next file...")
                await asyncio.sleep(self.delay_between_files)
        
        print("\n✅ Automatic simulation completed successfully!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_interactive_mode_mixed(self):
        """Mode 2MIXED: Interactive - Adam from JSON, User from terminal OR JSON (Enter to use JSON)"""
        self.previous_adam_text = ""
        
        print("\n" + "="*60)
        print("Mode: INTERACTIVE MIXED - Adam from JSON, User from Terminal or JSON")
        print(f"WebSocket server: ws://localhost:{self.ws_port}/ta")
        print("="*60 + "\n")
        print("Instructions:")
        print("- Adam's responses will come from the conversation files")
        print("- User's text from JSON will be shown as a suggestion")
        print("- Press Enter to use the JSON text, or type your own response")
        print("- Type 'quit' or 'exit' to end the session\n")
        
        for file_idx, session_file in enumerate(self.session_files, 1):
            # Start a NEW session for each file
            session_id = self.conversation_storage.start_session()
            
            # Send session_start event
            await broadcast_to_teaching_assistant({
                "type": "session_start",
                "data": {
                    "session_id": session_id,
                    "user_id": self.user_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }, self.ta_clients)
            
            filepath = self.conversations_path / session_file
            if not filepath.exists():
                print(f"⚠️  Skipping {session_file} - file not found")
                await self._end_session_for_file(session_id)
                continue
            
            print(f"\n📂 Processing file {file_idx}/{len(self.session_files)}: {session_file}")
            print("-" * 60)
            
            turns = parse_conversation_file(filepath)
            if not turns:
                print(f"⚠️  No turns found in {session_file}")
                await self._end_session_for_file(session_id)
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
                await self._end_session_for_file(session_id)
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
                    await self._end_session_for_file(session_id)
                    return
                
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
            
            # End session for this file
            await self._end_session_for_file(session_id)
            
            # Ask if user wants to continue to next file
            if file_idx < len(self.session_files):
                continue_choice = await read_user_input("\nContinue to next file? (y/n): ")
                if continue_choice.lower().strip() not in ['y', 'yes']:
                    break
        
        print("\n✅ Interactive mixed mode completed!")
        print(f"💾 Memory data stored in: services/TeachingAssistant/Memory/data/{self.user_id}/")

    async def run_simulation(self):
        """Main simulation runner - routes to appropriate mode"""
        try:
            # Start WebSocket server
            await self.start_websocket_server()
            
            # Wait for TeachingAssistant to connect (with timeout)
            print("\n⏳ Waiting for TeachingAssistant to connect...")
            if self.ws_port == 8767:
                print("   (TeachingAssistant should connect automatically - default port matches)")
            else:
                print(f"   (Make sure TeachingAssistant is configured with TUTOR_WS_URL=ws://localhost:{self.ws_port}/ta)")
            print("   (Start TeachingAssistant: python services/TeachingAssistant/api.py)")
            
            max_wait_time = 30  # Wait up to 30 seconds
            wait_interval = 1
            waited = 0
            
            while not self.ta_clients and waited < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                if waited % 5 == 0:
                    print(f"   Still waiting... ({waited}s/{max_wait_time}s)")
            
            if not self.ta_clients:
                print(f"⚠️  Warning: No TeachingAssistant clients connected after {max_wait_time} seconds.")
                print("   Continuing anyway, but events will not be processed.")
                if self.ws_port != 8767:
                    print(f"   Make sure TeachingAssistant is configured with TUTOR_WS_URL=ws://localhost:{self.ws_port}/ta")
            else:
                print("✅ TeachingAssistant connected! Starting simulation...")
            
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
            if self.conversation_storage.session:
                end_time = datetime.utcnow().isoformat() + "Z"
                session_id = self.conversation_storage.end_session()
                if session_id:
                    await broadcast_to_teaching_assistant({
                        "type": "session_end",
                        "data": {
                            "session_id": session_id,
                            "user_id": self.user_id,
                            "timestamp": end_time
                        }
                    }, self.ta_clients)
            await self.stop_websocket_server()

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
        "--ws-port",
        type=int,
        default=None,
        help=f"WebSocket server port (default: {SIMULATOR_WS_PORT})"
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
        delay_between_files=args.delay,
        ws_port=args.ws_port
    )

    asyncio.run(simulator.run_simulation())
