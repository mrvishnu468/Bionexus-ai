
import json
import os
from typing import Any

import httpx

from app.services.intent_prompt import build_intent_messages


class OpenAICompatibleIntentProvider:
    """Call an OpenAI-compatible chat-completions API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("BIONEXUS_AI_BASE_URL", "")
        ).rstrip("/")
        self.model = model or os.getenv("BIONEXUS_AI_MODEL", "")
        self.api_key = (
            api_key if api_key is not None
            else os.getenv("BIONEXUS_AI_API_KEY", "")
        )
        self.client = client
        self.timeout = timeout

    async def interpret(self, query: str) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("BIONEXUS_AI_BASE_URL is not configured.")
        if not self.model:
            raise RuntimeError("BIONEXUS_AI_MODEL is not configured.")

        messages = build_intent_messages(query)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        if self.client is not None:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        else:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

        if response.is_error:
            raise RuntimeError(
                f"AI provider returned HTTP {response.status_code}."
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            result = json.loads(content)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "AI provider returned an invalid JSON response."
            ) from exc

        if not isinstance(result, dict):
            raise RuntimeError(
                "AI provider output must be a JSON object."
            )

        return result
