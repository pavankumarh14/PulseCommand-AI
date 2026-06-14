"""
LLM Connector — provider-agnostic interface.

Supported providers (set via .env or environment variables):
  openai     → OpenAI API         (default)
  groq       → Groq API           (OpenAI-compatible)
  deepseek   → DeepSeek API       (OpenAI-compatible)
  gemini     → Google Gemini API  (OpenAI-compatible endpoint)
  anthropic  → Anthropic Claude

Configuration (via .env):
  LLM_PROVIDER=openai
  LLM_API_KEY=sk-...
  LLM_MODEL=gpt-4o-mini          (optional — sane default chosen per provider)
"""

import os
from dotenv import load_dotenv

load_dotenv()

_PROVIDER_DEFAULTS = {
    "openai":    "gpt-4o-mini",
    "groq":      "llama-3.3-70b-versatile",
    "deepseek":  "deepseek-chat",
    "gemini":    "gemini-1.5-flash",
    "anthropic": "claude-3-5-haiku-20241022",
}

_OPENAI_COMPAT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "gemini":   "https://generativelanguage.googleapis.com/v1beta/openai/",
}


class LLMConnector:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
        self.api_key  = os.getenv("LLM_API_KEY", "").strip()
        self.model    = os.getenv("LLM_MODEL", "").strip() or _PROVIDER_DEFAULTS.get(self.provider, "gpt-4o-mini")
        self._client  = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_client(self):
        if self._client is not None:
            return self._client

        if self.provider in ("openai", "deepseek", "gemini"):
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if self.provider in _OPENAI_COMPAT_BASE_URLS:
                kwargs["base_url"] = _OPENAI_COMPAT_BASE_URLS[self.provider]
            self._client = OpenAI(**kwargs)

        elif self.provider == "groq":
            from groq import Groq
            self._client = Groq(api_key=self.api_key)

        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)

        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{self.provider}'. "
                "Valid options: openai, groq, deepseek, gemini, anthropic"
            )

        return self._client

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(self, system_prompt: str, user_message: str, max_tokens: int = 512) -> str:
        """
        Send a single-turn chat request.
        Returns the assistant's reply as a plain string.
        On any error, returns a graceful fallback message so the UI never crashes.
        """
        if not self.api_key:
            return (
                "⚠️ No LLM API key configured. "
                "Set LLM_API_KEY in your .env file to enable AI analysis."
            )

        try:
            client = self._get_client()

            if self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                return response.content[0].text.strip()

            # OpenAI-compatible (openai / groq / deepseek / gemini)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()

        except Exception as exc:
            return (
                f"⚠️ LLM request failed ({type(exc).__name__}: {exc}). "
                "Check your API key and provider settings in .env."
            )

    def provider_info(self) -> str:
        return f"{self.provider} / {self.model}"
