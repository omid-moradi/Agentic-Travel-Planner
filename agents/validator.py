# agents/validator.py

import re
import json
from typing import Sequence, Optional, Type
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage, BaseChatMessage
from autogen_agentchat.base import Response
from autogen_core import CancellationToken

from utils.validation import ResearchReport, ItineraryPlan
from utils.validation_utils import validate_json_with_model

class ValidatorAgent(BaseChatAgent):
    """
    A robust, code-based validator for JSON messages (AutoGen v0.4+).
    It intelligently extracts JSON from markdown blocks before validation.
    """

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        last_message = messages[-1] if messages else None

        if not isinstance(last_message, TextMessage):
            reply_content = "VALIDATION_SKIPPED: Last message was not text."
            return Response(chat_message=TextMessage(content=reply_content, source=self.name))

        # --- INTELLIGENT JSON EXTRACTION ---
        # This new block makes the agent much more robust.
        content_to_validate = last_message.content.strip()
        # Find JSON within markdown code blocks (e.g., ```json ... ```)
        match = re.search(r"```(json)?\s*({.*})", content_to_validate, re.DOTALL)
        if match:
            # If found, extract the pure JSON part.
            content_to_validate = match.group(2)
        # ------------------------------------

        sender_name = getattr(last_message, "source", None)
        sender_name_lc = (sender_name or "").lower()

        model_to_use: Optional[Type] = None
        if sender_name_lc == "researcher":
            model_to_use = ResearchReport
        elif sender_name_lc == "planner":
            model_to_use = ItineraryPlan

        if model_to_use:
            validation_result = validate_json_with_model(content_to_validate, model_to_use)
        else:
            validation_result = f"VALIDATION_SKIPPED: No validation rule for sender '{sender_name}'."

        return Response(chat_message=TextMessage(content=validation_result, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        return None

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

def build_validator() -> ValidatorAgent:
    return ValidatorAgent(
        name="validator",
        description="A code-based agent that validates JSON output from other agents against a Pydantic schema.",
    )