"""
Load test for the /chat/stream SSE endpoint added in Stage 1.5.

WHAT THIS MEASURES, AND WHY IN TWO SEPARATE METRICS:

1. "/chat/stream [ttfb]" — Locust's own built-in per-request timer.
   We pass `stream=True` through to the underlying `requests` call, which
   makes `requests` return control as soon as response HEADERS arrive,
   BEFORE the body is read. That means Locust's default timer here is
   measuring connection setup + server processing (Supabase history fetch,
   intent routing, prompt build, Groq connection) up to the first byte of
   the response — i.e. "how long before the user sees ANYTHING happen."
   This is the number that determines whether the UI feels instant or laggy.

2. "/chat/stream [total]" — a custom metric we fire manually via
   events.request.fire(), measured by consuming the rest of the stream
   ourselves after headers arrive. This scales with answer length and is
   NOT a proxy for inference speed on its own — a 400-token answer will
   always show a longer [total] than a 40-token answer, that's expected,
   not a regression. What IS worth watching is [total] minus [ttfb]: that
   delta divided by token_count approximates the per-token generation rate
   during steady-state streaming, which is the actual Groq-LPU throughput
   number worth quoting.

Run against a LOCAL docker-compose stack first (see README below) before
ever pointing this at a shared/staging Supabase project — every simulated
user writes two real rows to your chat_history table per request.
"""
import time
from locust import HttpUser, task, between, events


class SolGentStreamUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # One session_id per simulated user for the life of the test run,
        # so Supabase's fetch_chat_session() has a realistic (small,
        # growing) history to pull on each request, rather than every
        # request hitting an empty-history fast path that wouldn't be
        # representative of a real multi-turn conversation.
        self.session_id = f"locust-{id(self)}-{int(time.time())}"

    @task
    def stream_chat(self):
        payload = {
            "message": "Explain how binary search works, step by step",
            "session_id": self.session_id,
            "deep_think": False,
        }

        stream_start = time.perf_counter()

        with self.client.post(
            "/chat/stream",
            json=payload,
            stream=True,
            catch_response=True,
            name="/chat/stream [ttfb]",
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return

            token_count = 0
            saw_error_event = False

            try:
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8")
                    if line.startswith("event: error"):
                        saw_error_event = True
                    elif line.startswith("data:"):
                        token_count += 1
            except Exception as exc:
                response.failure(f"stream read error: {exc}")
                return

            total_time_ms = (time.perf_counter() - stream_start) * 1000

            if saw_error_event:
                response.failure("backend emitted an SSE error event")
            elif token_count == 0:
                response.failure("stream closed with zero tokens received")
            else:
                response.success()

            events.request.fire(
                request_type="SSE",
                name="/chat/stream [total]",
                response_time=total_time_ms,
                response_length=token_count,
                exception=None,
            )