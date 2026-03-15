import logging
import re

from src.infrastructure.external.llm_client import LLMClient

logger = logging.getLogger(__name__)


class GuardrailsAgent:
    """Validates and sanitizes journey input using LLM and rule-based checks"""

    MAX_LENGTH = 1000
    MIN_LENGTH = 10
    FORBIDDEN_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
    ]

    @staticmethod
    async def validate_journey(journey_summary: str) -> tuple[bool, str]:
        """
        Validates and sanitizes journey summary.

        Args:
            journey_summary: Raw journey summary input

        Returns:
            Tuple of (is_valid, sanitized_summary)
        """
        if not journey_summary or not isinstance(journey_summary, str):
            logger.warning("Empty or invalid journey summary provided")
            return False, ""

        sanitized = journey_summary.strip()

        if len(sanitized) < GuardrailsAgent.MIN_LENGTH:
            logger.warning(f"Journey summary too short: {len(sanitized)} chars")
            return False, ""

        if len(sanitized) > GuardrailsAgent.MAX_LENGTH:
            sanitized = sanitized[:GuardrailsAgent.MAX_LENGTH]
            logger.info(f"Journey summary truncated to {GuardrailsAgent.MAX_LENGTH} chars")

        for pattern in GuardrailsAgent.FORBIDDEN_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"Journey summary contains forbidden pattern: {pattern}")
                return False, ""

        llm_validated = await GuardrailsAgent._llm_validation(sanitized)
        if not llm_validated:
            logger.warning("Journey summary failed LLM validation")
            return False, ""

        return True, sanitized

    @staticmethod
    async def _llm_validation(journey_summary: str) -> bool:
        """
        Use LLM to validate journey summary appropriateness.

        Args:
            journey_summary: Sanitized journey summary

        Returns:
            True if valid, False otherwise
        """
        system_prompt = """You are a content moderation system. 
Evaluate if the user's journey goal is appropriate, constructive, and safe.
Return only "VALID" or "INVALID" followed by a brief reason.

Consider:
- Is it a legitimate personal development goal?
- Does it contain harmful, illegal, or inappropriate content?
- Is it clear and meaningful?"""

        prompt = f"""Journey summary to validate:
"{journey_summary}"

Respond with only "VALID" or "INVALID" followed by a brief reason."""

        try:
            response = await LLMClient.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
            )

            result = response["content"].strip().upper()
            is_valid = result.startswith("VALID")

            if not is_valid:
                logger.info(f"LLM validation failed: {response['content']}")

            return is_valid
        except Exception as e:
            logger.error(f"LLM validation error: {str(e)}", exc_info=True)
            return False
