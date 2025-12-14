import logging
from typing import List
from .core.context import SessionContext
from .skills.base import Skill

logger = logging.getLogger(__name__)


class SkillsManager:
    def __init__(self):
        self.skills: List[Skill] = []
        self.skill_states = {}

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

