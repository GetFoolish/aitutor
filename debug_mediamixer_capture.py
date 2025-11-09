#!/usr/bin/env python3
"""
Debug script to visualize what MediaMixer is capturing
"""

import cv2
import numpy as np
import mss

def main():
    with mss.mss() as screen_capture:
        # Show available monitors
        print("Available monitors:")
        for i, monitor in enumerate(screen_capture.monitors):
            print(f"  Monitor {i}: {monitor}")

        # Capture primary display (what MediaMixer uses)
        print("\nCapturing from monitors[0] (primary display - ALL monitors combined):")
        monitor = screen_capture.monitors[0]
        print(f"  Resolution: {monitor['width']}x{monitor['height']}")

        # Take a screenshot
        screenshot = screen_capture.grab(monitor)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        print(f"  Captured frame shape: {frame.shape}")

        # Resize to what MediaMixer does (1280x720 for middle section)
        resized = cv2.resize(frame, (1280, 720))
        print(f"  Resized to: {resized.shape}")

        # Save both frames
        cv2.imwrite("/tmp/mediamixer_original.jpg", frame)
        cv2.imwrite("/tmp/mediamixer_resized.jpg", resized)

        print("\nSaved debug frames:")
        print("  Original: /tmp/mediamixer_original.jpg")
        print("  Resized (what Gemini sees): /tmp/mediamixer_resized.jpg")
        print("\nOpen these images to see if the question is readable!")

if __name__ == '__main__':
    main()
