import pytest
from agents.planner import build_planner, SYSTEM_MSG as PLANNER_SYSTEM_MSG
from agents.researcher import build_researcher, SYSTEM_MSG as RESEARCHER_SYSTEM_MSG
from models.GoogleModel import model_client

@pytest.mark.asyncio
async def test_planner_initialization():
    agent = await build_planner(model_client)
    assert agent is not None
    assert agent.name == "planner"
    assert agent.description == "Plans geographically-efficient itineraries in Iran with TOMAN budgeting."
    assert len(agent._system_messages) >= 1
    assert agent._system_messages[0].content.strip() == PLANNER_SYSTEM_MSG.strip()

@pytest.mark.asyncio
async def test_researcher_initialization():
    agent = await build_researcher(model_client)
    assert agent is not None
    assert agent.name == "researcher"
    assert agent.description == (
        "Conducts destination research for Iran and returns structured findings with sources (TOMAN)."
    )
    assert len(agent._system_messages) >= 1
    assert agent._system_messages[0].content.strip() == RESEARCHER_SYSTEM_MSG.strip()
