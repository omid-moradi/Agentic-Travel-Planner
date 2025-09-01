"""
Assembles the advanced travel planning team using a SelectorGroupChat.

This module defines the final team structure, orchestrating the agents
(researcher, planner, writer, validator) using a custom, code-based
selector function to ensure a robust and predictable workflow.
"""
from typing import Sequence, Optional

from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.messages import BaseChatMessage

# Import agent and client builders
from models.GoogleModel import model_client
from agents.planner import build_planner
from agents.researcher import build_researcher
from agents.writer import build_writer
from agents.validator import build_validator
from utils.utils import get_termination_conditions

# --- Helper Functions for the Selector ---
def _last_source(history: Sequence[BaseChatMessage]) -> str:
    """
    Safely retrieves the source (sender name) of the last message in the chat history.

    Args:
        history: The sequence of messages from the chat.

    Returns:
        The name of the last speaker, or an empty string if the history is empty.
    """
    return getattr(history[-1], "source", "") if history else ""

def _validation_state(msg: BaseChatMessage) -> Optional[str]:
    """
    Parses a validator's message content to determine the validation outcome.

    Args:
        msg: The message object from the validator agent.

    Returns:
        'success', 'failure', 'skipped', or None if the state cannot be determined.
    """
    content = (getattr(msg, "content", "") or "")
    if "VALIDATION_SUCCESS" in content:
        return "success"
    if "VALIDATION_FAILURE" in content:
        return "failure"
    if "VALIDATION_SKIPPED" in content:
        return "skipped"
    return None

# --- Core Selection Logic ---
async def selector_func(messages: Sequence[BaseChatMessage]) -> Optional[str]:
    """
    The main traffic controller for the group chat.

    This function is called after every message and decides which agent should speak next.
    It implements a deterministic workflow:
    1. Researcher produces a report.
    2. Validator checks the report.
    3. Planner produces an itinerary.
    4. Validator checks the itinerary.
    5. Writer produces the final text.
    It also includes a self-correction loop if validation fails.
    """
    # Rule: If the chat has just begun, the researcher starts the process.
    if not messages or len(messages) <= 1:
        return "researcher"
    
    last = messages[-1]
    src = _last_source(messages)

    # Rule: After the user speaks, the researcher always begins the workflow.
    if src == "user":
        return "researcher"

    # Rule: After the researcher produces its report, the validator must check it.
    if src == "researcher":
        return "validator"

    # Rule: After the planner produces its itinerary, the validator must check it.
    if src == "planner":
        return "validator"

    # Rule: After the validator speaks, decide the next step based on the outcome.
    if src == "validator":
        state = _validation_state(last)
        content = last.content or ""

        # Check what was being validated by looking for keywords in the validator's message.
        if "ResearchReport" in content:
            # If the research report was validated successfully, move to the planner.
            # Otherwise, send it back to the researcher for correction.
            return "planner" if state == "success" else "researcher"
        
        if "ItineraryPlan" in content:
            # If the itinerary was validated successfully, move to the writer.
            # Otherwise, send it back to the planner for correction.
            return "writer" if state == "success" else "planner"
        
        # Fallback if the validator's message is unclear.
        return "researcher"

    # Rule: After the writer has produced the final output, the conversation is over.
    if src == "writer":
        return None # Returning None is a valid way to terminate the chat.

    # Default fallback to the researcher if the state is unknown.
    return "researcher"

# --- Team Factory ---
async def build_travel_team():
    """
    Builds and configures the complete, selector-driven travel planning team.

    This function assembles all the specialized agents and orchestrates them
    within a SelectorGroupChat controlled by our custom `selector_func`.

    Returns:
        An instance of SelectorGroupChat ready to process tasks.
    """
    # 1. Build all the specialized agents.
    researcher = await build_researcher(model_client) 
    planner = await build_planner(model_client)        
    writer = await build_writer(model_client)       
    validator = build_validator()                   

    # 2. Configure the SelectorGroupChat.
    team = SelectorGroupChat(
        participants=[researcher, validator, planner, writer],
        selector_func=selector_func,
        model_client=model_client,
        allow_repeated_speaker=True, # Essential for the self-correction loop.
        termination_condition=get_termination_conditions(),
        name="travel_team_selector",
        description="A flat travel planning team with a code-based validation workflow.",
    )
    return team