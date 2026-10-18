
import asyncio
import json

import httpx
import pytest

from app.services.ai_provider import OpenAICompatibleIntentProvider


def make_client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )


def test_provider_sends_structured_request():
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["model"] == "test-model"
        assert body["response_format"] == {"type": "json_object"}
        assert body["temperature"] == 0
        assert body["messages"][0]["role"] == "system"

        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "original_question": "test query"
                        })
                    }
                }]
            },
        )

    async def run():
        async with make_client(handler) as client:
            provider = OpenAICompatibleIntentProvider(
                base_url="https://example.test/v1",
                model="test-model",
                api_key="test-secret",
                client=client,
            )
            result = await provider.interpret("test query")
            assert result == {"original_question": "test query"}

    asyncio.run(run())


def test_provider_rejects_missing_configuration():
    provider = OpenAICompatibleIntentProvider(
        base_url="",
        model="",
        api_key="",
    )

    with pytest.raises(RuntimeError, match="BASE_URL"):
        asyncio.run(provider.interpret("test query"))


def test_provider_reports_http_errors_without_response_body():
    def handler(request):
        return httpx.Response(
            503,
            text="private provider diagnostic",
        )

    async def run():
        async with make_client(handler) as client:
            provider = OpenAICompatibleIntentProvider(
                base_url="https://example.test/v1",
                model="test-model",
                client=client,
            )
            with pytest.raises(RuntimeError, match="HTTP 503") as error:
                await provider.interpret("test query")

            assert "private provider diagnostic" not in str(error.value)

    asyncio.run(run())


def test_provider_rejects_malformed_response():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {"content": "not valid JSON"}
                }]
            },
        )

    async def run():
        async with make_client(handler) as client:
            provider = OpenAICompatibleIntentProvider(
                base_url="https://example.test/v1",
                model="test-model",
                client=client,
            )
            with pytest.raises(RuntimeError, match="invalid JSON"):
                await provider.interpret("test query")

    asyncio.run(run())
