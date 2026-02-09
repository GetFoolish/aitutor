from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ..core.context import SessionContext


class Skill(ABC):
    def __init__(self, name: str):
        self.name = name
        self.state: Dict[str, Any] = {}

    @abstractmethod
    def should_run(self, context: SessionContext) -> bool:
        pass

    @abstractmethod
    def execute(self, context: SessionContext) -> Optional[str]:
        pass

