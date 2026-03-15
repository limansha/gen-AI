import logging
import json
import re
from typing import TypedDict

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.domain.entities.journey import Journey
from src.domain.value_objects.journey_trait import JourneyTrait
from src.infrastructure.database.models import JourneyModel
from src.infrastructure.database.journey_repository import JourneyRepository
from src.infrastructure.external.llm_client import LLMClient

logger = logging.getLogger(__name__)


class TraitExtraction(TypedDict):
    traits: list[dict[str, float]]


class JourneyMatcherAgent:
    """Determines if journey exists in DB using semantic matching via LLM"""

    SIMILARITY_THRESHOLD = 0.7

    @staticmethod
    async def check_journey_exists(
        journey_summary: str,
        db: Session,
    ) -> tuple[bool, Journey | None]:
        """
        Check if a similar journey exists in the database.

        Args:
            journey_summary: The journey summary to match
            db: Database session

        Returns:
            Tuple of (exists, matched_template)
        """
        extracted_traits = await JourneyMatcherAgent._extract_traits(journey_summary)
        
        if not extracted_traits:
            logger.info("No traits extracted from journey summary")
            return False, None

        matched_template = await JourneyMatcherAgent._find_matching_template(
            extracted_traits,
            db,
        )

        exists = matched_template is not None
        return exists, matched_template

    @staticmethod
    async def _extract_traits(journey_summary: str) -> list[JourneyTrait]:
        """
        Extract traits from journey summary using LLM.

        Args:
            journey_summary: Journey summary text

        Returns:
            List of JourneyTrait objects
        """
        system_prompt = """You are a trait extraction system.
Extract key traits, characteristics, and themes from a journey description.
Return a JSON object with a "traits" array.
Each trait should have a "name" (string) and "confidence" (float 0.0-1.0).

Example:
{
  "traits": [
    {"name": "public_speaking", "confidence": 0.95},
    {"name": "confidence_building", "confidence": 0.90},
    {"name": "stress_management", "confidence": 0.85}
  ]
}"""

        prompt = f"""Extract traits from this journey description:
"{journey_summary}"

Return only valid JSON with the traits array."""

        try:
            response = await LLMClient.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
            )

            content = response["content"].strip()
            
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            parsed = json.loads(content)
            traits_data = parsed.get("traits", [])

            traits = [
                JourneyTrait(
                    name=trait["name"],
                    confidence=float(trait["confidence"]),
                )
                for trait in traits_data
                if "name" in trait and "confidence" in trait
            ]

            logger.info(f"Extracted {len(traits)} traits from journey summary")
            return traits

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM trait extraction: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Trait extraction error: {str(e)}", exc_info=True)
            return []

    @staticmethod
    async def _find_matching_template(
        extracted_traits: list[JourneyTrait],
        db: Session,
    ) -> Journey | None:
        """
        Find matching journey based on trait similarity.

        Args:
            extracted_traits: Traits extracted from journey summary
            db: Database session

        Returns:
            Matched Journey or None
        """
        if not extracted_traits:
            return None

        trait_names = [trait.name.lower() for trait in extracted_traits]

        stmt = select(JourneyModel)
        all_journeys = db.scalars(stmt).all()

        if not all_journeys:
            logger.info("No journeys found in database")
            return None

        best_match = None
        best_score = 0.0

        for journey_model in all_journeys:
            journey_traits_dict = {
                trait["name"].lower(): float(trait["confidence"])
                for trait in journey_model.journey_traits
            }

            match_score = JourneyMatcherAgent._calculate_similarity(
                extracted_traits,
                journey_traits_dict,
            )

            if match_score > best_score and match_score >= JourneyMatcherAgent.SIMILARITY_THRESHOLD:
                best_score = match_score
                best_match = journey_model

        if best_match:
            logger.info(f"Found matching journey with similarity score: {best_score:.2f}")
            return JourneyRepository._model_to_entity(best_match)

        return None

    @staticmethod
    def _calculate_similarity(
        extracted_traits: list[JourneyTrait],
        template_traits: dict[str, float],
    ) -> float:
        """
        Calculate similarity score between extracted traits and template traits.

        Args:
            extracted_traits: Traits from journey summary
            template_traits: Traits from database template

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not extracted_traits or not template_traits:
            return 0.0

        matches = 0
        total_confidence = 0.0

        for trait in extracted_traits:
            trait_name_lower = trait.name.lower()
            if trait_name_lower in template_traits:
                matches += 1
                template_confidence = template_traits[trait_name_lower]
                total_confidence += (trait.confidence + template_confidence) / 2.0

        if matches == 0:
            return 0.0

        base_score = matches / max(len(extracted_traits), len(template_traits))
        confidence_bonus = total_confidence / matches if matches > 0 else 0.0

        return (base_score * 0.6) + (confidence_bonus * 0.4)

