import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LmStudioClient:
    """Minimal client for LM Studio's OpenAI-compatible local API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def rewrite(self, prompt: str) -> dict:
        model = self.model or self._loaded_model()
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Write a concise, professional Spanish business email. "
                        "Return the JSON immediately. Do not include analysis, reasoning, "
                        "explanations, or tool calls."
                    ),
                },
                {"role": "user", "content": f"{prompt}\n\n/no_think"},
            ],
            "temperature": 0.5,
            "max_tokens": 200,
            "stream": True,
        }
        content = self._post_stream("/chat/completions", payload).strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(content)

    def _loaded_model(self) -> str:
        response = self._get("/models")
        models = response.get("data", [])
        if not models:
            raise RuntimeError("LM Studio has no loaded model.")
        return models[0]["id"]

    def _get(self, path: str) -> dict:
        request = Request(f"{self.base_url}{path}")
        return self._send(request)

    def _post_stream(self, path: str, data: dict) -> str:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return self._content_from_stream(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"LM Studio request failed: {error}") from error

    @staticmethod
    def _content_from_stream(lines) -> str:
        content_parts = []
        for raw_line in lines:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue

            data = line.removeprefix("data: ")
            if data == "[DONE]":
                break

            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if text := delta.get("content"):
                content_parts.append(text)

        return "".join(content_parts)

    @staticmethod
    def _send(request: Request) -> dict:
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"LM Studio request failed: {error}") from error
