#!/usr/bin/env python3
"""
Session Processor for Memory System Testing

Processes simulated session files through the v4+v5 memory pipeline:
1. Extracts memories from conversations
2. Stores memories in Pinecone vector database
3. Updates/generates the Living Biography

Usage:
    python process_sessions.py --sessions-dir simulated_sessions/leo_takahashi
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()


def process_sessions(sessions_dir: str, student_id: str = None):
    """Process all sessions through the memory pipeline."""

    # Import memory system components
    from services.TeachingAssistant.Memory.vector_store import MemoryStore
    from services.TeachingAssistant.Memory.extractor import MemoryExtractor
    from services.TeachingAssistant.core.biographer import BiographerAgent

    sessions_path = Path(sessions_dir)

    # Load manifest
    manifest_path = sessions_path / "_manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    persona = manifest.get("persona", {})
    if not student_id:
        student_id = persona.get("name", "unknown").lower().replace(" ", "_")

    print(f"\n{'='*70}")
    print(f"[PROCESSOR] Processing sessions for: {persona.get('name', student_id)}")
    print(f"[PROCESSOR] Student ID: {student_id}")
    print(f"[PROCESSOR] Sessions directory: {sessions_path}")
    print(f"[PROCESSOR] Total sessions: {manifest.get('total_sessions', 0)}")
    print(f"{'='*70}\n")

    # Initialize components
    print("[PROCESSOR] Initializing memory components...")
    memory_store = MemoryStore(user_id=student_id)
    memory_extractor = MemoryExtractor()
    biographer = BiographerAgent()

    if not memory_store.enabled:
        print("WARNING: Memory store not enabled (check Pinecone API key)")
    if not memory_extractor.enabled:
        print("WARNING: Memory extractor not enabled (check Gemini API key)")
    if not biographer.enabled:
        print("WARNING: Biographer not enabled (check Gemini API key)")

    # Track overall statistics
    total_memories = 0
    total_emotions = []
    total_breakthroughs = []
    all_topics = []
    session_summaries = []

    # Process each session
    for session_info in manifest.get("sessions", []):
        session_file = sessions_path / session_info["filename"]

        if not session_file.exists():
            print(f"  WARNING: Session file not found: {session_file}")
            continue

        with open(session_file, 'r') as f:
            session_data = json.load(f)

        session_num = session_data.get("session_number", 0)
        topic = session_data.get("topic", "Unknown")
        conversation = session_data.get("conversation", [])

        print(f"\n[SESSION {session_num}] Processing: {topic}")
        print(f"  Turns: {len(conversation)}")

        # Convert conversation format for extractor
        exchanges = []
        for turn in conversation:
            exchanges.append({
                "student": turn.get("student", ""),
                "tutor": turn.get("tutor", "")
            })

        # Extract memories
        session_id = f"session_{session_num}"
        extraction_result = memory_extractor.extract_memories_batch(
            student_id=student_id,
            session_id=session_id,
            exchanges=exchanges
        )

        memories = extraction_result.get("memories", [])
        emotions = extraction_result.get("emotions", [])
        breakthroughs = extraction_result.get("breakthroughs", [])

        print(f"  Memories extracted: {len(memories)}")
        print(f"  Emotions detected: {emotions}")
        print(f"  Breakthroughs: {len(breakthroughs)}")

        # Store memories in vector database
        if memories and memory_store.enabled:
            saved_count = memory_store.save_memories_batch(memories)
            print(f"  Memories saved to Pinecone: {saved_count}")
            total_memories += saved_count

        # Track for biography
        total_emotions.extend(emotions)
        total_breakthroughs.extend(breakthroughs)
        all_topics.append(topic)

        session_summaries.append({
            "session_number": session_num,
            "topic": topic,
            "memories_extracted": len(memories),
            "emotions": emotions,
            "breakthroughs": breakthroughs
        })

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    # Generate/Update Biography
    print(f"\n{'='*70}")
    print("[BIOGRAPHY] Generating Living Biography...")
    print(f"{'='*70}")

    # Prepare biography input data
    onboarding_data = {
        "core_values": persona.get("personality_traits", []),
        "north_star_goals": [persona.get("core_motivation", "")],
        "personality_traits": persona.get("personality_traits", []),
        "blind_spots": persona.get("dislikes", []),
        "emotional_baseline": "curious",
        "interests": list(persona.get("interests_and_hobbies", {}).keys()),
    }

    # Generate initial biography
    biography = biographer.generate_initial_biography(
        name=persona.get("name", student_id),
        onboarding_data=onboarding_data
    )

    if biography:
        print("\n[BIOGRAPHY] Initial Biography Generated:")
        print("-" * 50)
        print(biography)
        print("-" * 50)

    # Now update biography based on session summaries
    if biography and session_summaries:
        print("\n[BIOGRAPHY] Updating biography with session data...")

        # Build comprehensive transcript from all sessions
        all_turns = []
        for session_info in manifest.get("sessions", []):
            session_file = sessions_path / session_info["filename"]
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                for turn in session_data.get("conversation", []):
                    all_turns.append({
                        "speaker": "student",
                        "text": turn.get("student", "")
                    })
                    all_turns.append({
                        "speaker": "tutor",
                        "text": turn.get("tutor", "")
                    })

        # Create session summary for biography update
        session_summary = {
            "topics_covered": list(set(all_topics)),
            "emotional_arc": total_emotions[:20] if total_emotions else ["engaged"],
            "key_moments": total_breakthroughs[:10] if total_breakthroughs else [],
            "questions_answered": len(manifest.get("sessions", [])) * 5,
            "questions_correct": len(manifest.get("sessions", [])) * 3,
        }

        updated_biography = biographer.update_biography(
            current_biography=biography,
            session_transcript=all_turns[-100:],  # Last 100 turns
            session_summary=session_summary
        )

        if updated_biography:
            print("\n[BIOGRAPHY] Updated Biography:")
            print("-" * 50)
            print(updated_biography)
            print("-" * 50)
            biography = updated_biography

    # Save results
    results_dir = sessions_path / "memory_results"
    results_dir.mkdir(exist_ok=True)

    # Save biography
    biography_path = results_dir / "living_biography.txt"
    with open(biography_path, 'w') as f:
        f.write(biography or "No biography generated")

    # ================================================================
    # PROVENANCE TRACKING - Save exact inputs used for biography
    # ================================================================

    # Build detailed provenance for the transcript used
    transcript_provenance = []
    turn_index = 0
    for session_info in manifest.get("sessions", []):
        session_file = sessions_path / session_info["filename"]
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            session_num = session_data.get("session_number", 0)
            topic = session_data.get("topic", "Unknown")
            for i, turn in enumerate(session_data.get("conversation", [])):
                transcript_provenance.append({
                    "global_turn_index": turn_index,
                    "session_number": session_num,
                    "session_file": session_info["filename"],
                    "topic": topic,
                    "turn_in_session": i + 1,
                    "student_message": turn.get("student", ""),
                    "tutor_message": turn.get("tutor", "")
                })
                turn_index += 1

    # Calculate which turns were actually used (last 100 turns = last 50 exchanges)
    total_turns = len(transcript_provenance)
    used_start_index = max(0, total_turns - 50)  # Last 50 exchanges (100 speaker turns)
    used_turns = transcript_provenance[used_start_index:]

    # Create the biography sources file with full provenance
    biography_sources = {
        "generated_at": datetime.now().isoformat(),
        "student_id": student_id,
        "student_name": persona.get("name", "Unknown"),

        # Initial biography inputs
        "initial_biography_inputs": {
            "onboarding_data": onboarding_data,
            "source": "Persona file (_persona.json)"
        },

        # Update biography inputs
        "update_biography_inputs": {
            "session_summary": session_summary,
            "transcript_stats": {
                "total_exchanges_available": total_turns,
                "exchanges_used": len(used_turns),
                "used_range": f"exchanges {used_start_index + 1} to {total_turns}",
            },
            "sessions_contributing_to_transcript": list(set(
                t["session_file"] for t in used_turns
            )),
        },

        # Detailed breakdown by session
        "session_contributions": [],

        # The actual transcript used (with source tracking)
        "transcript_used": []
    }

    # Calculate per-session contribution
    session_turn_counts = {}
    for turn in used_turns:
        sess_file = turn["session_file"]
        if sess_file not in session_turn_counts:
            session_turn_counts[sess_file] = {
                "session_number": turn["session_number"],
                "topic": turn["topic"],
                "turns_used": 0,
                "turn_range": {"first": turn["turn_in_session"], "last": turn["turn_in_session"]}
            }
        session_turn_counts[sess_file]["turns_used"] += 1
        session_turn_counts[sess_file]["turn_range"]["last"] = turn["turn_in_session"]

    biography_sources["session_contributions"] = [
        {
            "file": fname,
            "session_number": info["session_number"],
            "topic": info["topic"],
            "turns_used": info["turns_used"],
            "turn_range": f"{info['turn_range']['first']}-{info['turn_range']['last']}"
        }
        for fname, info in session_turn_counts.items()
    ]

    # Save the actual transcript with provenance markers
    for turn in used_turns:
        biography_sources["transcript_used"].append({
            "source": f"Session {turn['session_number']}: {turn['topic']} (turn {turn['turn_in_session']})",
            "file": turn["session_file"],
            "student": turn["student_message"],
            "tutor": turn["tutor_message"]
        })

    # Save biography sources
    sources_path = results_dir / "biography_sources.json"
    with open(sources_path, 'w') as f:
        json.dump(biography_sources, f, indent=2)

    # Also save a human-readable provenance report
    provenance_report_path = results_dir / "biography_provenance.txt"
    with open(provenance_report_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("LIVING BIOGRAPHY - SOURCE PROVENANCE REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Student: {persona.get('name', student_id)}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        f.write("-" * 70 + "\n")
        f.write("INITIAL BIOGRAPHY SOURCES:\n")
        f.write("-" * 70 + "\n")
        f.write("Source: Persona file (_persona.json)\n\n")
        f.write("Onboarding data used:\n")
        for key, value in onboarding_data.items():
            f.write(f"  - {key}: {value}\n")
        f.write("\n")

        f.write("-" * 70 + "\n")
        f.write("BIOGRAPHY UPDATE SOURCES:\n")
        f.write("-" * 70 + "\n\n")

        f.write("Session Summary Data:\n")
        f.write(f"  - Topics covered: {session_summary['topics_covered']}\n")
        f.write(f"  - Emotional arc: {session_summary['emotional_arc']}\n")
        f.write(f"  - Key moments/breakthroughs: {len(session_summary['key_moments'])}\n\n")

        f.write("Transcript Used:\n")
        f.write(f"  - Total exchanges available: {total_turns}\n")
        f.write(f"  - Exchanges used: {len(used_turns)} (last {len(used_turns)} of {total_turns})\n\n")

        f.write("Sessions Contributing to Biography Update:\n")
        for contrib in biography_sources["session_contributions"]:
            f.write(f"  - {contrib['file']}\n")
            f.write(f"    Topic: {contrib['topic']}\n")
            f.write(f"    Turns used: {contrib['turns_used']} (turns {contrib['turn_range']})\n\n")

        f.write("-" * 70 + "\n")
        f.write("FULL TRANSCRIPT USED (with source markers):\n")
        f.write("-" * 70 + "\n\n")

        current_session = None
        for turn in used_turns:
            if turn["session_file"] != current_session:
                current_session = turn["session_file"]
                f.write(f"\n{'='*50}\n")
                f.write(f"SESSION {turn['session_number']}: {turn['topic']}\n")
                f.write(f"File: {turn['session_file']}\n")
                f.write(f"{'='*50}\n\n")

            f.write(f"[Turn {turn['turn_in_session']}]\n")
            f.write(f"STUDENT: {turn['student_message'][:500]}{'...' if len(turn['student_message']) > 500 else ''}\n")
            f.write(f"TUTOR: {turn['tutor_message'][:500]}{'...' if len(turn['tutor_message']) > 500 else ''}\n\n")

    print(f"\n[PROVENANCE] Saved biography source tracking:")
    print(f"  - biography_sources.json (machine-readable)")
    print(f"  - biography_provenance.txt (human-readable report)")

    # ================================================================
    # END PROVENANCE TRACKING
    # ================================================================

    # Save processing summary
    summary = {
        "processed_at": datetime.now().isoformat(),
        "student_id": student_id,
        "student_name": persona.get("name", "Unknown"),
        "total_sessions_processed": len(session_summaries),
        "total_memories_extracted": total_memories,
        "unique_emotions_detected": list(set(total_emotions)),
        "total_breakthroughs": len(total_breakthroughs),
        "topics_covered": list(set(all_topics)),
        "session_summaries": session_summaries,
        "biography_generated": bool(biography),
        "provenance_files": ["biography_sources.json", "biography_provenance.txt"]
    }

    summary_path = results_dir / "processing_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    # Save biography as JSON too
    biography_json_path = results_dir / "living_biography.json"
    with open(biography_json_path, 'w') as f:
        json.dump({
            "student_id": student_id,
            "student_name": persona.get("name", "Unknown"),
            "biography": biography,
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "sessions_included": len(session_summaries),
            "provenance": "See biography_sources.json for detailed source tracking"
        }, f, indent=2)

    print(f"\n{'='*70}")
    print("[PROCESSOR] COMPLETE!")
    print(f"  Sessions processed: {len(session_summaries)}")
    print(f"  Total memories saved: {total_memories}")
    print(f"  Emotions detected: {len(set(total_emotions))} unique")
    print(f"  Breakthroughs identified: {len(total_breakthroughs)}")
    print(f"  Results saved to: {results_dir}")
    print(f"{'='*70}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Process simulated sessions through memory system")
    parser.add_argument("--sessions-dir", type=str, required=True, help="Path to sessions directory")
    parser.add_argument("--student-id", type=str, default=None, help="Override student ID")
    args = parser.parse_args()

    # Resolve path
    if not Path(args.sessions_dir).is_absolute():
        script_dir = Path(__file__).parent
        sessions_dir = script_dir / args.sessions_dir
    else:
        sessions_dir = Path(args.sessions_dir)

    if not sessions_dir.exists():
        print(f"ERROR: Sessions directory not found: {sessions_dir}")
        sys.exit(1)

    process_sessions(str(sessions_dir), args.student_id)


if __name__ == "__main__":
    main()
