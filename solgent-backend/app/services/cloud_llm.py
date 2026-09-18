from openai import OpenAI
from app.config import settings


class CloudLLMClient:
    def __init__(self):
        self.base_url = "https://api.groq.com/openai/v1"
        self.api_key = settings.GROQ_API_KEY

        if not self.api_key:
            raise ValueError("CRITICAL FAILURE: GROQ_API_KEY environment parameter missing.")

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def generate_with_history(self, prompt: str, history: list, model: str = "llama-3.3-70b-versatile", max_tokens: int = 1200) -> str:
        """Runs high-complexity contextual inference completely offloaded inside remote cloud clusters."""
        formatted_messages = []
        for msg in history:
            formatted_messages.append({"role": msg.get("role"), "content": msg.get("content")})
        formatted_messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=0.4,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Distributed Inference Execution Error: {str(e)}"

    def stream_with_history(self, prompt: str, history: list, model: str = "llama-3.3-70b-versatile", max_tokens: int = 1200):
        """
        Yields incremental text deltas as they arrive from Groq's LPU cluster.

        This is a plain generator, not an async generator, because the openai
        SDK's default client is synchronous — each `next()` call blocks on a
        network read. FastAPI still handles this correctly under
        StreamingResponse by running the generator in a threadpool, so the
        main event loop stays free to serve other requests concurrently.
        Swapping to `AsyncOpenAI` + `async for` is a legitimate future
        optimization once this endpoint is under enough concurrent load that
        threadpool exhaustion (default: 40 threads in Starlette) becomes the
        bottleneck — worth watching for in the Stage 2 load test results.
        """
        formatted_messages = []
        for msg in history:
            formatted_messages.append({"role": msg.get("role"), "content": msg.get("content")})
        formatted_messages.append({"role": "user", "content": prompt})

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=0.4,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            yield f"[[STREAM_ERROR]] {str(e)}"