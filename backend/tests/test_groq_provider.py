import pytest

from app.services.ai import groq_provider


def test_groq_provider_initializes_with_reliability_settings(
    monkeypatch,
):
    captured = {}

    class FakeGroq:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(groq_provider, "Groq", FakeGroq)

    monkeypatch.setattr(
        groq_provider.settings,
        "ai_provider_timeout_seconds",
        15.0,
    )
    monkeypatch.setattr(
        groq_provider.settings,
        "ai_provider_max_retries",
        3,
    )

    provider = groq_provider.GroqProvider()

    assert provider.client is not None
    assert captured["api_key"] == "test-api-key"
    assert captured["timeout"] == 15.0
    assert captured["max_retries"] == 3


def test_groq_provider_handles_missing_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    provider = groq_provider.GroqProvider()

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        provider.generate_response("System", "User")


def test_groq_provider_rejects_empty_response(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return type(
                "Completion",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {
                                "message": type(
                                    "Message",
                                    (),
                                    {"content": "   "},
                                )()
                            },
                        )()
                    ]
                },
            )()

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat",
                (),
                {"completions": FakeCompletions()},
            )()

    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(groq_provider, "Groq", FakeGroq)

    provider = groq_provider.GroqProvider()

    with pytest.raises(RuntimeError, match="empty response"):
        provider.generate_response("System", "User")


def test_groq_provider_rejects_missing_choices(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            return type("Completion", (), {"choices": []})()

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat",
                (),
                {"completions": FakeCompletions()},
            )()

    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(groq_provider, "Groq", FakeGroq)

    provider = groq_provider.GroqProvider()

    with pytest.raises(RuntimeError, match="no completion choices"):
        provider.generate_response("System", "User")


def test_groq_provider_returns_stripped_response(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)

            message = type(
                "Message",
                (),
                {"content": "  Hello customer!  "},
            )()

            choice = type(
                "Choice",
                (),
                {"message": message},
            )()

            return type(
                "Completion",
                (),
                {"choices": [choice]},
            )()

    class FakeGroq:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat",
                (),
                {"completions": FakeCompletions()},
            )()

    monkeypatch.setenv("GROQ_API_KEY", "test-api-key")
    monkeypatch.setattr(groq_provider, "Groq", FakeGroq)

    provider = groq_provider.GroqProvider()

    result = provider.generate_response("System", "User")

    assert result == "Hello customer!"
    assert captured["model"] == provider.model
    assert captured["max_tokens"] == (
        groq_provider.settings.ai_provider_max_tokens
    )