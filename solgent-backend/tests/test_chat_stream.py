"""
Tests the CONTROL FLOW of /chat/stream — SSE framing correctness and that
the assistant's assembled reply gets persisted to Supabase — without hitting
Groq or a real Supabase project.

AsyncIterMock exists because stream_with_history is now an async generator
(post-AsyncOpenAI migration): a plain `iter([...])` is a sync iterator and
`async for` in main.py cannot consume it — that's precisely the
`TypeError: 'async for' requires an object with __aiter__ method` failure
this file was producing before this fix. AsyncIterMock implements
__aiter__/__anext__ explicitly so the mock genuinely behaves like the real
async generator it's replacing, not merely looks like one from the outside.
"""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class AsyncIterMock:
    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


def test_chat_stream_emits_sse_data_and_done_events():
    fake_db = MagicMock()
    fake_db.fetch_chat_session.return_value = []

    with patch("app.main.SupabaseMemoryManager", return_value=fake_db), \
         patch("app.main.CloudLLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.stream_with_history.return_value = AsyncIterMock(["Hel", "lo", " world"])
        mock_llm_cls.return_value = mock_llm

        response = client.post(
            "/chat/stream",
            json={"message": "hi", "session_id": "test-session"},
        )
        body = response.text

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.count("data:") == 4
    assert "event: done" in body


def test_chat_stream_persists_assembled_assistant_reply():
    fake_db = MagicMock()
    fake_db.fetch_chat_session.return_value = []

    with patch("app.main.SupabaseMemoryManager", return_value=fake_db), \
         patch("app.main.CloudLLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.stream_with_history.return_value = AsyncIterMock(["Hel", "lo"])
        mock_llm_cls.return_value = mock_llm

        client.post("/chat/stream", json={"message": "hi", "session_id": "abc123"})

    fake_db.log_message.assert_any_call("abc123", "user", "hi")
    fake_db.log_message.assert_any_call("abc123", "assistant", "Hello")


def test_chat_stream_surfaces_upstream_error_as_sse_error_event():
    fake_db = MagicMock()
    fake_db.fetch_chat_session.return_value = []

    with patch("app.main.SupabaseMemoryManager", return_value=fake_db), \
         patch("app.main.CloudLLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.stream_with_history.return_value = AsyncIterMock(["[[STREAM_ERROR]] rate limited"])
        mock_llm_cls.return_value = mock_llm

        response = client.post(
            "/chat/stream",
            json={"message": "hi", "session_id": "err-session"},
        )

    assert "event: error" in response.text
    persisted_roles = [c.args[1] for c in fake_db.log_message.call_args_list]
    assert "assistant" not in persisted_roles