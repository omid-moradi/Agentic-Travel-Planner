# agents/planner.py
from autogen_agentchat.agents import AssistantAgent
from config.settings import google_cfg, app_cfg

SYSTEM_MSG = (
    "You are a travel planner agent.\n"
    "Transform user request + research findings into a realistic itinerary.\n"
    "Output ONLY one JSON object with keys: overview, days[], total_est_cost_usd.\n"
    "Each day item: {date (YYYY-MM-DD), summary, morning[], afternoon[], evening[], est_cost_usd (float)}.\n"
    "Constraints: respect budget level; minimize transit friction; cluster POIs geographically;\n"
    "use opening hours heuristics; add buffer time; avoid backtracking.\n"
    "Rules: strictly valid JSON; no comments; no trailing commas; USD floats."
)

def build_planner(model_client) -> AssistantAgent:
    """
    Build the planner agent using the OpenAI-compatible Gemini client.
    - Forces structured JSON output via OpenAI-style `response_format`.
    - Passes Gemini-specific reasoning effort via `extra_body`.
    """
    agent = AssistantAgent(
        name="planner",
        model_client=model_client,
        description="Plans complete, geographically-efficient travel itineraries as JSON.",
        system_message=SYSTEM_MSG,
    )

    # Default create kwargs for ALL planner generations.
    # Note:
    # - `response_format={"type": "json_object"}` is OpenAI-compatible JSON mode.
    # - `extra_body={"reasoning": {"effort": ...}}` is Gemini-specific (ignored by non-Gemini backends).
    agent.extra_create_kwargs = {
        "response_format": {"type": "json_object"},
        "extra_body": {
            "reasoning": {"effort": google_cfg.REASONING_EFFORT}  # none|low|medium|high
        },
        # Optional: you can also pass temperature per-agent if you want to override global:
        "temperature": app_cfg.TEMPERATURE,
    }

    return agent
