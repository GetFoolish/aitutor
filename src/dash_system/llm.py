from typing import List
import json

class LLMClientProtocol:
    def complete(self, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


def generate_tags_for_question(llm_client: LLMClientProtocol, question_content: str) -> List[str]:
    prompt = (
        "You are a curriculum tagging expert for a K-12 math platform. "
        "Based on the following question content, generate a JSON array of 3-5 relevant, searchable tags. "
        "Tags should be lowercase and hyphenated if multiple words.\n\n"
        f"Question: \"{question_content}\"\n\nOutput:"
    )
    try:
        response_text = llm_client.complete(prompt)
        tags = json.loads(response_text)
        if isinstance(tags, list):
            tags = [str(t).strip().lower() for t in tags]
            return tags
        return []
    except Exception:
        return []
