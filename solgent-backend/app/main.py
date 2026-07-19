import textwrap
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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