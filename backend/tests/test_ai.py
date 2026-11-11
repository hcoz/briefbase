"""ai.summarize against a fake Gemini client: retry, fallback, never raises."""

import json
from types import SimpleNamespace

import pytest

from app import ai

VALID = json.dumps({"summary": "A short summary.", "tags": ["python", "sql", "testing"]})


class FakeClient:
    """Stands in for genai.Client; each call pops the next response (text or exception)."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.models = self  # client.models.generate_content(...)

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(text=response)


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setattr(ai.settings, "gemini_api_key", "test-key")

    def install(*responses):
        fake = FakeClient(responses)
        monkeypatch.setattr(ai, "_client", lambda: fake)
        return fake

    return install


def test_valid_response(gemini):
    fake = gemini(VALID)
    result = ai.summarize("Title", "some note")
    assert result == ai.AIResult(summary="A short summary.", tags=["python", "sql", "testing"])
    assert len(fake.calls) == 1
    assert fake.calls[0]["contents"].startswith("Title: Title")


def test_tags_are_normalized(gemini):
    raw = json.dumps({"summary": " s ", "tags": ["Python", "#SQL", "python", " ", "a", "b", "c"]})
    gemini(raw)
    result = ai.summarize(None, "x")
    assert result is not None
    assert result.summary == "s"
    assert result.tags == ["python", "sql", "a", "b", "c"]  # lowercased, deduped, capped at 5


@pytest.mark.parametrize(
    "bad",
    ["not json", '{"summary": "no tags"}', json.dumps({"summary": "s", "tags": []}), None],
    ids=["not-json", "missing-field", "empty-tags", "no-text"],
)
def test_malformed_output_is_retried_once(gemini, bad):
    fake = gemini(bad, VALID)
    assert ai.summarize(None, "x") is not None
    assert len(fake.calls) == 2


def test_gives_up_after_second_malformed_output(gemini):
    fake = gemini("nope", "still nope")
    assert ai.summarize(None, "x") is None
    assert len(fake.calls) == 2


def test_provider_error_returns_none(gemini):
    gemini(TimeoutError("deadline exceeded"))
    assert ai.summarize(None, "x") is None


def test_missing_api_key_skips_the_call(monkeypatch):
    monkeypatch.setattr(ai.settings, "gemini_api_key", "")
    monkeypatch.setattr(ai, "_client", lambda: pytest.fail("client must not be created"))
    assert ai.summarize(None, "x") is None


def test_long_content_is_truncated(gemini):
    fake = gemini(VALID)
    ai.summarize(None, "a" * (ai.MAX_INPUT_CHARS + 5000))
    assert len(fake.calls[0]["contents"]) == ai.MAX_INPUT_CHARS
