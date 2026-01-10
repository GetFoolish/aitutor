"""
Skills Manager - Dynamic skill loading and execution
Based on v4 teaching-assistant branch implementation

Manages:
- Dynamic skill loading from directory
- Skill registration and execution
- Skill state management
"""

import logging
import importlib
import inspect
from pathlib import Path
from typing import List, Optional, Type, Dict, Any

from .core.context import SessionContext
from .core.config import TeachingAssistantConfig
from .skills.base import Skill, DEFAULT_SKILLS

logger = logging.getLogger(__name__)


class SkillsManager:
    """
    Manages skill registration, loading, and execution.

    Features:
    - Dynamic loading from skills directory
    - Priority-based execution order
    - Skill state management
    - Default skill loading
    """

    def __init__(
        self,
        skills_dir: Optional[str] = None,
        config: Optional[TeachingAssistantConfig] = None,
        load_defaults: bool = True
    ):
        self.skills: List[Skill] = []
        self.skill_states: Dict[str, Dict[str, Any]] = {}
        self.config = config or TeachingAssistantConfig()

        # Load default skills
        if load_defaults:
            self._load_default_skills()

        # Auto-load skills from directory if provided
        if skills_dir:
            self._load_skills_from_directory(Path(skills_dir))

        logger.info(f"[SKILLS_MANAGER] Initialized with {len(self.skills)} skills")

    def _load_default_skills(self):
        """Load default built-in skills"""
        for skill_class in DEFAULT_SKILLS:
            try:
                skill_instance = skill_class(self.config)
                self.register_skill(skill_instance)
                logger.debug(f"[SKILLS_MANAGER] Loaded default skill: {skill_instance.name}")
            except Exception as e:
                logger.error(f"[SKILLS_MANAGER] Failed to load default skill: {e}")

    def _load_skills_from_directory(self, skills_dir: Path):
        """Dynamically load all skill modules from directory"""
        logger.info(f"[SKILLS_MANAGER] Loading skills from {skills_dir}")

        if not skills_dir.exists():
            logger.warning(f"[SKILLS_MANAGER] Skills directory does not exist: {skills_dir}")
            return

        for file in skills_dir.glob("*.py"):
            if file.name.startswith("_") or file.name == "base.py":
                continue

            try:
                # Import module
                module_name = f"services.TeachingAssistant.skills.{file.stem}"
                module = importlib.import_module(module_name)

                # Find Skill subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Skill) and obj != Skill:
                        # Instantiate with config
                        skill_instance = obj(self.config)
                        self.register_skill(skill_instance)
                        logger.info(f"[SKILLS_MANAGER] Loaded skill: {skill_instance.name}")

            except Exception as e:
                logger.error(f"[SKILLS_MANAGER] Failed to load skill from {file.name}: {e}")

    def register_skill(self, skill: Skill):
        """
        Register a skill with the manager.

        Args:
            skill: Skill instance to register
        """
        # Check for duplicate names
        for existing in self.skills:
            if existing.name == skill.name:
                logger.warning(f"[SKILLS_MANAGER] Replacing existing skill: {skill.name}")
                self.skills.remove(existing)
                break

        self.skills.append(skill)
        self.skill_states[skill.name] = {}

        # Sort by priority (higher first)
        self.skills.sort(key=lambda s: -s.priority)

    def unregister_skill(self, skill_name: str) -> bool:
        """
        Unregister a skill by name.

        Args:
            skill_name: Name of skill to remove

        Returns:
            True if skill was found and removed
        """
        for skill in self.skills:
            if skill.name == skill_name:
                self.skills.remove(skill)
                if skill_name in self.skill_states:
                    del self.skill_states[skill_name]
                logger.info(f"[SKILLS_MANAGER] Unregistered skill: {skill_name}")
                return True
        return False

    def execute_skills(self, context: SessionContext) -> List[str]:
        """
        Execute all applicable skills and collect injections.

        Args:
            context: Current session context

        Returns:
            List of instruction injections from skills
        """
        injections = []

        for skill in self.skills:
            if not skill.enabled:
                continue

            try:
                if skill.should_run(context):
                    logger.debug(f"[SKILLS_MANAGER] Executing skill: {skill.name}")
                    result = skill.execute(context)
                    if result:
                        injections.append(result)
                        logger.info(f"[SKILLS_MANAGER] Skill {skill.name} generated injection")
            except Exception as e:
                logger.error(f"[SKILLS_MANAGER] Skill {skill.name} failed: {e}")

        if injections:
            logger.info(f"[SKILLS_MANAGER] Generated {len(injections)} injections from skills")

        return injections

    def execute_single_skill(
        self,
        skill_name: str,
        context: SessionContext
    ) -> Optional[str]:
        """
        Execute a specific skill by name.

        Args:
            skill_name: Name of skill to execute
            context: Current session context

        Returns:
            Injection string or None
        """
        for skill in self.skills:
            if skill.name == skill_name:
                try:
                    if skill.should_run(context):
                        return skill.execute(context)
                except Exception as e:
                    logger.error(f"[SKILLS_MANAGER] Skill {skill_name} failed: {e}")
                return None
        return None

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Get a skill by name"""
        for skill in self.skills:
            if skill.name == skill_name:
                return skill
        return None

    def get_skill_names(self) -> List[str]:
        """Get list of registered skill names"""
        return [skill.name for skill in self.skills]

    def enable_skill(self, skill_name: str) -> bool:
        """Enable a skill by name"""
        skill = self.get_skill(skill_name)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable_skill(self, skill_name: str) -> bool:
        """Disable a skill by name"""
        skill = self.get_skill(skill_name)
        if skill:
            skill.enabled = False
            return True
        return False

    def get_state(self, skill_name: str) -> Dict[str, Any]:
        """Get state for a skill"""
        return self.skill_states.get(skill_name, {})

    def set_state(self, skill_name: str, key: str, value: Any):
        """Set state for a skill"""
        if skill_name not in self.skill_states:
            self.skill_states[skill_name] = {}
        self.skill_states[skill_name][key] = value

    def clear_all_states(self):
        """Clear all skill states"""
        self.skill_states = {skill.name: {} for skill in self.skills}

    def get_info(self) -> Dict[str, Any]:
        """Get information about registered skills"""
        return {
            "skill_count": len(self.skills),
            "skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "priority": skill.priority,
                    "enabled": skill.enabled
                }
                for skill in self.skills
            ]
        }


# Singleton instance with default skills
skills_manager = SkillsManager(load_defaults=True)
