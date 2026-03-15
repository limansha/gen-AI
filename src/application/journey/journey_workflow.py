import logging
from typing import TypedDict, Annotated
from uuid import UUID, uuid4

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

from src.domain.entities.journey import Action, Journey
from src.domain.value_objects.journey_trait import JourneyTrait
from src.application.journey.agents.guardrails_agent import GuardrailsAgent
from src.application.journey.agents.journey_matcher_agent import JourneyMatcherAgent
from src.application.journey.agents.understanding_agent import UnderstandingAgent
from src.application.journey.agents.generation_agent import GenerationAgent
from src.infrastructure.database.journey_repository import JourneyRepository

logger = logging.getLogger(__name__)


class JourneyWorkflowState(TypedDict):
    journey_summary: str
    sanitized_summary: str
    journey_exists: bool
    matched_journey: Journey | None
    understanding: dict | None
    actions: Annotated[list[Action], "actions"]
    traits: Annotated[list[JourneyTrait], "traits"]
    db_session: Session
    error: str | None


class JourneyWorkflow:
    """LangGraph workflow for journey processing"""

    def __init__(self):
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.checkpointer)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph"""
        workflow = StateGraph(JourneyWorkflowState)

        workflow.add_node("guardrails", self._guardrails_node)
        workflow.add_node("check_db", self._check_db_node)
        workflow.add_node("understand", self._understand_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("save_db", self._save_db_node)
        workflow.add_node("retrieve_db", self._retrieve_db_node)
        workflow.add_node("format_response", self._format_response_node)

        workflow.set_entry_point("guardrails")
        workflow.add_edge("guardrails", "check_db")

        workflow.add_conditional_edges(
            "check_db",
            self._route_after_check,
            {
                "exists": "retrieve_db",
                "not_exists": "understand",
                "error": END,
            },
        )

        workflow.add_edge("understand", "generate")
        workflow.add_edge("generate", "save_db")
        workflow.add_edge("save_db", "format_response")
        workflow.add_edge("retrieve_db", "format_response")
        workflow.add_edge("format_response", END)

        return workflow

    async def _guardrails_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Apply guardrails to journey input"""
        try:
            is_valid, sanitized = await GuardrailsAgent.validate_journey(
                state["journey_summary"]
            )
            if not is_valid:
                state["error"] = "Journey summary failed guardrails validation"
                return state
            state["sanitized_summary"] = sanitized
            logger.info("Guardrails validation passed")
            return state
        except Exception as e:
            logger.error(f"Guardrails node error: {str(e)}", exc_info=True)
            state["error"] = f"Guardrails validation failed: {str(e)}"
            return state

    async def _check_db_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Check if journey exists in DB"""
        try:
            if state.get("error"):
                return state

            exists, template = await JourneyMatcherAgent.check_journey_exists(
                state["sanitized_summary"],
                state["db_session"],
            )
            state["journey_exists"] = exists
            state["matched_journey"] = template
            logger.info(f"DB check completed: exists={exists}")
            return state
        except Exception as e:
            logger.error(f"DB check node error: {str(e)}", exc_info=True)
            state["error"] = f"Database check failed: {str(e)}"
            return state

    def _route_after_check(self, state: JourneyWorkflowState) -> str:
        """Route based on DB check result"""
        if state.get("error"):
            return "error"
        return "exists" if state["journey_exists"] else "not_exists"

    async def _understand_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Understand user needs"""
        try:
            if state.get("error"):
                return state

            understanding = await UnderstandingAgent.understand_user_need(
                state["sanitized_summary"]
            )
            state["understanding"] = understanding
            logger.info("User understanding extracted")
            return state
        except Exception as e:
            logger.error(f"Understanding node error: {str(e)}", exc_info=True)
            state["error"] = f"Understanding extraction failed: {str(e)}"
            return state

    async def _generate_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Generate actions and traits"""
        try:
            if state.get("error"):
                return state

            actions, traits = await GenerationAgent.generate_actions_and_traits(
                state["sanitized_summary"],
                state["understanding"] or {},
            )
            state["actions"] = actions
            state["traits"] = traits
            logger.info(f"Generated {len(actions)} actions and {len(traits)} traits")
            return state
        except Exception as e:
            logger.error(f"Generation node error: {str(e)}", exc_info=True)
            state["error"] = f"Action generation failed: {str(e)}"
            return state

    async def _save_db_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Save generated journey to DB"""
        try:
            if state.get("error"):
                return state

            saved_journey = JourneyRepository.save_journey(
                db=state["db_session"],
                summary=state["sanitized_summary"],
                traits=state["traits"],
                actions=state["actions"],
            )
            logger.info(f"Saved journey: {saved_journey.id}")
            return state
        except Exception as e:
            logger.error(f"Save DB node error: {str(e)}", exc_info=True)
            state["error"] = f"Failed to save journey: {str(e)}"
            return state

    async def _retrieve_db_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Retrieve existing journey from DB"""
        try:
            if state.get("error"):
                return state

            journey = state["matched_journey"]
            if journey:
                state["actions"] = journey.actions
                state["traits"] = journey.traits
                logger.info(f"Retrieved {len(journey.actions)} actions from DB")
            return state
        except Exception as e:
            logger.error(f"Retrieve DB node error: {str(e)}", exc_info=True)
            state["error"] = f"Failed to retrieve journey: {str(e)}"
            return state

    async def _format_response_node(
        self, state: JourneyWorkflowState
    ) -> JourneyWorkflowState:
        """Format final response"""
        if state.get("error"):
            logger.warning(f"Workflow ended with error: {state['error']}")
        else:
            logger.info(f"Workflow completed successfully with {len(state['actions'])} actions")
        return state

    async def execute(
        self,
        journey_summary: str,
        db_session: Session,
    ) -> list[Action]:
        """
        Execute the workflow.

        Args:
            journey_summary: The journey summary input
            db_session: Database session

        Returns:
            List of Action entities

        Raises:
            ValueError: If workflow execution fails
        """
        initial_state: JourneyWorkflowState = {
            "journey_summary": journey_summary,
            "sanitized_summary": "",
            "journey_exists": False,
            "matched_journey": None,
            "understanding": None,
            "actions": [],
            "traits": [],
            "db_session": db_session,
            "error": None,
        }

        config = {"configurable": {"thread_id": str(uuid4())}}
        
        try:
            final_state = await self.app.ainvoke(initial_state, config)
            
            if final_state.get("error"):
                raise ValueError(final_state["error"])
            
            if not final_state.get("actions"):
                raise ValueError("No actions generated")
            
            return final_state["actions"]
        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}", exc_info=True)
            raise
