"""
Unit tests for the intent-classification router.

route_intent() is pure logic — no network, no Supabase, no Groq — which makes it
the highest-value, lowest-cost thing to test in this codebase. It's also the
component most likely to silently regress: adding a new keyword to one branch
can accidentally shadow another branch's classification with no runtime error,
just a wrong answer. These tests pin the current classification contract so
that regression shows up as a failed assertion in CI, not as a support ticket.
"""

from app.utils.router import route_intent


def test_developer_workspace_intent_detected():
    result = route_intent("I'm getting a bug in my docker container, help me debug")
    assert result["workflow"] == "DEVELOPER_WORKSPACE"
    assert result["needs_youtube"] is False
    assert result["needs_commerce"] is False


def test_developer_workspace_error_adds_root_cause_hint():
    result = route_intent("getting an error when I run the function")
    assert result["workflow"] == "DEVELOPER_WORKSPACE"
    assert "root-cause" in result["system_hint"]


def test_student_companion_intent_triggers_youtube():
    result = route_intent("can you explain how photosynthesis works")
    assert result["workflow"] == "STUDENT_COMPANION"
    assert result["needs_youtube"] is True
    assert "comprehensive academic tutorial" in result["yt_query"]


def test_general_fallback_when_no_keywords_match():
    result = route_intent("hello there")
    assert result["workflow"] == "GENERAL_KNOWLEDGE"
    assert result["needs_youtube"] is False
    assert result["needs_commerce"] is False


def test_route_intent_always_returns_required_keys():
    required_keys = {
        "workflow",
        "needs_youtube",
        "needs_commerce",
        "yt_query",
        "commerce_query",
        "system_hint",
    }
    result = route_intent("anything at all")
    assert required_keys.issubset(result.keys())
