import logging
import importlib
import inspect
from pathlib import Path
from typing import List, Optional
from .core.context import SessionContext
from .skills.base import Skill

logger = logging.getLogger(__name__)


class SkillsManager:
    def __init__(self, skills_dir: Optional[str] = None, config = None):
        self.skills: List[Skill] = []
        self.skill_states = {}
        self.config = config
        
        # Auto-load skills if directory provided
        if skills_dir:
            self._load_skills_from_directory(Path(skills_dir))
    
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
                        # Instantiate with config if available
                        if self.config:
                            skill_instance = obj(self.config)
                        else:
                            skill_instance = obj()
                        
                        self.register_skill(skill_instance)
                        logger.info(f"[SKILLS_MANAGER] Loaded skill: {skill_instance.name}")
            
            except Exception as e:
                logger.error(f"[SKILLS_MANAGER] Failed to load skill from {file.name}: {e}")

    def register_skill(self, skill: Skill):
        self.skills.append(skill)
        self.skill_states[skill.name] = {}

    def execute_skills(self, context: SessionContext) -> List[str]:
        injections = []
        for skill in self.skills:
            if skill.should_run(context):
                try:
                    result = skill.execute(context)
                    if result:
                        injections.append(result)
                except Exception as e:
                    logger.error(f"Skill {skill.name} failed: {e}")
        return injections

