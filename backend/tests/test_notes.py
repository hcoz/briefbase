import pytest

from app import ai
from app.ai import AIResult


@pytest.fixture
def fake_ai(monkeypatch):
    """Deterministic AI: summary echoes the content, tags are its words."""

    def fake_summarize(title, content):
        return AIResult(summary=f"About: {content}", tags=content.split())

    monkeypatch.setattr(ai, "summarize", fake_summarize)


def _create(client, headers, content, title=None):
    r = client.post("/notes", json={"title": title, "content": content}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_note_stores_ai_summary_and_tags(client, register, fake_ai):
    headers = register()
    note = _create(client, headers, "python sql", title="Stack")
    assert note["title"] == "Stack"
    assert note["summary"] == "About: python sql"
    assert note["tags"] == ["python", "sql"]

    listed = client.get("/notes", headers=headers).json()
    assert listed == [note]  # persisted, not just echoed back


def test_create_note_is_saved_when_ai_fails(client, register, monkeypatch):
    monkeypatch.setattr(ai, "summarize", lambda title, content: None)
    headers = register()
    note = _create(client, headers, "keep this text")
    assert note["content"] == "keep this text"
    assert note["summary"] is None
    assert note["tags"] == []
    assert len(client.get("/notes", headers=headers).json()) == 1


@pytest.mark.parametrize("content", ["", "   \n\t "], ids=["empty", "whitespace"])
def test_create_note_rejects_blank_content(client, register, content):
    r = client.post("/notes", json={"content": content}, headers=register())
    assert r.status_code == 422


def test_blank_title_is_stored_as_null(client, register, fake_ai):
    assert _create(client, register(), "text", title="   ")["title"] is None


def test_list_is_newest_first(client, register, fake_ai):
    headers = register()
    ids = [_create(client, headers, f"note{i}")["id"] for i in range(3)]
    listed = [n["id"] for n in client.get("/notes", headers=headers).json()]
    assert listed == ids[::-1]


def test_tag_filter_returns_only_matching_notes(client, register, fake_ai):
    headers = register()
    a = _create(client, headers, "python sql")
    b = _create(client, headers, "python docker")
    _create(client, headers, "react css")

    def ids(tag):
        r = client.get("/notes", params={"tag": tag}, headers=headers)
        assert r.status_code == 200
        return {n["id"] for n in r.json()}

    assert ids("python") == {a["id"], b["id"]}
    assert ids("  PYTHON ") == {a["id"], b["id"]}  # normalized like stored tags
    assert ids("docker") == {b["id"]}
    assert ids("nope") == set()
    assert len(client.get("/notes", headers=headers).json()) == 3  # no filter


def test_delete_note(client, register, fake_ai):
    headers = register()
    note = _create(client, headers, "temp")
    assert client.delete(f"/notes/{note['id']}", headers=headers).status_code == 204
    assert client.get("/notes", headers=headers).json() == []
    assert client.delete(f"/notes/{note['id']}", headers=headers).status_code == 404


def test_users_cannot_see_or_touch_each_others_notes(client, register, fake_ai):
    alice, bob = register("alice@example.com"), register("bob@example.com")
    note = _create(client, alice, "python secret")

    assert client.get("/notes", headers=bob).json() == []
    assert client.get("/notes", params={"tag": "python"}, headers=bob).json() == []
    # Someone else's note looks exactly like a missing one.
    assert client.delete(f"/notes/{note['id']}", headers=bob).status_code == 404
    assert client.post(f"/notes/{note['id']}/summarize", headers=bob).status_code == 404
    assert client.delete("/notes/999999", headers=bob).status_code == 404

    assert client.get("/notes", headers=alice).json() == [note]  # untouched


def test_resummarize_updates_note(client, register, monkeypatch):
    monkeypatch.setattr(ai, "summarize", lambda title, content: None)
    headers = register()
    note = _create(client, headers, "python sql")
    assert note["summary"] is None

    monkeypatch.setattr(ai, "summarize", lambda title, content: AIResult(summary="S", tags=["x"]))
    r = client.post(f"/notes/{note['id']}/summarize", headers=headers)
    assert r.status_code == 200
    assert (r.json()["summary"], r.json()["tags"]) == ("S", ["x"])
    assert client.get("/notes", headers=headers).json()[0]["summary"] == "S"


def test_resummarize_failure_returns_502_and_keeps_note(client, register, fake_ai, monkeypatch):
    headers = register()
    note = _create(client, headers, "python sql")

    monkeypatch.setattr(ai, "summarize", lambda title, content: None)
    r = client.post(f"/notes/{note['id']}/summarize", headers=headers)
    assert r.status_code == 502
    assert client.get("/notes", headers=headers).json() == [note]
