

import asyncio
import traceback
import pyaudio
import json
import os
import subprocess
from datetime import datetime

from google import genai
from google.genai import types

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.0-flash-exp"

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key="AIzaSyAqeEM31IrxFhB65dDWSYCtdu433Wg1NTw",
)

# Base system instruction
BASE_SYSTEM_INSTRUCTION = "You are AI Helpful assistant speak in english  talk naturally"


def load_current_memory():
    """Load current memory from current_memory folder"""
    try:
        memory_file = os.path.join("student", "memory", "current_memory", "memory.json")
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Handle both dict format and direct string
                if isinstance(data, dict):
                    return data.get("memory", "")
                elif isinstance(data, str):
                    return data
        return ""
    except Exception as e:
        print(f"Error loading current memory: {e}")
        return ""


def get_config():
    """Get CONFIG with memory included in system instruction"""
    # Load current memory
    current_memory = load_current_memory()

    # Build system instruction
    system_instruction_text = BASE_SYSTEM_INSTRUCTION
    if current_memory:
        system_instruction_text += f"\n\nStudent Memory: {current_memory}\nUse this memory to personalize your responses and remember student preferences. only use past memory whenver required."

    return types.LiveConnectConfig(
        response_modalities=[
            "AUDIO",
        ],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=system_instruction_text)], role="user"
        ),
        context_window_compression=types.ContextWindowCompressionConfig(
            trigger_tokens=25600,
            sliding_window=types.SlidingWindow(target_tokens=12800),
        ),
        output_audio_transcription={},
        input_audio_transcription={},
    )


