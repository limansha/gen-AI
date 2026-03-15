import logging
import json
import re
from typing import TypedDict

from src.infrastructure.external.llm_client import LLMClient

logger = logging.getLogger(__name__)


class UnderstandingResult(TypedDict):
    goal: str
    context: str
    key_attributes: list[str]
    target_outcome: str


class UnderstandingAgent:
    """Extracts user intent and needs from journey summary"""

    @staticmethod
    async def understand_user_need(journey_summary: str) -> UnderstandingResult:
        """
        Understand user's goal and needs from journey summary.

        Args:
            journey_summary: The journey summary text

        Returns:
            UnderstandingResult with structured understanding
        """
        system_prompt = """You are an expert at understanding personal development goals.
Analyze the user's journey description and extract:
1. The primary goal they want to achieve
2. The context/situation they're in
3. Key attributes or characteristics they want to develop
4. The target outcome they envision

Return a JSON object with this structure:
{
  "goal": "clear statement of the primary goal",
  "context": "description of their current situation or context",
  "key_attributes": ["attribute1", "attribute2", ...],
  "target_outcome": "what success looks like for them"
}"""

        prompt = f"""Analyze this journey description and extract the user's needs:
"{journey_summary}"

Return only valid JSON with the structure described."""

        try:
            response = await LLMClient.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
            )

            content = response["content"].strip()
            
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            parsed = json.loads(content)

            result: UnderstandingResult = {
                "goal": parsed.get("goal", ""),
                "context": parsed.get("context", ""),
                "key_attributes": parsed.get("key_attributes", []),
                "target_outcome": parsed.get("target_outcome", ""),
            }

            logger.info(f"Extracted understanding: goal={result['goal'][:50]}...")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM understanding: {str(e)}")
            return UnderstandingAgent._default_understanding(journey_summary)
        except Exception as e:
            logger.error(f"Understanding extraction error: {str(e)}", exc_info=True)
            return UnderstandingAgent._default_understanding(journey_summary)

    @staticmethod
    def _default_understanding(journey_summary: str) -> UnderstandingResult:
        """Fallback understanding when LLM parsing fails"""
        return {
            "goal": journey_summary[:200],
            "context": "User wants to improve themselves",
            "key_attributes": [],
            "target_outcome": "Achieve the stated goal",
        }
