from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from config.settings import app_cfg
from utils.utils import get_termination_conditions

from models.GoogleModel import model_client
from agents.planner import build_planner
from agents.researcher import build_researcher
from agents.writer import build_writer
from agents.validator import build_validator

async def build_validated_pair(producer, validator_name: str, max_messages: int = 2):
    """
    Creates a Producer->Validator sub-team that terminates after max_messages.
    """
    validator = build_validator()
    inner_termination = MaxMessageTermination(max_messages=max_messages)
    pair_team = RoundRobinGroupChat(
        participants=[producer, validator],
        termination_condition=inner_termination,
        name=f"{producer.name}_validation_loop",
        description=f"Validate outputs of {producer.name} before proceeding.",
    )
    return pair_team

async def build_travel_team():
    # 1. Build the primary agents
    researcher = await build_researcher(model_client)
    planner = await build_planner(model_client)
    writer = await build_writer(model_client)

    # 2. Create validation sub-teams ONLY for JSON producers
    researcher_chain = await build_validated_pair(researcher, "validator_after_researcher")
    planner_chain = await build_validated_pair(planner, "validator_after_planner")

    # 3. The main team uses the sub-teams and the final writer agent directly
    team = RoundRobinGroupChat(
        participants=[
            researcher_chain,  # Step 1: Research + Validation
            planner_chain,     # Step 2: Plan + Validation
            writer,            # Step 3: Final Write-up (no validation needed)
        ],
        name="travel_team",
        description="Validated travel planning workflow with nested producer->validator loops.",
        max_turns=app_cfg.MAX_TURNS,
        termination_condition=get_termination_conditions(),
    )
    return team