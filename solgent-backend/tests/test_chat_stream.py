"""
Tests the CONTROL FLOW of /chat/stream — SSE framing correctness and that
the assistant's assembled reply gets persisted to Supabase — without hitting
Groq or a real Supabase project. CloudLLMClient and SupabaseMemoryManager
are patched at their import site in app.main, not at their definition site,
which is the detail that makes `patch()` actually intercept the call FastAPI
makes inside the route handler (patching app.services.cloud_llm.CloudLLMClient
would NOT work here, since app.main already holds its own reference to the
class from its `from ... import CloudLLMClient` at module load time).

This intentionally does not assert anything about response content quality —
that's what Stage 2's load test and manual QA are for. This test exists to
catch the boring-but-real regression risk: someone touches the SSE
formatting or the finally-block persistence logic in main.py and breaks it
without Groq/Supabase creds available to notice locally.
"""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_stream_emits_sse_data_and_done_events():
    fake_db = MagicMock()
    fake_db.fetch_chat_session.return_value = []

    with patch("app.main.SupabaseMemoryManager", return_value=fake_db), \
         patch("app.main.CloudLLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.stream_with_history.return_value = iter(["Hel", "lo", " world"])
        mock_llm_cls.return_value = mock_llm

        response = client.post(
            "/chat/stream",
            json={"message": "hi", "session_id": "test-session"},
        )
        body = response.text

   assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body.count('data: {"token":') == 3
    assert body.count("data:") == 4
    assert "event: done" in body


def test_chat_stream_persists_assembled_assistant_reply():
    fake_db = MagicMock()
    fake_db.fetch_chat_session.return_value = []

    with patch("app.main.SupabaseMemoryManager", return_value=fake_db), \
         patch("app.main.CloudLLMClient") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.stream_with_history.return_value = iter(["Hel", "lo"])
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
        mock_llm.stream_with_history.return_value = iter(["[[STREAM_ERROR]] rate limited"])
        mock_llm_cls.return_value = mock_llm

        response = client.post(
            "/chat/stream",
            json={"message": "hi", "session_id": "err-session"},
        )

    assert "event: error" in response.text
    # No assistant turn should be persisted on a failed stream — an empty
    # reply in history would confuse the next turn's context.
    persisted_roles = [c.args[1] for c in fake_db.log_message.call_args_list]
    assert "assistant" not in persisted_roles