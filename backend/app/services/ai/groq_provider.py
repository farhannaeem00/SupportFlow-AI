import os

from groq import Groq

from app.config import settings
from app.services.ai.base import AIProvider


class GroqProvider(AIProvider):
    """Groq implementation of the AI provider interface."""

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        self.client = (
            Groq(
                api_key=api_key,
                timeout=settings.ai_provider_timeout_seconds,
                max_retries=settings.ai_provider_max_retries,
            )
            if api_key
            else None
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile",
        )

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if self.client is None:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=settings.ai_provider_max_tokens,
        )

        if not completion.choices:
            raise RuntimeError("Groq returned no completion choices.")

        content = completion.choices[0].message.content

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Groq returned an empty response.")

        return content.strip()