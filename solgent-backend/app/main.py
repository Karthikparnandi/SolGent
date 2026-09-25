import json
import textwrap
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.logging_config import logger
from app.models import ChatRequest, ChatResponse
from app.services.cloud_llm import CloudLLMClient
from app.services.commerce import UniversalCommerceEngine
from app.services.memory import SupabaseMemoryManager
from app.services.youtube import youtube_search
from app.utils.router import route_intent

app = FastAPI(
    title="SolGent Workspace Cloud Engine",
    version="4.0.0",
    description="Production-grade distributed workspace intelligence router backed entirely by Supabase state vectors."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting setup -----------------------------------------------
# Limiter keyed on client IP (get_remote_address). app.state.limiter and
# the exception handler let @limiter.limit(...) decorators work on
# individual routes; SlowAPIMiddleware is required in addition to those —
# without it, slowapi's decorators error on every request instead of
# only rate-limiting the 11th+ call, which is the exact bug that caused
# every /chat call to 500 before this middleware line was added.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/health")
def health_check():
    return {"status": "healthy", "architecture": "clean-slate-v4", "persistence": "supabase"}


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def handle_workspace_transaction(request: Request, req: ChatRequest):
    # 1. Coordinate conversational memory via Supabase Manager
    db = SupabaseMemoryManager()
    session_history = db.fetch_chat_session(req.session_id)

    # 2. Run incoming statement through cognitive intent parsing matrices
    intent = route_intent(req.message)
    metadata = {"intent": intent}

    # 3. Pull auxiliary learning video hooks programmatically
    yt = youtube_search(q=intent["yt_query"], max_results=2) if intent.get("needs_youtube") else []
    if yt: metadata["youtube"] = yt

    # 4. Route queries into our Universal Agnostic E-Commerce Search Engine
    products = []
    if intent.get("needs_commerce"):
        commerce_bot = UniversalCommerceEngine()
        products = commerce_bot.search_all_platforms(intent["commerce_query"])
        metadata["marketplace_sourcing"] = products

    # 5. New dynamic context payload compilation
    prompt = build_architectural_prompt(
        user=req.message,
        system_hint=intent.get("system_hint", ""),
        yt=yt,
        products=products,
        deep=req.deep_think
    )

    # 6. Offload raw text parsing to lightning-fast cloud LPUs
    #    NOTE: `await` here is load-bearing. Without it, `answer` is a
    #    coroutine object, not a string, and ChatResponse validation
    #    fails with a 500 on every single call — this exact bug shipped
    #    once already in this repo; see test_chat_endpoint_returns_string_answer_not_coroutine.
    client = CloudLLMClient()
    answer = await client.generate_with_history(
        prompt=prompt,
        history=session_history,
        model=req.model or "openai/gpt-oss-120b"
    )

    # 7. Sync the transaction record data back into Supabase tables
    db.log_message(req.session_id, "user", req.message)
    db.log_message(req.session_id, "assistant", answer)

    metadata["provider"] = "groq-serverless-cloud"
    return ChatResponse(answer=answer, used_metadata=metadata)


@app.post("/chat/stream")
@limiter.limit("10/minute")
async def handle_workspace_transaction_stream(request: Request, req: ChatRequest):
    """
    SSE variant of /chat. Consumed via `fetch()` + a ReadableStream reader on
    the frontend, NOT the browser's native EventSource API — EventSource only
    supports GET requests with no body, and this endpoint needs a POST body
    (message, session_id, model).
    """
    start = time.perf_counter()
    logger.info("chat_stream_request_received", extra={
        "session_id": req.session_id,
        "message_length": len(req.message),
        "model": req.model,
    })

    db = SupabaseMemoryManager()
    session_history = db.fetch_chat_session(req.session_id)

    intent = route_intent(req.message)
    metadata = {"intent": intent}

    logger.info("intent_classified", extra={
        "session_id": req.session_id,
        "workflow": intent.get("workflow"),
    })

    yt = youtube_search(q=intent["yt_query"], max_results=2) if intent.get("needs_youtube") else []
    if yt: metadata["youtube"] = yt

    products = []
    if intent.get("needs_commerce"):
        commerce_bot = UniversalCommerceEngine()
        products = commerce_bot.search_all_platforms(intent["commerce_query"])
        metadata["marketplace_sourcing"] = products

    prompt = build_architectural_prompt(
        user=req.message,
        system_hint=intent.get("system_hint", ""),
        yt=yt,
        products=products,
        deep=req.deep_think
    )

    # Log the user's turn BEFORE opening the stream, so a mid-stream
    # disconnect still leaves the user's message persisted even if the
    # assistant's reply is incomplete.
    db.log_message(req.session_id, "user", req.message)

    # Instantiated outside the generator: if GROQ_API_KEY is missing, this
    # raises ValueError here, while headers haven't been sent yet, giving a
    # normal 500 instead of a broken half-open SSE stream.
    client = CloudLLMClient()

    async def event_generator():
        full_response_chunks = []
        token_count = 0
        try:
            async for delta in client.stream_with_history(
                prompt=prompt,
                history=session_history,
                model=req.model or "openai/gpt-oss-120b",
            ):
                if delta.startswith("[[STREAM_ERROR]]"):
                    logger.error("stream_upstream_error", extra={
                        "session_id": req.session_id,
                        "error": delta,
                    })
                    yield f"event: error\ndata: {json.dumps({'error': delta})}\n\n"
                    return
                full_response_chunks.append(delta)
                token_count += 1
                yield f"data: {json.dumps({'token': delta})}\n\n"
        finally:
            # Runs even on client disconnect (StreamingResponse closes the
            # generator via GeneratorExit) — so whatever was generated so
            # far still gets persisted to Supabase.
            assembled = "".join(full_response_chunks)
            if assembled:
                db.log_message(req.session_id, "assistant", assembled)

            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("chat_stream_request_completed", extra={
                "session_id": req.session_id,
                "token_count": token_count,
                "duration_ms": round(elapsed_ms, 2),
            })

        yield f"event: done\ndata: {json.dumps({'metadata': metadata})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevents any nginx layer in front of this service (e.g. the
            # frontend container's nginx, or a future reverse proxy) from
            # buffering the whole response before forwarding it, which
            # would defeat streaming entirely.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def build_architectural_prompt(user: str, system_hint: str, yt, products, deep: bool) -> str:
    context_blocks = []
    if system_hint:
        context_blocks.append(f"Operational Parameters: {system_hint}")
    if yt:
        ytxt = "\n".join([f"* Tutorial: {v['title']} -> {v['url']}" for v in yt])
        context_blocks.append("Supportive Reference Videos:\n" + ytxt)
    if products:
        ptxt = "\n".join([f"* [{p['source']}] {p['title']} -> URL: {p['url']}" for p in products])
        context_blocks.append("Verified Purchasing Context Matrices:\n" + ptxt)

    format_instruction = (
        "Generate a highly professional, scannable markdown resolution. When items, equipment, components, "
        "or books are referenced, explicitly weave direct clickable inline markdown hyperlinks "
        "(e.g., [Purchase this tracking component on Amazon](URL)) using the exact URLs provided in the Verified Purchasing Context list. "
        "Never alter the target URLs."
    ) if deep else "Provide immediate, high-impact tactical data points."

    preamble = textwrap.dedent(f"""
    You are SolGent, an elite workspace companion engineered to accelerate productivity patterns for students and enterprise personnel.
    {format_instruction}
    """).strip()

    context = "\n\n".join(context_blocks) if context_blocks else "(No auxiliary references loaded)"
    return f"{preamble}\n\nContext Layers:\n{context}\n\nUser Input: {user}\n\nProcessing Pipeline Execution:"