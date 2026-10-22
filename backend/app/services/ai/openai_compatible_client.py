import time

import httpx

from app.services.ai.base import AICompletionResult, AIClientError

# Default endpoints for vendors whose API is OpenAI-compatible (Chat
# Completions shape: POST {base_url}/chat/completions, Bearer auth).
# A custom base_url (e.g. a local vLLM/Ollama server) always overrides this.
DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com/v1",
}


class OpenAICompatibleClient:
    """Real client for any vendor exposing an OpenAI-compatible Chat
    Completions endpoint — DeepSeek (https://api-docs.deepseek.com/) today,
    and generically any other OPENAI_COMPATIBLE provider (self-hosted
    vLLM/Ollama, etc). Same testing caveat as AnthropicClient and the
    WooCommerce connector: real request/response handling, HTTP layer
    mocked in tests since no live API key is provisioned in this sandbox."""

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, *, system: str, user_message: str, max_tokens: int = 1024) -> AICompletionResult:
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
        duration_ms = int((time.monotonic() - started) * 1000)

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                detail = resp.text
            raise AIClientError(f"API 错误 ({resp.status_code}): {detail}")

        body = resp.json()
        choices = body.get("choices", [])
        text = choices[0]["message"]["content"] if choices else ""
        usage = body.get("usage", {})

        return AICompletionResult(
            text=text,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            duration_ms=duration_ms,
        )
