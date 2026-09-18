import hashlib
import math
import re
from openai import AsyncOpenAI
from app.config import get_settings


def client() -> AsyncOpenAI:
    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=s.openai_api_key, base_url=s.openai_base_url)


async def embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    if s.embedding_provider.lower() == "local":
        return [_local_embedding(text, s.embedding_dimensions) for text in texts]
    result: list[list[float]] = []
    # Bound request size for large uploads; API limits vary by embedding provider.
    for offset in range(0, len(texts), 96):
        response = await client().embeddings.create(model=s.embedding_model, input=texts[offset:offset + 96], dimensions=s.embedding_dimensions)
        result.extend(item.embedding for item in response.data)
    return result


def _local_embedding(text: str, dimensions: int) -> list[float]:
    """Deterministic, dependency-free smoke-test embedding (not for production quality)."""
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9_]+", text.lower())
    for token in tokens:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1 if digest[4] & 1 else -1
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / magnitude for value in vector]


async def complete(system: str, user: str, temperature: float = 0.1) -> str:
    s = get_settings()
    response = await client().chat.completions.create(
        model=s.chat_model,
        temperature=temperature,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content or "I could not generate an answer."
