from openai import AsyncOpenAI
from app.config import settings


class CloudLLMClient:
    def __init__(self):
        self.base_url = "https://api.groq.com/openai/v1"
        self.api_key = settings.GROQ_API_KEY

        if not self.api_key:
            raise ValueError("CRITICAL FAILURE: GROQ_API_KEY environment parameter missing.")

        # AsyncOpenAI allows non-blocking asynchronous socket reads directly on
        # FastAPI's asyncio event loop, bypassing threadpool constraints.
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    async def generate_with_history(
        self,
        prompt: str,
        history: list,
        model: str = "openai/gpt-oss-120b",
        max_tokens: int = 1200,
    ) -> str:
        """Runs contextual inference offloaded to remote cloud clusters."""
        formatted_messages = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in history
        ]
        formatted_messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=0.4,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Distributed Inference Execution Error: {str(e)}"

    async def stream_with_history(
        self,
        prompt: str,
        history: list,
        model: str = "openai/gpt-oss-120b",
        max_tokens: int = 1200,
    ):
        """
        Asynchronously yields incremental text deltas as they arrive from the cluster.

        Using AsyncOpenAI and an async generator allows the socket wait to yield
        control back to the event loop rather than blocking a worker thread in
        Starlette's default threadpool (capped at 40 threads). This enables the
        single process to interleave hundreds of concurrent streaming sessions.
        """
        formatted_messages = [
            {"role": msg.get("role"), "content": msg.get("content")}
            for msg in history
        ]
        formatted_messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=0.4,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"[[STREAM_ERROR]] {str(e)}"