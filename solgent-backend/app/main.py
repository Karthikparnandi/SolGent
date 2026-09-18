import json
import textwrap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
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

@app.get("/health")
def health_check():
    return {"status": "healthy", "architecture": "clean-slate-v4", "persistence": "supabase"}

@app.post("/chat", response_model=ChatResponse)
def handle_workspace_transaction(req: ChatRequest):
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
    client = CloudLLMClient()
    answer = client.generate_with_history(
        prompt=prompt,
        history=session_history,
        model=req.model or "llama-3.3-70b-versatile"
    )

    # 7. Sync the transaction record data back into Supabase tables
    db.log_message(req.session_id, "user", req.message)
    db.log_message(req.session_id, "assistant", answer)

    metadata["provider"] = "groq-serverless-cloud"
    return ChatResponse(answer=answer, used_metadata=metadata)


@app.post("/chat/stream")
def handle_workspace_transaction_stream(req: ChatRequest):
    """
    SSE variant of /chat. Consumed via `fetch()` + a ReadableStream reader on
    the frontend, NOT the browser's native EventSource API — EventSource only
    supports GET requests with no body, and this endpoint needs a POST body
    (message, session_id, model). That's a deliberate, standard tradeoff for
    chat-style SSE (ChatGPT, Claude.ai, etc. all do the same thing): you get
    SSE's simple `data: ...\\n\\n` framing without giving up the ability to
    send a structured request body.
    """
    db = SupabaseMemoryManager()
    session_history = db.fetch_chat_session(req.session_id)

    intent = route_intent(req.message)
    metadata = {"intent": intent}

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

    # Log the user's turn BEFORE opening the stream. If the client
    # disconnects mid-generation (closed tab, network drop), the user's
    # message is still recorded — losing only the assistant's reply, not
    # the whole turn. Losing both would silently desync session_history
    # from what the user actually sees they sent.
    db.log_message(req.session_id, "user", req.message)

    # Instantiated outside the generator, not inside: if GROQ_API_KEY is
    # missing, this raises ValueError here, and FastAPI returns a normal
    # 500 with headers not yet sent. If it were instantiated inside the
    # generator instead, the failure would happen AFTER we've already
    # committed to a 200 + text/event-stream response, which is a much
    # worse failure mode for a client trying to parse SSE frames.
    client = CloudLLMClient()

    def event_generator():
        full_response_chunks = []
        try:
            for delta in client.stream_with_history(
                prompt=prompt,
                history=session_history,
                model=req.model or "llama-3.3-70b-versatile",
            ):
                if delta.startswith("[[STREAM_ERROR]]"):
                    yield f"event: error\ndata: {json.dumps({'error': delta})}\n\n"
                    return
                full_response_chunks.append(delta)
                yield f"data: {json.dumps({'token': delta})}\n\n"
        finally:
            # Runs even on client disconnect (StreamingResponse closes the
            # generator via GeneratorExit) — so a user who closes the tab
            # mid-answer still gets whatever was generated so far persisted
            # to Supabase, keeping session_history consistent for their next
            # message instead of silently dropping the assistant's turn.
            assembled = "".join(full_response_chunks)
            if assembled:
                db.log_message(req.session_id, "assistant", assembled)

        yield f"event: done\ndata: {json.dumps({'metadata': metadata})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disables response buffering on any nginx layer sitting in
            # front of this service (e.g. if you later put this backend
            # behind an nginx reverse proxy or an ingress controller that
            # uses nginx under the hood — the Stage 1 frontend Dockerfile
            # already introduced nginx into this stack). Without this,
            # nginx can buffer the whole response before forwarding it,
            # which defeats streaming entirely and the client just sees
            # one big delayed chunk.
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