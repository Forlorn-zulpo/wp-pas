import time

import httpx


class AIClientError(Exception):
    pass


class AICompletionResult:
    def __init__(self, text: str, input_tokens: int, output_tokens: int, duration_ms: int):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms


class AnthropicClient:
    """Real client for the Anthropic Messages API
    (https://docs.claude.com/en/api/messages). Same pattern as the
    WooCommerce connector in Phase 4: this is genuine request/response
    handling for the real API shape, tested against a mocked HTTP
    transport since this sandbox has no API key configured for the
    project's own use — a real deployment only needs a real key, no code
    change."""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com", timeout: float = 60.0):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def complete(self, *, system: str, user_message: str, max_tokens: int = 1024) -> AICompletionResult:
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
        duration_ms = int((time.monotonic() - started) * 1000)

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                detail = resp.text
            raise AIClientError(f"Anthropic API 错误 ({resp.status_code}): {detail}")

        body = resp.json()
        text_blocks = [b["text"] for b in body.get("content", []) if b.get("type") == "text"]
        text = "".join(text_blocks)
        usage = body.get("usage", {})

        return AICompletionResult(
            text=text,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            duration_ms=duration_ms,
        )
