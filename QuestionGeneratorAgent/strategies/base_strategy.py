"""
Base Strategy Interface for Question Generation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import logger
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class GenerationResult:
    """Result of a question generation attempt."""
    success: bool
    question: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    generation_cost: Optional[float] = None
    tokens_used: Optional[Dict[str, int]] = None
    cost_breakdown: Optional[Dict[str, float]] = None
    source_question_id: Optional[str] = None
    generated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "success": self.success,
            "question": self.question,
            "error_message": self.error_message,
            "generation_cost": self.generation_cost,
            "tokens_used": self.tokens_used,
            "cost_breakdown": self.cost_breakdown,
            "source_question_id": self.source_question_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None
        }

    def __post_init__(self):
        """Log result creation."""
        if self.success:
            logger.debug("GenerationResult created", success=True, source=self.source_question_id)
        else:
            logger.debug("GenerationResult created", success=False, error=self.error_message)


class BaseGenerationStrategy(ABC):
    """
    Abstract base class for question generation strategies.
    """

    def __init__(self, llm_client=None, config: Optional[Dict[str, Any]] = None):
        self.llm_client = llm_client
        self.config = config or {}
        logger.info(f"Strategy initialized: {self.__class__.__name__}", 
                   has_llm_client=llm_client is not None,
                   config_keys=list(self.config.keys()) if self.config else [])

    @abstractmethod
    def generate(self, source_question: Dict[str, Any]) -> GenerationResult:
        pass

    @abstractmethod
    def validate(self, generated_question: Dict[str, Any]) -> Tuple[bool, str]:
        pass

    def get_strategy_name(self) -> str:
        return self.__class__.__name__

    def supports_question_type(self, question: Dict[str, Any]) -> bool:
        return True

    def _extract_widgets(self, question: Dict[str, Any]) -> Dict[str, Any]:
        widgets = question.get("question", {}).get("widgets", {})
        logger.debug(f"Extracted {len(widgets)} widgets")
        return widgets

    def _extract_content(self, question: Dict[str, Any]) -> str:
        content = question.get("question", {}).get("content", "")
        logger.debug(f"Extracted content: {len(content)} chars")
        return content

    def _get_answer_widgets(self, question: Dict[str, Any]) -> Dict[str, Any]:
        widgets = self._extract_widgets(question)
        answer_types = ["numeric-input", "radio", "dropdown", "expression", "input-number"]
        answer_widgets = {k: v for k, v in widgets.items() if v.get("type") in answer_types}
        logger.debug(f"Found {len(answer_widgets)} answer widgets", 
                    types=[w.get("type") for w in answer_widgets.values()])
        return answer_widgets

    def _get_correct_answers(self, question: Dict[str, Any]) -> Dict[str, Any]:
        answer_widgets = self._get_answer_widgets(question)
        answers = {}
        for widget_name, widget_data in answer_widgets.items():
            widget_type = widget_data.get("type")
            options = widget_data.get("options", {})
            if widget_type == "numeric-input":
                answer_list = options.get("answers", [])
                for ans in answer_list:
                    if ans.get("status") == "correct":
                        answers[widget_name] = ans.get("value")
                        logger.debug(f"Found numeric answer", widget=widget_name, value=ans.get("value"))
                        break
            elif widget_type == "radio":
                choices = options.get("choices", [])
                for i, choice in enumerate(choices):
                    if choice.get("correct"):
                        answers[widget_name] = {"index": i, "content": choice.get("content", "")}
                        logger.debug(f"Found radio answer", widget=widget_name, index=i)
                        break
            elif widget_type == "dropdown":
                choices = options.get("choices", [])
                for i, choice in enumerate(choices):
                    if choice.get("correct"):
                        answers[widget_name] = {"index": i, "content": choice.get("content", "")}
                        logger.debug(f"Found dropdown answer", widget=widget_name, index=i)
                        break
        logger.info(f"Extracted {len(answers)} correct answers from question")
        return answers
