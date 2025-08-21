from config.settings import GOOGLE_API_KEY, MODEL, TEMPERATURE, MAX_TOKENS, MAX_TURNS, TERMINATION_WORD
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model=MODEL,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    api_key=GOOGLE_API_KEY,
)
