"""
Historical Context Provider

Surfaces past context from Vector DB and Knowledge Graph to enhance Adam's responses.
Provides historical struggles, prerequisite gaps, and learning patterns.
"""

import logging
from enum import Enum
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from memory.vector_store import VectorStore
from memory.knowledge_graph import KnowledgeGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of historical context"""
    PAST_STRUGGLE = "past_struggle"
    PAST_SUCCESS = "past_success"
    PREREQUISITE_GAP = "prerequisite_gap"


@dataclass
class ContextResult:
    """A piece of historical context"""
    context_type: ContextType
    content: str
    relevance_score: float
    metadata: Optional[Dict] = None

    def to_string(self) -> str:
        """Convert to human-readable string"""
        type_label = self.context_type.value.replace("_", " ").title()
        return f"[{type_label}] {self.content} (relevance: {self.relevance_score:.2f})"


class ContextProvider:
    """
    Historical Context Provider

    Retrieves and provides historical context to Adam:
    1. Past struggles/successes from Vector DB
    2. Prerequisite gaps from Knowledge Graph
    3. Learning patterns and trends

    This context is injected to Adam BEFORE his response, enabling
    him to provide more informed, personalized teaching.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        prompt_injection_callback: Optional[Callable] = None
    ):
        """
        Initialize Context Provider

        Args:
            vector_store: Vector database for semantic search
            knowledge_graph: Knowledge graph for prerequisite tracking
            prompt_injection_callback: Async function to inject context to Gemini
        """
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.prompt_injection_callback = prompt_injection_callback

        logger.info("Context Provider initialized")

    async def get_past_struggles(
        self,
        topic: str,
        student_id: str,
        k: int = 3
    ) -> List[ContextResult]:
        """
        Get past struggles for a topic from Vector DB

        Args:
            topic: Topic to search for
            student_id: Student identifier
            k: Number of results to retrieve

        Returns:
            List of past struggles as ContextResult objects
        """
        if not self.vector_store:
            logger.warning("No vector store available for past struggles")
            return []

        # Search for similar past interactions
        query = f"Student struggling with {topic}"
        filter_metadata = {
            "student_id": student_id
        }

        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter_metadata=filter_metadata
            )

            # Convert to ContextResult
            context_results = []
            for result in results:
                # Calculate relevance score (lower distance = higher relevance)
                distance = result.get('distance', 1.0)
                relevance_score = max(0.0, 1.0 - distance)

                context_results.append(ContextResult(
                    context_type=ContextType.PAST_STRUGGLE,
                    content=result['text'],
                    relevance_score=relevance_score,
                    metadata=result.get('metadata', {})
                ))

            logger.info(f"Found {len(context_results)} past struggles for topic: {topic}")
            return context_results

        except Exception as e:
            logger.error(f"Error retrieving past struggles: {e}")
            return []

    async def get_prerequisite_gaps(
        self,
        current_skill: str,
        student_id: str,
        student_skills: Dict[str, float],
        threshold: float = 0.5
    ) -> List[ContextResult]:
        """
        Get prerequisite gaps from Knowledge Graph

        Args:
            current_skill: Current skill being learned
            student_id: Student identifier
            student_skills: Dict mapping skill_id -> mastery level (0-1)
            threshold: Minimum mastery threshold

        Returns:
            List of prerequisite gaps as ContextResult objects
        """
        if not self.knowledge_graph:
            logger.warning("No knowledge graph available for prerequisite gaps")
            return []

        try:
            # Find gaps in prerequisites
            gaps = self.knowledge_graph.find_prerequisite_gaps(
                current_skill=current_skill,
                student_skills=student_skills,
                threshold=threshold
            )

            # Convert to ContextResult
            context_results = []
            for gap in gaps:
                skill_id = gap.get('skill_id', 'unknown')
                current_mastery = gap.get('current_mastery', 0.0)
                gap_size = gap.get('gap', 0.0)

                content = (
                    f"Student has incomplete mastery of prerequisite '{skill_id}' "
                    f"(current: {current_mastery:.0%}, needed: {threshold:.0%})"
                )

                # Relevance based on gap size (larger gap = more relevant)
                relevance_score = min(1.0, gap_size * 2)  # Scale gap to 0-1

                context_results.append(ContextResult(
                    context_type=ContextType.PREREQUISITE_GAP,
                    content=content,
                    relevance_score=relevance_score,
                    metadata=gap
                ))

            logger.info(f"Found {len(context_results)} prerequisite gaps for skill: {current_skill}")
            return context_results

        except Exception as e:
            logger.error(f"Error retrieving prerequisite gaps: {e}")
            return []

    async def inject_context_to_adam(self, context: List[ContextResult]):
        """
        Inject historical context to Adam via prompt

        Args:
            context: List of context items to inject
        """
        if not context or len(context) == 0:
            logger.debug("No context to inject")
            return

        if not self.prompt_injection_callback:
            logger.warning("No prompt injection callback set")
            return

        # Format context as prompt
        context_parts = ["[Historical Context]"]

        for item in context:
            context_parts.append(f"- {item.content}")

        context_parts.append(
            "\nPlease consider this context when responding to the student. "
            "Tailor your teaching approach based on their history and gaps."
        )

        context_prompt = "\n".join(context_parts)

        # Inject to Adam
        await self.prompt_injection_callback(context_prompt)
        logger.info(f"Injected {len(context)} context items to Adam")

    async def provide_context(
        self,
        topic: Optional[str] = None,
        current_skill: Optional[str] = None,
        student_id: Optional[str] = None,
        student_skills: Optional[Dict[str, float]] = None
    ):
        """
        Convenience method: retrieve and inject all relevant context

        This is the main workflow for context provision:
        1. Get past struggles from Vector DB
        2. Get prerequisite gaps from Knowledge Graph
        3. Inject combined context to Adam

        Args:
            topic: Topic being studied
            current_skill: Current skill being learned
            student_id: Student identifier
            student_skills: Student's skill mastery levels
        """
        all_context = []

        # Retrieve past struggles if topic provided
        if topic and student_id:
            struggles = await self.get_past_struggles(topic, student_id)
            all_context.extend(struggles)

        # Retrieve prerequisite gaps if skill provided
        if current_skill and student_id and student_skills:
            gaps = await self.get_prerequisite_gaps(
                current_skill,
                student_id,
                student_skills
            )
            all_context.extend(gaps)

        # Inject all context
        if all_context:
            await self.inject_context_to_adam(all_context)
            logger.info(f"Provided {len(all_context)} total context items")
        else:
            logger.debug("No context to provide")
