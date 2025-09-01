# agents/researcher.py (Final Corrected Version)

from autogen_agentchat.agents import AssistantAgent
from config.settings import google_cfg, app_cfg
from tools.web_search import web_search

SYSTEM_MSG = """
You are a world-class travel research agent for Iran. Your workflow is to first use tools to gather live facts, and then synthesize the results into a single, final JSON report.

**1. Tool Use:**
- First, use the `web_search` tool to find up-to-date information.
- The tool returns a dictionary: `web_search(query: str) -> { ok: bool, answer: str, sources: [{name,url}] }`
- You can use the tool multiple times if needed.

**2. Final Output:**
- After you have gathered all necessary information, your FINAL response MUST be a single JSON object.
- Do not add any text or markdown fences like ```json before or after the JSON object.
- The JSON must conform to this structure:
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
  "risks": ["..."],
  "verification": ["..."]
}
"""

async def build_researcher(model_client) -> AssistantAgent:
    """
    Builds and configures the Research Agent, equipping it with a web search tool
    and instructing it to reflect on the tool's output to generate a final JSON report.
    """
    agent = AssistantAgent(
        name="researcher",
        model_client=model_client,
        description="Uses web search to find up-to-date travel info for Iran and returns a structured JSON report.",
        system_message=SYSTEM_MSG,
        tools=[web_search],
        # CRITICAL: Must be True for the agent to process tool results and then generate a final answer.
        reflect_on_tool_use=True, 
    )

    # CRITICAL: We remove 'response_format' to allow the agent to freely choose
    # between outputting a tool call or a final JSON response.
    agent.extra_create_kwargs = {
        "extra_body": {"reasoning": {"effort": google_cfg.REASONING_EFFORT}},
        "temperature": min(app_cfg.TEMPERATURE, 0.35)
    }

    return agent