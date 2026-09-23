"""
Smoke test for the FastAPI app object and /health endpoint.

This intentionally does NOT hit /chat. That route instantiates
CloudLLMClient and SupabaseMemoryManager, both of which raise ValueError
at construction time if GROQ_API_KEY / SUPABASE_URL / SUPABASE_KEY are
unset (see app/config.py) — which they will be in a CI runner with no
secrets configured. Testing /chat for real requires mocking those two
clients; that's a follow-up commit once we decide whether to record/replay
fixtures or use dependency injection. For now, /health is the correct
"is the app alive and importable" contract for CI to enforce, and it's
also literally the endpoint your container orchestrator (Cloud Run, ECS,
Kubernetes) will poll to decide whether to route traffic to this instance.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload_shape():
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "healthy"
    assert "persistence" in body


def test_app_metadata():
    assert app.title == "SolGent Workspace Cloud Engine"
