from autogen_agentchat.agents import AssistantAgent
from config.settings import app_cfg

SYSTEM_MSG = """
You are a Persian travel writer. 
Input is a validated JSON (planner itinerary or research payload) for trips in Iran.
Write a concise, friendly Farsi brief for the user:
- Use clear section titles (e.g., «روز ۱»، «نکات مهم»، «بودجه تقریبی»).
- Keep it practical, avoid clichés, and ensure costs remain in TOMAN.
- Do not expose raw JSON; only produce polished Persian text.
"""

async def build_writer(model_client) -> AssistantAgent:
    agent = AssistantAgent(
        name="writer",
        model_client=model_client,
        description="Turns structured JSON into a friendly Persian brief.",
        system_message=SYSTEM_MSG,
    )
    agent.extra_create_kwargs = {
        "temperature": max(0.5, app_cfg.TEMPERATURE), 
    }
    return agent
