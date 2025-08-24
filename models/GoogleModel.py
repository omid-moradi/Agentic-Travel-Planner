from autogen_ext.models.openai import OpenAIChatCompletionClient
from config.settings import google_cfg, app_cfg
from autogen_core.models import ModelInfo

MODEL_INFO = ModelInfo(
    vision=True,
    json_output=True,
    structured_output=True,
    function_calling=True,
    family="gemini",
)

model_client = OpenAIChatCompletionClient(
    model=google_cfg.MODEL,
    api_key=google_cfg.API_KEY,
    base_url=google_cfg.BASE_URL,
    temperature=app_cfg.TEMPERATURE,
    max_tokens=4096,
    timeout=google_cfg.TIMEOUT, 
    model_info=MODEL_INFO,
)

extra_create_kwargs = {
    "extra_body": {
        "reasoning": {
            "effort": google_cfg.REASONING_EFFORT  # 👈 low/medium/high
        }
    }
}
