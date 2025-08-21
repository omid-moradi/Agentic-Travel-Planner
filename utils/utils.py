from autogen_agentchat.conditions import TextMentionTermination
from config.settings import app_cfg
import json
import os
from typing import Any

# Termination conditions
def get_termination_conditions():
    """
    Compose termination condition(s) for the chat.
    Currently uses a text-mention stop word; combine with max_turns at team level.
    """
    text_mention_termination = TextMentionTermination(app_cfg.TERMINATION_WORD)
    return text_mention_termination

def save_state(agent, file_path: str):
    """
    Persist agent state to a JSON file (best-effort).
    """
    try:
        state: Any = agent.save_state()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[WARN] Failed to save state: {e}")

def load_state(agent, file_path: str):
    """
    Load agent state from a JSON file (best-effort).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        agent.load_state(state)
    except FileNotFoundError:
        return
    except Exception as e:
        print(f"[WARN] Failed to load state: {e}")