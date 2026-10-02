"""Agentic Travel Planner.

Plans and manages an entire trip - domestic Iran and international - in Persian (RTL) and English.

The package is a modular monolith:

* ``config``  typed, env-driven settings and market region profiles
* ``llm``     provider-agnostic model factory (OpenAI-compatible, Ollama, offline mock)
* ``schemas`` typed data contracts shared by agents, tools and providers
* ``graph``   the LangGraph workflow over a checkpointed ``TravelState``
* ``providers``  data providers behind ``Protocol`` interfaces with fallback chains
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