pya = pyaudio.PyAudio()


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None
        self.audio_stream = None

        # Conversation storage for turn-based JSON
        self.conversation = []
        self.current_student_text = ""
        self.current_ai_text = ""
        self.is_student_turn = False
        self.is_ai_turn = False
        self.session_close_requested = False

        # Folder structure setup
        self.base_dir = "student"
        self.last_conv_dir = os.path.join(
            self.base_dir, "conversation", "last_conversation"
        )
        self.all_conv_dir = os.path.join(
            self.base_dir, "conversation", "all_conversation"
        )

        # Create directories if they don't exist
        os.makedirs(self.last_conv_dir, exist_ok=True)
        os.makedirs(self.all_conv_dir, exist_ok=True)

        # File paths
        self.last_conv_file = os.path.join(self.last_conv_dir, "conversation.json")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.all_conv_file = os.path.join(
            self.all_conv_dir, f"conversation_{self.timestamp}.json"
        )

    def save_turn(self, speaker, text):
        """Save a complete turn to conversation list"""
        if text.strip():  # Only save if there's actual text
            self.conversation.append({"speaker": speaker, "text": text.strip()})
            self.save_to_json()

    def save_to_json(self):
        """Save conversation to JSON file - both last and all conversation folders"""
        try:
            # Save to last_conversation (overwrite - keeps only 1 latest)
            with open(self.last_conv_file, "w", encoding="utf-8") as f:
                json.dump(self.conversation, f, indent=2, ensure_ascii=False)

            # Save to all_conversation (new file with timestamp - keeps all)
            with open(self.all_conv_file, "w", encoding="utf-8") as f:
                json.dump(self.conversation, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving to JSON: {e}")

    def trigger_memory_analysis(self):
        """Automatically trigger memory.py for memory analysis"""
        try:
            # Import and call memory.py function directly instead of subprocess
            import memory

            memory_result = memory.generate_response()

            # Check if memory was actually created
            memory_file = os.path.join(
                self.base_dir, "memory", "current_memory", "memory.json"
            )
            if os.path.exists(memory_file) and memory_result:
                print("✅ Memory generated and saved successfully!")
                return True
            else:
                print("⚠️  Warning: Memory generation may have failed.")
                return False

        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("💡 Trying subprocess method as fallback...")
            try:
                import sys

                result = subprocess.run(
                    [sys.executable, "memory.py"],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                )
                if result.stdout:
                    print(result.stdout)
                if result.stderr and "ImportError" not in result.stderr:
                    print("⚠️  Errors:", result.stderr)

                # Check if memory was created
                memory_file = os.path.join(
                    self.base_dir, "memory", "current_memory", "memory.json"
                )
                if os.path.exists(memory_file):
                    print("✅ Memory file created successfully!")
                    return True
            except Exception as sub_e:
                print(f"❌ Subprocess also failed: {sub_e}")
        except Exception as e:
            print(f"❌ Error triggering memory analysis: {e}")
            import traceback

            traceback.print_exc()
            return False

    def reset_session(self):
        """Reset session state for new session"""
        self.conversation = []
        self.current_student_text = ""
        self.current_ai_text = ""
        self.is_student_turn = False
        self.is_ai_turn = False
        self.session_close_requested = False
        # Update timestamp for new session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.all_conv_file = os.path.join(
            self.all_conv_dir, f"conversation_{self.timestamp}.json"
        )

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            # Check for session close command
            if text.strip() == "/sc":
                self.session_close_requested = True
                break
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}

        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                # Process audio data first - this is critical for audio playback
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)

                # Handle input transcription (student's speech)
                if hasattr(response, "server_content") and response.server_content:
                    if (
                        hasattr(response.server_content, "input_transcription")
                        and response.server_content.input_transcription
                    ):
                        transcript_text = (
                            response.server_content.input_transcription.text
                        )
                        print(f"[Input Transcript]: {transcript_text}")

                        # Accumulate student transcription
                        if not self.is_student_turn:
                            # New student turn started
                            if self.current_ai_text:  # Save previous AI turn if exists
                                self.save_turn("AI", self.current_ai_text)
                                self.current_ai_text = ""
                            self.is_student_turn = True
                            self.is_ai_turn = False
                            self.current_student_text = transcript_text
                        else:
                            # Continue accumulating student turn
                            self.current_student_text += transcript_text

                    # Handle output transcription (AI's speech)
                    if (
                        hasattr(response.server_content, "output_transcription")
                        and response.server_content.output_transcription
                    ):
                        transcript_text = (
                            response.server_content.output_transcription.text
                        )
                        print(f"[Output Transcript]: {transcript_text}")

                        # Accumulate AI transcription
                        if not self.is_ai_turn:
                            # New AI turn started
                            if (
                                self.current_student_text
                            ):  # Save previous student turn if exists
                                self.save_turn("Student", self.current_student_text)
                                self.current_student_text = ""
                            self.is_ai_turn = True
                            self.is_student_turn = False
                            self.current_ai_text = transcript_text
                        else:
                            # Continue accumulating AI turn
                            self.current_ai_text += transcript_text

                    # Check for turn_complete - save current turn when complete
                    if (
                        hasattr(response.server_content, "turn_complete")
                        and response.server_content.turn_complete
                    ):
                        # Save current turn based on who was speaking
                        if self.current_student_text:
                            self.save_turn("Student", self.current_student_text)
                            self.current_student_text = ""
                            self.is_student_turn = False
                        elif self.current_ai_text:
                            self.save_turn("AI", self.current_ai_text)
                            self.current_ai_text = ""
                            self.is_ai_turn = False

                        # If you interrupt the model, it sends a turn_complete.
                        # For interruptions to work, we need to stop playback.
                        # So empty out the audio queue because it may have loaded
                        # much more audio than has played yet.
                        while not self.audio_in_queue.empty():
                            self.audio_in_queue.get_nowait()

                if text := response.text:
                    print(text, end="")

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            # Get config with current memory included in system instruction
            config = get_config()
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                tasks = []
                send_text_task = asyncio.create_task(self.send_text())
                tasks.append(send_text_task)
                tasks.append(asyncio.create_task(self.send_realtime()))
                tasks.append(asyncio.create_task(self.listen_audio()))
                tasks.append(asyncio.create_task(self.receive_audio()))
                tasks.append(asyncio.create_task(self.play_audio()))

                await send_text_task

                # Cancel other tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()

                raise asyncio.CancelledError("User requested exit")

        except asyncio.CancelledError:
            # Save any remaining turns before exiting
            if self.current_student_text:
                self.save_turn("Student", self.current_student_text)
            if self.current_ai_text:
                self.save_turn("AI", self.current_ai_text)

            # Final save
            if self.conversation:
                self.save_to_json()

            print("\n✅ Conversation saved to:")
            print(f"   - Last: {self.last_conv_file}")
            print(f"   - All: {self.all_conv_file}")

            # Automatically trigger memory analysis if /sc was used
            if self.session_close_requested and self.conversation:
                print("\n🔄 Triggering memory analysis...")
                memory_success = self.trigger_memory_analysis()
                if memory_success:
                    print("\n✅ Session closed. Memory generated and updated.")
                else:
                    print(
                        "\n⚠️  Session closed, but memory generation had issues. Check errors above."
                    )
                print("💡 Type '/start' to begin a new session or 'q' to quit.")
        except Exception as e:
            # Save any remaining turns on error
            if self.current_student_text:
                self.save_turn("Student", self.current_student_text)
            if self.current_ai_text:
                self.save_turn("AI", self.current_ai_text)

            # Final save on error
            if self.conversation:
                self.save_to_json()

            if self.audio_stream:
                self.audio_stream.close()
            print(f"\n❌ Error in session: {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
            print("\n💡 Type '/start' to begin a new session or 'q' to quit.")


async def main_loop():
    """Main loop that handles continuous sessions"""
    main = AudioLoop()

    print("=" * 60)
    print("🎤 Audio Conversation System")
    print("=" * 60)
    print("Commands:")
    print("  /start  - Start a new conversation session")
    print("  /sc     - Close current session and generate memory")
    print("  q       - Quit the application")
    print("=" * 60)

    while True:
        try:
            # Wait for /start command
            user_input = input(
                "\n💬 Enter command (/start to begin, q to quit): "
            ).strip()

            if user_input.lower() == "q":
                print("\n👋 Goodbye!")
                break

            elif user_input == "/start":
                print("\n🚀 Starting new session...")
                print("💡 Type '/sc' to close session and generate memory")
                print("=" * 60)

                # Reset for new session
                main.reset_session()

                # Run the session
                await main.run()

            else:
                print("❌ Invalid command. Use '/start' to begin or 'q' to quit.")

        except KeyboardInterrupt:
            print(
                "\n\n⚠️  Interrupted. Use '/sc' to close session gracefully or 'q' to quit."
            )
        except Exception as e:
            print(f"\n❌ Error: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main_loop())
