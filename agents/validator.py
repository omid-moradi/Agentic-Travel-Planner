# agents/validator.py

from typing import Sequence, Optional, Type
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage, BaseChatMessage
from autogen_agentchat.base import Response
from autogen_core import CancellationToken

# Import our Pydantic models and validation utility
from utils.validation import ResearchReport, ItineraryPlan
from utils.validation_utils import validate_json_with_model

class ValidatorAgent(BaseChatAgent):
    """
    A custom, code-based agent for validating JSON messages in an AutoGen v0.4+ chat.
    This agent does not use an LLM. Its logic is entirely defined in on_messages.
    """

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        # The logic inside here remains perfectly correct.
        last_message = messages[-1] if messages else None

        if not isinstance(last_message, TextMessage):
            reply_content = "VALIDATION_SKIPPED: The last message was not a text message."
            return Response(
                chat_message=TextMessage(content=reply_content, source=self.name)
            )

        content_to_validate = last_message.content
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

        return Response(
            chat_message=TextMessage(content=validation_result, source=self.name)
        )

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
