from autogen_agentchat.agents import AssistantAgent
from config.settings import google_cfg, app_cfg

SYSTEM_MSG = """
You are a travel planner agent specialized in trips in Iran.

## TASK:
Transform user request + research findings into a feasible itinerary for Iran.

---
## OUTPUT FORMAT (strict JSON, one object):
Example:
{
  "currency": "TOMAN",
  "overview": "string",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "summary": "string",
      "morning": ["POI or activity", "..."],
      "afternoon": ["POI or activity", "..."],
      "evening": ["POI or activity", "..."],
      "est_cost_toman": 0
    }
  ],
  "total_est_cost_toman": 0
}
---

## CONSTRAINTS:
- Respect budget level; minimize transit friction; cluster POIs geographically in Iranian cities.
- Consider opening hours, prayer times where relevant, domestic transport (flight/train/bus/metro/taxi apps), and seasonal variations.
- Add buffer time; avoid backtracking; ensure activities are culturally appropriate.

---
## RULES:
- Strict JSON only (no markdown fences, no comments, no trailing commas).
- Do not output any text outside the JSON object.
- All costs in TOMAN; use rounded integers (no decimals).
- Dates must be realistic, starting from the requested trip start date.
- If uncertain, use conservative ranges in text but pick a single rounded integer for the JSON fields.
"""


async def build_planner(model_client) -> AssistantAgent:
    """
    Create and configure the Iran-focused planner agent.

    The agent converts the request + research notes into a day-by-day itinerary,
    enforcing strict JSON with TOMAN budgeting via response_format and default kwargs.

    Args:
        model_client: OpenAI-compatible Gemini client used for chat completions.

    Returns:
        AssistantAgent: Configured "planner" agent with JSON output and reasoning effort presets.
    """
    agent = AssistantAgent(
        name="planner",
        model_client=model_client,
        description="Plans geographically-efficient itineraries in Iran with TOMAN budgeting.",
        system_message=SYSTEM_MSG,
    )

    agent.extra_create_kwargs = {
        "response_format": {"type": "json_object"},
        "extra_body": {
            "reasoning": {"effort": google_cfg.REASONING_EFFORT}
        },
        "temperature": app_cfg.TEMPERATURE,
    }

    return agent
