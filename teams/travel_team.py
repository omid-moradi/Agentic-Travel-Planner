# teams/travel_team.py
from autogen_agentchat.teams import RoundRobinGroupChat
from models.GoogleModel import model_client
from agents.planner import build_planner
from agents.researcher import build_researcher
from config.settings import app_cfg
from utils.utils import get_termination_conditions

async def build_travel_team():
    """
    Assemble the travel team (researcher + planner) with proper async agent construction.
    Returns an initialized RoundRobinGroupChat.
    """
    researcher = await build_researcher(model_client)
    planner = await build_planner(model_client)

    team = RoundRobinGroupChat(
        participants=[planner, researcher],  # or [researcher, planner] بسته به جریان دلخواه
        name="travel_team",
        description="Team for travel planning and research on Iran trips.",
        max_turns=app_cfg.MAX_TURNS,
        termination_condition=get_termination_conditions(),
    )
    return team
