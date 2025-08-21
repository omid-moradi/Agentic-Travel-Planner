from autogen_agentchat.agents import AssistantAgent
from config.settings import google_cfg, app_cfg

SYSTEM_MSG = """
You are a travel research agent specialized in trips within Iran and to Iran.
GOALS:
- Produce concise, practical findings about the destination: airport/terminal transfers, best seasons, neighborhoods, safety and local norms, visas, local SIM/data, common scams, money (cash/cards), and typical costs in TOMAN.
- Prefer authoritative Farsi/Persian or official sources; include source name + URL; avoid speculative claims.
OUTPUT FORMAT (strict JSON, one object):
{
  "currency": "TOMAN",
  "findings": [
    {
      "topic": "string",
      "bullets": ["short, factual point", "..."],
      "sources": [{"name": "Site or Org (FA or EN)", "url": "https://..."}],
      "confidence": 0.0
    }
  ],
  "risks": ["seasonal/weather notes, local regulations, scams", "..."],
  "verification": ["how to verify critical points (official site, phone, etc.)", "..."]
}
RULES:
- Strict JSON (no markdown fences, no comments, no trailing commas).
- Costs in TOMAN; use rounded ranges (e.g., 150000–250000 TOMAN), no decimals.
- Cite at least 1–2 real sources per topic when possible; never invent sources.
- If uncertain or sources conflict, write 'TBD' and propose how to verify in `verification`.
"""

async def build_researcher(model_client) -> AssistantAgent:
    """
    Create and configure the Iran-focused research agent.

    The agent gathers concise, source-backed findings (in TOMAN), returning a single JSON object.
    It enables JSON mode and sets a conservative temperature for factual accuracy.

    Args:
        model_client: OpenAI-compatible Gemini client used for chat completions.

    Returns:
        AssistantAgent: Configured "researcher" agent with JSON output and reasoning effort presets.
    """
    agent = AssistantAgent(
        name="researcher",
        model_client=model_client,
        description="Conducts destination research for Iran and returns structured findings with sources (TOMAN).",
        system_message=SYSTEM_MSG,
    )

    agent.extra_create_kwargs = {
        "response_format": {"type": "json_object"},
        "extra_body": {
            "reasoning": {"effort": google_cfg.REASONING_EFFORT}  # none|low|medium|high
        },
        "temperature": min(app_cfg.TEMPERATURE, 0.35),
    }

    return agent
