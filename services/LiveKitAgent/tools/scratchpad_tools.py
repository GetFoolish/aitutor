"""
Scratchpad Drawing Tools for AI Tutor Agent

These tools allow the AI agent to draw on the student's scratchpad
to explain concepts visually during tutoring sessions.
"""

import json
import asyncio
from typing import Optional, Literal
from livekit import rtc


class ScratchpadTools:
    """Tools for the AI agent to draw on the student's scratchpad."""

    def __init__(self, room: rtc.Room):
        """Initialize scratchpad tools with LiveKit room for data channel.

        Args:
            room: The LiveKit room to send drawing commands through
        """
        self._room = room
        self._command_queue: list[dict] = []

    async def _send_command(self, command: dict) -> None:
        """Send a drawing command to the frontend via data channel.

        Args:
            command: The drawing command to send
        """
        try:
            data = json.dumps({
                "type": "scratchpad_command",
                "command": command
            }).encode('utf-8')

            await self._room.local_participant.publish_data(
                data,
                reliable=True,
                topic="scratchpad"
            )
            print(f"[ScratchpadTools] Sent command: {command['action']}")
        except Exception as e:
            print(f"[ScratchpadTools] Error sending command: {e}")

    async def draw_line(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        color: str = "#1a1a1a",
        stroke_width: float = 2.0
    ) -> str:
        """Draw a line on the scratchpad.

        Use this to draw lines, underlines, or arrows to point to things.
        Coordinates are in percentage of canvas (0-100).

        Args:
            start_x: Starting X position (0-100, percentage of canvas width)
            start_y: Starting Y position (0-100, percentage of canvas height)
            end_x: Ending X position (0-100)
            end_y: Ending Y position (0-100)
            color: Line color in hex format (default: black)
            stroke_width: Line thickness (default: 2.0)

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "draw_line",
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "color": color,
            "stroke_width": stroke_width
        })
        return f"Drew line from ({start_x}, {start_y}) to ({end_x}, {end_y})"

    async def draw_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        color: str = "#1a1a1a",
        fill: bool = False
    ) -> str:
        """Draw a circle on the scratchpad.

        Use this to circle important items or draw attention to something.

        Args:
            center_x: Center X position (0-100, percentage of canvas width)
            center_y: Center Y position (0-100, percentage of canvas height)
            radius: Circle radius (in percentage units)
            color: Circle color in hex format
            fill: Whether to fill the circle

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "draw_circle",
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "color": color,
            "fill": fill
        })
        return f"Drew circle at ({center_x}, {center_y}) with radius {radius}"

    async def draw_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = "#1a1a1a",
        fill: bool = False
    ) -> str:
        """Draw a rectangle on the scratchpad.

        Use this to highlight areas or create boxes for grouping.

        Args:
            x: Top-left X position (0-100)
            y: Top-left Y position (0-100)
            width: Rectangle width (percentage units)
            height: Rectangle height (percentage units)
            color: Rectangle color in hex format
            fill: Whether to fill the rectangle

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "draw_rectangle",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color,
            "fill": fill
        })
        return f"Drew rectangle at ({x}, {y}) with size {width}x{height}"

    async def write_text(
        self,
        x: float,
        y: float,
        text: str,
        color: str = "#1a1a1a",
        font_size: float = 16.0
    ) -> str:
        """Write text on the scratchpad.

        Use this to write explanations, labels, or show work steps.
        Great for showing mathematical steps or writing hints.

        Args:
            x: Text X position (0-100)
            y: Text Y position (0-100)
            text: The text to write (can include math like "2 + 3 = 5")
            color: Text color in hex format
            font_size: Font size

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "write_text",
            "x": x,
            "y": y,
            "text": text,
            "color": color,
            "font_size": font_size
        })
        return f"Wrote '{text}' at ({x}, {y})"

    async def draw_arrow(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        color: str = "#e63946",
        stroke_width: float = 2.0
    ) -> str:
        """Draw an arrow on the scratchpad.

        Use this to point to specific areas or show direction/flow.

        Args:
            start_x: Arrow start X position (0-100)
            start_y: Arrow start Y position (0-100)
            end_x: Arrow end X position (0-100, where the arrowhead points)
            end_y: Arrow end Y position (0-100)
            color: Arrow color in hex format (default: red)
            stroke_width: Arrow line thickness

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "draw_arrow",
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "color": color,
            "stroke_width": stroke_width
        })
        return f"Drew arrow from ({start_x}, {start_y}) to ({end_x}, {end_y})"

    async def clear_my_drawings(self) -> str:
        """Clear all drawings made by the AI tutor.

        Use this to clean up your drawings before making new ones.
        Does NOT clear the student's work.

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "clear_ai_drawings"
        })
        return "Cleared AI tutor drawings from scratchpad"

    async def highlight_area(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = "#ffd60a"
    ) -> str:
        """Highlight an area on the scratchpad with a semi-transparent overlay.

        Use this to draw attention to a specific region of the student's work.

        Args:
            x: Top-left X position (0-100)
            y: Top-left Y position (0-100)
            width: Highlight width (percentage units)
            height: Highlight height (percentage units)
            color: Highlight color (default: yellow)

        Returns:
            Confirmation message
        """
        await self._send_command({
            "action": "highlight_area",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color
        })
        return f"Highlighted area at ({x}, {y}) with size {width}x{height}"

    def get_tools(self) -> list:
        """Return the list of tools for the agent to use."""
        return [
            self.draw_line,
            self.draw_circle,
            self.draw_rectangle,
            self.write_text,
            self.draw_arrow,
            self.clear_my_drawings,
            self.highlight_area,
        ]
