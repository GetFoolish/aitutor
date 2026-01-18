"""
Smart Scratchpad Drawing Tools for AI Tutor Agent

These tools allow the AI agent to draw on the student's scratchpad
WITHOUT needing to specify coordinates. The system automatically
positions content in a logical flow.
"""

import json
from typing import Annotated
from livekit import rtc
from livekit.agents import RunContext
from livekit.agents.llm import function_tool


# Global room reference for tools
_room: rtc.Room | None = None

# Auto-positioning state - tracks where to place next item
_next_y_position: float = 10.0  # Start near top
_line_height: float = 8.0  # Space between lines


def set_room(room: rtc.Room) -> None:
    """Set the room for scratchpad tools to use."""
    global _room, _next_y_position
    _room = room
    _next_y_position = 10.0  # Reset position for new session
    print("[ScratchpadTools] Room set for data channel communication")


def _get_next_position() -> tuple[float, float]:
    """Get the next auto-position and advance the cursor."""
    global _next_y_position
    x = 10.0  # Left margin
    y = _next_y_position
    _next_y_position += _line_height

    # Wrap to top if we go too far down
    if _next_y_position > 85:
        _next_y_position = 10.0

    return x, y


async def _send_command(command: dict) -> bool:
    """Send a drawing command to the frontend via data channel."""
    global _room
    if _room is None:
        print("[ScratchpadTools] Error: Room not set")
        return False

    try:
        data = json.dumps({
            "type": "scratchpad_command",
            "command": command
        }).encode('utf-8')

        await _room.local_participant.publish_data(
            data,
            reliable=True,
            topic="scratchpad"
        )
        print(f"[ScratchpadTools] Sent command: {command['action']}")
        return True
    except Exception as e:
        print(f"[ScratchpadTools] Error sending command: {e}")
        import traceback
        traceback.print_exc()
        return False


@function_tool
async def write_on_scratchpad(
    text: Annotated[str, "The text to write (math equations, explanations, steps, etc.)"],
) -> str:
    """Write text or math on the scratchpad to explain something to the student. Just provide the text - positioning is automatic. Use this to show steps, write equations, or add explanations."""
    print(f"[ScratchpadTools] >>> TOOL CALLED: write_on_scratchpad with text='{text}'")
    x, y = _get_next_position()

    success = await _send_command({
        "action": "write_text",
        "x": x,
        "y": y,
        "text": text,
        "color": "#2563eb",  # Blue for tutor's writing
        "font_size": 20.0
    })
    if success:
        return f"Successfully wrote '{text}' on the scratchpad"
    else:
        return f"Failed to write on scratchpad - room may not be connected"


@function_tool
async def draw_arrow_to_area(
    area: Annotated[str, "Where to point: 'top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right'"],
) -> str:
    """Draw an arrow pointing to a general area of the scratchpad. Use 'top', 'middle', 'bottom' for vertical and 'left', 'center', 'right' for horizontal."""
    # Map area names to coordinates
    area_coords = {
        "top-left": (25, 20),
        "top-center": (50, 20),
        "top-right": (75, 20),
        "middle-left": (25, 50),
        "middle-center": (50, 50),
        "middle-right": (75, 50),
        "bottom-left": (25, 80),
        "bottom-center": (50, 80),
        "bottom-right": (75, 80),
    }

    target = area_coords.get(area.lower(), (50, 50))

    # Arrow starts from the side and points to target
    start_x = 5 if target[0] > 50 else 95
    start_y = target[1]

    await _send_command({
        "action": "draw_arrow",
        "start_x": start_x,
        "start_y": start_y,
        "end_x": target[0],
        "end_y": target[1],
        "color": "#dc2626",  # Red for emphasis
        "stroke_width": 3.0
    })
    return f"Drew arrow pointing to {area}"


@function_tool
async def circle_area(
    area: Annotated[str, "Area to circle: 'top-left', 'top-center', 'top-right', 'middle-left', 'middle-center', 'middle-right', 'bottom-left', 'bottom-center', 'bottom-right'"],
) -> str:
    """Draw a circle to highlight an area of the scratchpad. Use 'top', 'middle', 'bottom' for vertical and 'left', 'center', 'right' for horizontal."""
    area_coords = {
        "top-left": (25, 20),
        "top-center": (50, 20),
        "top-right": (75, 20),
        "middle-left": (25, 50),
        "middle-center": (50, 50),
        "middle-right": (75, 50),
        "bottom-left": (25, 80),
        "bottom-center": (50, 80),
        "bottom-right": (75, 80),
    }

    center = area_coords.get(area.lower(), (50, 50))

    await _send_command({
        "action": "draw_circle",
        "center_x": center[0],
        "center_y": center[1],
        "radius": 15,
        "color": "#dc2626",  # Red for emphasis
        "fill": False
    })
    return f"Circled the {area} area"


@function_tool
async def clear_tutor_drawings() -> str:
    """Clear all drawings and text that the tutor has added to the scratchpad. Use this before starting a new explanation."""
    global _next_y_position
    _next_y_position = 10.0  # Reset position

    await _send_command({
        "action": "clear_ai_drawings"
    })
    return "Cleared tutor drawings from scratchpad"


@function_tool
async def open_scratchpad() -> str:
    """Open and show the scratchpad/whiteboard to the student. Call this FIRST before writing anything, like a teacher walking to the whiteboard."""
    await _send_command({
        "action": "open_scratchpad"
    })
    return "Opened the scratchpad for the student to see"


@function_tool
async def show_step_by_step(
    steps: Annotated[str, "The steps to show, separated by newlines or semicolons. Example: 'Step 1: Add 2+2; Step 2: Result is 4'"],
) -> str:
    """Write multiple steps on the scratchpad, one after another. Provide a list of steps separated by newlines or semicolons."""
    # Split by semicolons or newlines
    step_list = [s.strip() for s in steps.replace('\n', ';').split(';') if s.strip()]

    for step in step_list:
        x, y = _get_next_position()
        await _send_command({
            "action": "write_text",
            "x": x,
            "y": y,
            "text": step,
            "color": "#2563eb",
            "font_size": 18.0
        })

    return f"Wrote {len(step_list)} steps on the scratchpad"


# Get list of all scratchpad tools
def get_scratchpad_tools() -> list:
    """Get the list of scratchpad drawing tools for AgentSession."""
    tools = [
        open_scratchpad,
        write_on_scratchpad,
        draw_arrow_to_area,
        circle_area,
        clear_tutor_drawings,
        show_step_by_step,
    ]
    # Debug: print tool info
    for tool in tools:
        print(f"[ScratchpadTools] Registered tool: {getattr(tool, 'name', tool.__name__)}")
    return tools
