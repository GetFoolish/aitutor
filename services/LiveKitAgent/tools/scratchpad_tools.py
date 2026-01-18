"""
Scratchpad Drawing Tools for AI Tutor Agent

These tools allow the AI agent to draw on the student's scratchpad
to explain concepts visually during tutoring sessions.

Uses livekit-agents function calling API.
"""

import json
from typing import Annotated
from livekit import rtc
from livekit.agents.llm import function_tool, ToolContext


# Global room reference for tools
_room: rtc.Room | None = None


def set_room(room: rtc.Room) -> None:
    """Set the room for scratchpad tools to use."""
    global _room
    _room = room
    print("[ScratchpadTools] Room set for data channel communication")


async def _send_command(command: dict) -> None:
    """Send a drawing command to the frontend via data channel."""
    global _room
    if _room is None:
        print("[ScratchpadTools] Error: Room not set")
        return

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
    except Exception as e:
        print(f"[ScratchpadTools] Error sending command: {e}")


@function_tool(
    name="write_text",
    description="Write text on the scratchpad to show work steps or explanations. Use this to write mathematical steps, hints, or explanations on the student's canvas."
)
async def write_text(
    x: Annotated[float, "X position (0-100, percentage of canvas width)"],
    y: Annotated[float, "Y position (0-100, percentage of canvas height)"],
    text: Annotated[str, "The text to write (can include math like '2 + 3 = 5')"],
) -> str:
    """Write text on the scratchpad."""
    await _send_command({
        "action": "write_text",
        "x": x,
        "y": y,
        "text": text,
        "color": "#1a1a1a",
        "font_size": 18.0
    })
    return f"Wrote '{text}' on the scratchpad at position ({x}, {y})"


@function_tool(
    name="draw_arrow",
    description="Draw an arrow on the scratchpad to point to something. Use this to draw attention to a specific part of the student's work."
)
async def draw_arrow(
    start_x: Annotated[float, "Arrow start X (0-100)"],
    start_y: Annotated[float, "Arrow start Y (0-100)"],
    end_x: Annotated[float, "Arrow end X where arrowhead points (0-100)"],
    end_y: Annotated[float, "Arrow end Y (0-100)"],
) -> str:
    """Draw an arrow on the scratchpad."""
    await _send_command({
        "action": "draw_arrow",
        "start_x": start_x,
        "start_y": start_y,
        "end_x": end_x,
        "end_y": end_y,
        "color": "#e63946",
        "stroke_width": 2.0
    })
    return f"Drew arrow pointing to ({end_x}, {end_y})"


@function_tool(
    name="draw_circle",
    description="Draw a circle on the scratchpad to highlight something. Use this to circle important items."
)
async def draw_circle(
    center_x: Annotated[float, "Circle center X (0-100)"],
    center_y: Annotated[float, "Circle center Y (0-100)"],
    radius: Annotated[float, "Circle radius (percentage units, typically 5-20)"],
) -> str:
    """Draw a circle on the scratchpad."""
    await _send_command({
        "action": "draw_circle",
        "center_x": center_x,
        "center_y": center_y,
        "radius": radius,
        "color": "#e63946",
        "fill": False
    })
    return f"Drew circle at ({center_x}, {center_y}) with radius {radius}"


@function_tool(
    name="clear_my_drawings",
    description="Clear all drawings made by the AI tutor. Use this before making new drawings."
)
async def clear_my_drawings() -> str:
    """Clear AI drawings from the scratchpad."""
    await _send_command({
        "action": "clear_ai_drawings"
    })
    return "Cleared AI tutor drawings from scratchpad"


@function_tool(
    name="highlight_area",
    description="Highlight an area on the scratchpad with a yellow overlay to draw attention to a region."
)
async def highlight_area(
    x: Annotated[float, "Top-left X position (0-100)"],
    y: Annotated[float, "Top-left Y position (0-100)"],
    width: Annotated[float, "Width (percentage units)"],
    height: Annotated[float, "Height (percentage units)"],
) -> str:
    """Highlight an area on the scratchpad."""
    await _send_command({
        "action": "highlight_area",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "color": "#ffd60a"
    })
    return f"Highlighted area at ({x}, {y}) with size {width}x{height}"


# Create the tool context with all scratchpad tools
def get_scratchpad_tool_context() -> ToolContext:
    """Get the tool context with all scratchpad drawing tools."""
    return ToolContext([
        write_text,
        draw_arrow,
        draw_circle,
        clear_my_drawings,
        highlight_area,
    ])
