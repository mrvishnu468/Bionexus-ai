
import os

from app.services.ai_provider import OpenAICompatibleIntentProvider
from app.services.intent_interpreter import ResearchIntentInterpreter


base_url = os.getenv("BIONEXUS_AI_BASE_URL", "").strip()
model = os.getenv("BIONEXUS_AI_MODEL", "").strip()

provider = (
    OpenAICompatibleIntentProvider()
    if base_url and model
    else None
)

intent_interpreter = ResearchIntentInterpreter(provider=provider)
