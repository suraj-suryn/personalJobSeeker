"""
Unified LLM client supporting multiple zero-cost providers:
  - Ollama       (local, completely free)
  - OpenRouter   (online, free tier: meta-llama/llama-3.1-8b-instruct:free)
  - Groq         (online, free tier: 14,400 req/day)
  - Google Gemini (online, free tier: 1M tokens/day)
  - OpenAI       (paid, optional upgrade)

Usage:
    llm = LLMRouter()
    response = await llm.chat([{"role": "user", "content": "Hello"}])
"""

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": "..."}


class OllamaClient:
    """Local Ollama inference — completely free."""

    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_default_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model or self.default_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False


class OpenRouterClient:
    """OpenRouter — free tier includes llama-3.1-8b-instruct:free."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_free_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/PersonalJobSeeker",
            "X-Title": "PersonalJobSeeker",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json={
                    "model": model or self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return bool(self.api_key)


class GroqClient:
    """Groq API — free tier: 14,400 req/day, very fast inference."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self) -> None:
        self.api_key = settings.groq_api_key
        self.model = settings.groq_free_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json={
                    "model": model or self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return bool(self.api_key)


class GeminiClient:
    """Google Gemini — free tier: 1M tokens/day."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_free_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        # Convert OpenAI-style messages to Gemini format
        contents = []
        system_text = ""
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            elif msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        used_model = model or self.model
        url = f"{self.BASE_URL}/models/{used_model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def is_available(self) -> bool:
        return bool(self.api_key)


class OpenAIClient:
    """OpenAI — paid, optional upgrade path."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self) -> None:
        self.api_key = settings.openai_api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        messages: list[Message],
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return bool(self.api_key)


class LLMRouter:
    """
    Unified LLM interface with automatic fallback chain.

    Priority order (all zero-cost):
      1. Ollama (local)    — if running and available
      2. OpenRouter free   — if API key set
      3. Groq free         — if API key set
      4. Gemini free       — if API key set
      5. OpenAI            — if API key set (paid fallback)

    Per-user override: pass `provider` to force a specific client.
    """

    def __init__(self) -> None:
        self._ollama = OllamaClient()
        self._openrouter = OpenRouterClient()
        self._groq = GroqClient()
        self._gemini = GeminiClient()
        self._openai = OpenAIClient()

    def _get_client(self, provider: str) -> Any:
        mapping = {
            "ollama": self._ollama,
            "openrouter": self._openrouter,
            "groq": self._groq,
            "gemini": self._gemini,
            "openai": self._openai,
        }
        return mapping.get(provider, self._ollama)

    async def chat(
        self,
        messages: list[Message],
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat request. If provider is specified, use it directly.
        Otherwise auto-detect available providers in priority order.
        """
        if provider:
            client = self._get_client(provider)
            return await client.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)

        # Auto-fallback chain
        providers_to_try: list[tuple[str, Any]] = []

        # Try Ollama first (local, best quality, no rate limits)
        if await self._ollama.is_available():
            providers_to_try.append(("ollama", self._ollama))

        if self._openrouter.is_available():
            providers_to_try.append(("openrouter", self._openrouter))
        if self._groq.is_available():
            providers_to_try.append(("groq", self._groq))
        if self._gemini.is_available():
            providers_to_try.append(("gemini", self._gemini))
        if self._openai.is_available():
            providers_to_try.append(("openai", self._openai))

        if not providers_to_try:
            raise RuntimeError(
                "No LLM provider available. "
                "Start Ollama or add a free API key (OPENROUTER_API_KEY, GROQ_API_KEY, GEMINI_API_KEY)."
            )

        last_error: Exception | None = None
        for name, client in providers_to_try:
            try:
                logger.debug("Trying LLM provider: %s", name)
                result = await client.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
                return result
            except Exception as exc:
                logger.warning("LLM provider %s failed: %s", name, exc)
                last_error = exc
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


# Singleton instance
_llm_router: LLMRouter | None = None


def get_llm() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
