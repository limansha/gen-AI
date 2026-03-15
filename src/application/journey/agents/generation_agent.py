import logging
import json
import re

from src.domain.entities.journey import Action
from src.domain.value_objects.journey_trait import JourneyTrait
from src.infrastructure.external.llm_client import LLMClient

logger = logging.getLogger(__name__)


class GenerationAgent:
    """Generates actions and traits for a journey"""

    @staticmethod
    async def generate_actions_and_traits(
        journey_summary: str,
        understanding: dict,
    ) -> tuple[list[Action], list[JourneyTrait]]:
        """
        Generate actions and traits for a journey.

        Args:
            journey_summary: The journey summary
            understanding: UnderstandingResult from UnderstandingAgent

        Returns:
            Tuple of (actions, traits)
        """
        actions_data = await GenerationAgent._generate_actions(
            journey_summary,
            understanding,
        )

        traits = await GenerationAgent._generate_traits(
            journey_summary,
            understanding,
        )

        actions = []
        for idx, action_data in enumerate(actions_data, start=1):
            action = Action.create(
                title=action_data["title"],
                duration=action_data.get("duration", "5 min"),
                steps=action_data.get("steps", []),
                order=idx,
            )
            actions.append(action)

        logger.info(f"Generated {len(actions)} actions and {len(traits)} traits")
        return actions, traits

    @staticmethod
    async def _generate_actions(
        journey_summary: str,
        understanding: dict,
    ) -> list[dict]:
        """
        Generate action list using LLM.

        Args:
            journey_summary: Journey summary
            understanding: Understanding result

        Returns:
            List of action dictionaries
        """
        system_prompt = """You are an expert personal development coach.
Create a structured list of actionable tasks that help someone achieve their goal.
Each action should have:
- A clear, motivating title
- Estimated duration (e.g., "3-5 min", "10 min", "15-20 min")
- 3-5 specific, actionable steps

Return a JSON array of actions:
[
  {
    "title": "Action Title",
    "duration": "3-5 min",
    "steps": [
      "Step 1 instruction",
      "Step 2 instruction",
      "Step 3 instruction"
    ]
  },
  ...
]

Generate 4-6 actions that progressively build toward the goal."""

        prompt = f"""Journey Goal: {understanding.get('goal', journey_summary)}
Context: {understanding.get('context', '')}
Target Outcome: {understanding.get('target_outcome', '')}

Create a structured action plan. Return only valid JSON array."""

        try:
            response = await LLMClient.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=3000,
            )

            content = response["content"].strip()
            
            array_match = re.search(r'\[[^\]]+\]', content, re.DOTALL)
            if array_match:
                content = array_match.group(0)

            actions = json.loads(content)

            if not isinstance(actions, list):
                logger.warning("LLM returned non-list for actions")
                return GenerationAgent._default_actions()

            validated_actions = []
            for action in actions:
                if isinstance(action, dict) and "title" in action:
                    validated_actions.append({
                        "title": action["title"],
                        "duration": action.get("duration", "5 min"),
                        "steps": action.get("steps", []),
                    })

            if not validated_actions:
                return GenerationAgent._default_actions()

            return validated_actions[:6]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM actions: {str(e)}")
            return GenerationAgent._default_actions()
        except Exception as e:
            logger.error(f"Action generation error: {str(e)}", exc_info=True)
            return GenerationAgent._default_actions()

    @staticmethod
    async def _generate_traits(
        journey_summary: str,
        understanding: dict,
    ) -> list[JourneyTrait]:
        """
        Generate traits for the journey.

        Args:
            journey_summary: Journey summary
            understanding: Understanding result

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
    {"name": "confidence_building", "confidence": 0.90}
  ]
}"""

        prompt = f"""Journey: {journey_summary}
Goal: {understanding.get('goal', '')}
Key Attributes: {', '.join(understanding.get('key_attributes', []))}

Extract 3-5 key traits. Return only valid JSON."""

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

            return traits[:5]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM traits: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Trait generation error: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def _default_actions() -> list[dict]:
        """Fallback actions when LLM generation fails"""
        return [
            {
                "title": "Set Your Intention",
                "duration": "5 min",
                "steps": [
                    "Write down your goal clearly",
                    "Identify why this goal matters to you",
                    "Visualize your success",
                ],
            },
            {
                "title": "Take the First Step",
                "duration": "10 min",
                "steps": [
                    "Identify one small action you can take today",
                    "Commit to doing it",
                    "Reflect on how it feels",
                ],
            },
        ]
