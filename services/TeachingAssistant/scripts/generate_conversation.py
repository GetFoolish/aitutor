#!/usr/bin/env python3
"""
Conversation Generator for Testing Memory System

Generates realistic teacher-student conversations based on a student persona.
Uses Gemini to create organic dialogue that naturally reveals persona details.

Saves each session as a separate file in an organized folder structure:
  output/
    persona_name/
      session_001_topic_name.json
      session_002_topic_name.json
      ...
      _manifest.json (summary of all sessions)

Usage:
    python generate_conversation.py --persona leo_takahashi.json --sessions 20 --turns-per-session 25
"""

import os
import sys
import json
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

# Try Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("WARNING: google-generativeai not installed")


class ConversationGenerator:
    """Generates realistic tutoring conversations based on student personas."""

    # Math topics that can be covered across sessions
    MATH_TOPICS = [
        "Quadratic equations",
        "Factoring polynomials",
        "The discriminant",
        "Graphing parabolas",
        "Systems of equations",
        "Linear inequalities",
        "Slope and y-intercept",
        "Functions and domain/range",
        "Exponential growth and decay",
        "Logarithms basics",
        "Trigonometry introduction",
        "Pythagorean theorem applications",
        "Word problems with percentages",
        "Ratios and proportions",
        "Sequences and series",
        "Probability basics",
        "Statistics and mean/median",
        "Geometry - area and volume",
        "Coordinate geometry",
        "Absolute value equations",
    ]

    # Session themes that encourage personal sharing
    SESSION_THEMES = [
        "warm_up",  # Casual chat before math
        "struggle_moment",  # Student frustrated, reveals personal stuff
        "connection_moment",  # Math connects to student's interests
        "breakthrough",  # Student gets it, celebrates
        "tangent",  # Student goes off-topic briefly
        "motivation_check",  # Tutor checks in on goals/life
        "review",  # Going over previous material
        "new_concept",  # Introducing something new
    ]

    def __init__(self, persona_path: str, output_dir: str):
        """Initialize with a student persona."""
        self.persona = self._load_persona(persona_path)
        self.output_dir = Path(output_dir)
        self.model = None
        self.conversation_history: List[Dict[str, str]] = []
        self.revealed_facts: List[str] = []
        self.session_count = 0
        self.all_sessions_metadata = []

        # Create output directory
        persona_name = self.persona['name'].lower().replace(' ', '_')
        self.session_output_dir = self.output_dir / persona_name
        self.session_output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print(f"[GENERATOR] Initialized with Gemini")
            print(f"[GENERATOR] Output directory: {self.session_output_dir}")
        else:
            print("[GENERATOR] ERROR: No Gemini API key available")
            sys.exit(1)

    def _load_persona(self, path: str) -> Dict[str, Any]:
        """Load persona from JSON file."""
        with open(path, 'r') as f:
            return json.load(f)

    def _get_persona_context(self) -> str:
        """Build persona context string for the LLM."""
        p = self.persona
        return f"""Student Persona:
Name: {p['name']}
Age: {p['age']}, Grade: {p['grade']}
Location: {p['location']['neighborhood']}, {p['location']['city']}, {p['location']['state']}

Family:
- Father: {p['family']['father']['name']} ({p['family']['father']['occupation']})
- Mother: {p['family']['mother']['name']} ({p['family']['mother']['occupation']})
- Pet: {p['family']['pet']['name']} the {p['family']['pet']['type']} - {p['family']['pet']['description']}

Personality: {', '.join(p['personality_traits'])}

Hobbies:
- Film Photography: {p['interests_and_hobbies']['film_photography']['description']} with {p['interests_and_hobbies']['film_photography']['equipment']}
- Bouldering: {p['interests_and_hobbies']['bouldering']['frequency']}
- Lofi Music: {p['interests_and_hobbies']['lofi_music_production']['style']}
- Retro Gaming: {p['interests_and_hobbies']['retro_gaming']['preference']}

Likes: {', '.join(p['likes'])}
Dislikes: {', '.join(p['dislikes'])}

Key Life Events:
1. The Great Escape (age 7): {p['key_life_incidents']['the_great_escape']['description']}
2. The Coastline Project (age 15): {p['key_life_incidents']['the_coastline_project']['description']}
3. The Gallery Rejection (age 16): {p['key_life_incidents']['the_gallery_rejection']['description']}

Core Motivation: {p['core_motivation']}

Academic: Struggles with {', '.join(p['academic_context']['struggles'])}. Learning style: {p['academic_context']['learning_style']}
"""

    def _select_facts_to_reveal(self, theme: str) -> List[str]:
        """Select which persona facts might naturally come up in this exchange."""
        all_facts = [
            f"Has a dog named {self.persona['family']['pet']['name']}",
            f"Lives in {self.persona['location']['neighborhood']}, {self.persona['location']['city']}",
            f"Father {self.persona['family']['father']['name']} is a {self.persona['family']['father']['occupation']}",
            f"Mother {self.persona['family']['mother']['name']} is a {self.persona['family']['mother']['occupation']}",
            f"Does film photography with a vintage 35mm Nikon",
            f"Goes bouldering three times a week",
            f"Makes lofi music mixing city sounds with jazz",
            f"Loves restoring old Game Boys",
            f"Likes rainy mornings and thrift stores",
            f"Dislikes crowds and fluorescent lighting",
            f"Once tracked {self.persona['family']['pet']['name']} for 6 hours as a kid",
            f"Started an environmental club after seeing invasive species",
            f"Got rejected from a gallery but later featured at a coffee shop",
            f"Interested in environmental science",
            f"Procrastinates but is aware of it",
            f"Collects enamel pins",
            f"Loves spicy miso ramen",
            f"Prefers libraries over crowded places",
            f"Captures 'liminal spaces' and abandoned urban spots",
            f"Motivated to document things before they change or disappear",
        ]

        # Filter out already heavily revealed facts (but allow some repetition)
        available = [f for f in all_facts if self.revealed_facts.count(f) < 3]
        if not available:
            available = all_facts

        # Select 1-3 facts based on theme
        if theme in ["warm_up", "tangent", "motivation_check"]:
            return random.sample(available, min(3, len(available)))
        elif theme in ["connection_moment", "struggle_moment"]:
            return random.sample(available, min(2, len(available)))
        else:
            return random.sample(available, min(1, len(available)))

    def generate_session(
        self,
        session_number: int,
        turns_per_session: int = 25,
        math_topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a single tutoring session and save to file."""
        if not math_topic:
            math_topic = self.MATH_TOPICS[(session_number - 1) % len(self.MATH_TOPICS)]

        session_turns = []
        themes_used = []

        # Plan session structure
        session_themes = []
        session_themes.append("warm_up")  # Always start with warmup

        # Add variety of themes
        remaining_turns = turns_per_session - 4  # Reserve for warmup and closing
        while remaining_turns > 0:
            theme = random.choice(["new_concept", "struggle_moment", "connection_moment",
                                   "breakthrough", "tangent", "review"])
            session_themes.append(theme)
            themes_used.append(theme)
            remaining_turns -= random.randint(3, 6)

        session_themes.append("motivation_check")  # End with check-in

        print(f"\n  Session {session_number}: Topic='{math_topic}'")
        print(f"    Themes: {', '.join(session_themes[:6])}...")

        # Generate each section
        session_facts_revealed = []
        for i, theme in enumerate(session_themes):
            facts_to_reveal = self._select_facts_to_reveal(theme)

            prompt = self._build_generation_prompt(
                session_number=session_number,
                theme=theme,
                math_topic=math_topic,
                facts_to_reveal=facts_to_reveal,
                is_session_start=(i == 0),
                is_session_end=(i == len(session_themes) - 1),
                recent_history=session_turns[-6:] if session_turns else []
            )

            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.8,
                        max_output_tokens=2000,
                    )
                )

                # Parse the generated turns
                new_turns = self._parse_turns(response.text)
                session_turns.extend(new_turns)

                # Track revealed facts
                for fact in facts_to_reveal:
                    for turn in new_turns:
                        student_text = turn.get("student", "").lower()
                        if any(word in student_text for word in fact.lower().split()[:3]):
                            self.revealed_facts.append(fact)
                            session_facts_revealed.append(fact)
                            break

            except Exception as e:
                print(f"    Error generating {theme}: {e}")
                continue

        # Build session data
        session_data = {
            "session_number": session_number,
            "student_id": self.persona['name'].lower().replace(' ', '_'),
            "student_name": self.persona['name'],
            "topic": math_topic,
            "themes": themes_used,
            "generated_at": datetime.utcnow().isoformat(),
            "turn_count": len(session_turns),
            "facts_revealed": list(set(session_facts_revealed)),
            "conversation": session_turns
        }

        # Save session to file
        topic_slug = math_topic.lower().replace(' ', '_').replace('/', '_')
        filename = f"session_{session_number:03d}_{topic_slug}.json"
        filepath = self.session_output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f"    Generated {len(session_turns)} turns")
        print(f"    Facts revealed: {len(session_facts_revealed)}")
        print(f"    Saved to: {filename}")

        # Track metadata
        self.all_sessions_metadata.append({
            "session_number": session_number,
            "filename": filename,
            "topic": math_topic,
            "turn_count": len(session_turns),
            "facts_revealed": len(session_facts_revealed)
        })

        return session_data

    def _build_generation_prompt(
        self,
        session_number: int,
        theme: str,
        math_topic: str,
        facts_to_reveal: List[str],
        is_session_start: bool,
        is_session_end: bool,
        recent_history: List[Dict[str, str]]
    ) -> str:
        """Build the prompt for generating conversation turns."""
        history_str = ""
        if recent_history:
            history_str = "Recent conversation:\n" + "\n".join([
                f"TUTOR: {t.get('tutor', '')}\nSTUDENT: {t.get('student', '')}"
                for t in recent_history[-4:]
            ])

        theme_instructions = {
            "warm_up": "The tutor greets the student warmly and asks about their week/life. Student shares something personal about their hobbies, family, or recent experiences.",
            "struggle_moment": "The student is confused or frustrated with the math. They might mention how stress affects their other activities or compare math to something they're better at.",
            "connection_moment": "The tutor makes a brilliant connection between the math concept and something the student loves (photography angles, climbing physics, music patterns, etc.).",
            "breakthrough": "The student finally gets it! They're excited and might relate the concept to their own life experience or interests.",
            "tangent": "The conversation briefly goes off-topic as the student naturally shares something about their life, family, hobbies, or a recent experience.",
            "motivation_check": "The tutor asks about the student's goals, how they're feeling about school, or what's going on in their life. Student opens up.",
            "review": "Going over previous material, student recalls or struggles with concepts, might mention how they tried to practice.",
            "new_concept": "Introducing new material with step by step explanation, student asks clarifying questions.",
        }

        return f"""You are generating a realistic tutoring conversation between an AI tutor named Adam and a high school student.

{self._get_persona_context()}

CURRENT SESSION: #{session_number}
MATH TOPIC: {math_topic}
THEME FOR THIS SEGMENT: {theme}
THEME INSTRUCTIONS: {theme_instructions.get(theme, "Normal tutoring exchange")}

{"This is the START of the session - begin with natural greetings, maybe asking how they've been." if is_session_start else ""}
{"This is the END of the session - wrap up naturally, maybe preview next time or wish them well." if is_session_end else ""}

PERSONAL FACTS TO WORK IN NATURALLY (don't force them, let them emerge organically):
{chr(10).join(f"- {fact}" for fact in facts_to_reveal)}

{history_str}

CRITICAL GUIDELINES:
1. The student (Leo) speaks like a REAL 17-year-old:
   - Uses "like", "um", "kinda", "honestly", casual language
   - Sometimes interrupts themselves or changes direction mid-sentence
   - Shows genuine emotion (frustration, excitement, boredom)

2. Personal details should emerge NATURALLY:
   - NOT: "I have a dog named Barnaby who is a terrier"
   - YES: "Sorry I'm a bit tired, Barnaby kept me up barking at raccoons again"

3. The tutor (Adam) is warm and makes connections:
   - References things Leo has mentioned before
   - Connects math to Leo's interests when possible
   - Notices when Leo seems off and asks about it

4. Include substantive math content about {math_topic}

5. Generate 4-6 exchanges (8-12 lines total)

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
TUTOR: [what the tutor says]
STUDENT: [what the student says]
TUTOR: [next tutor response]
STUDENT: [next student response]
...

Generate the conversation segment now:"""

    def _parse_turns(self, text: str) -> List[Dict[str, str]]:
        """Parse LLM output into turn dictionaries."""
        turns = []
        current_turn = {}

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("TUTOR:"):
                if current_turn:
                    turns.append(current_turn)
                    current_turn = {}
                current_turn["tutor"] = line.replace("TUTOR:", "").strip()
            elif line.startswith("STUDENT:"):
                current_turn["student"] = line.replace("STUDENT:", "").strip()
                if "tutor" in current_turn:
                    turns.append(current_turn)
                    current_turn = {}

        if current_turn and "tutor" in current_turn:
            turns.append(current_turn)

        return turns

    def generate_all_sessions(self, num_sessions: int = 20, turns_per_session: int = 25):
        """Generate all sessions and save manifest."""
        print(f"\n{'='*60}")
        print(f"[GENERATOR] Generating {num_sessions} sessions for {self.persona['name']}")
        print(f"[GENERATOR] ~{turns_per_session} turns per session")
        print(f"[GENERATOR] Output: {self.session_output_dir}")
        print(f"{'='*60}")

        for session_num in range(1, num_sessions + 1):
            self.generate_session(
                session_number=session_num,
                turns_per_session=turns_per_session
            )

        # Save manifest
        manifest = {
            "persona": self.persona,
            "generated_at": datetime.utcnow().isoformat(),
            "total_sessions": len(self.all_sessions_metadata),
            "total_turns": sum(s["turn_count"] for s in self.all_sessions_metadata),
            "unique_facts_revealed": len(set(self.revealed_facts)),
            "sessions": self.all_sessions_metadata
        }

        manifest_path = self.session_output_dir / "_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Save persona copy
        persona_path = self.session_output_dir / "_persona.json"
        with open(persona_path, 'w', encoding='utf-8') as f:
            json.dump(self.persona, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"[GENERATOR] COMPLETE!")
        print(f"  Total sessions: {manifest['total_sessions']}")
        print(f"  Total turns: {manifest['total_turns']}")
        print(f"  Unique facts revealed: {manifest['unique_facts_revealed']}")
        print(f"  Output directory: {self.session_output_dir}")
        print(f"  Manifest: _manifest.json")
        print(f"{'='*60}\n")

        return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate tutoring conversations from persona")
    parser.add_argument("--persona", type=str, required=True, help="Path to persona JSON file")
    parser.add_argument("--output", type=str, default="simulated_sessions", help="Output directory")
    parser.add_argument("--sessions", type=int, default=20, help="Number of sessions to generate")
    parser.add_argument("--turns-per-session", type=int, default=25, help="Turns per session")
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    persona_path = script_dir / "test_personas" / args.persona if not Path(args.persona).is_absolute() else Path(args.persona)
    output_dir = script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)

    if not persona_path.exists():
        print(f"ERROR: Persona file not found: {persona_path}")
        sys.exit(1)

    print(f"[GENERATOR] Loading persona from: {persona_path}")

    generator = ConversationGenerator(str(persona_path), str(output_dir))
    generator.generate_all_sessions(
        num_sessions=args.sessions,
        turns_per_session=args.turns_per_session
    )


if __name__ == "__main__":
    main()
