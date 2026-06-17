import hashlib
import math
import re
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings


VECTOR_SIZE = 256
LOCAL_PROVIDER = "local_hash"
LOCAL_MODEL = "hashing-256"
_EMBEDDING_CACHE: dict[tuple[str, str, str], list[float]] = {}
_DISABLED_LIVE_PROVIDERS: dict[tuple[str, str], str] = {}


@dataclass(frozen=True)
class SimilarityResult:
    score: float
    provider: str
    model: str
    live: bool
    fallbackReason: str | None = None


def embed_text(text: str) -> list[float]:
    return _local_embed_text(text)


def semantic_similarity(left: str, right: str) -> SimilarityResult:
    settings = get_settings()
    provider, model, api_key = _resolve_provider(settings)
    if provider == "local":
        return SimilarityResult(
            score=_cosine_vectors(_local_embed_text(left), _local_embed_text(right)),
            provider=LOCAL_PROVIDER,
            model=LOCAL_MODEL,
            live=False,
            fallbackReason="No live embedding provider is configured.",
        )
    disabled_reason = _DISABLED_LIVE_PROVIDERS.get((provider, model))
    if disabled_reason:
        return SimilarityResult(
            score=_cosine_vectors(_local_embed_text(left), _local_embed_text(right)),
            provider=LOCAL_PROVIDER,
            model=LOCAL_MODEL,
            live=False,
            fallbackReason=disabled_reason,
        )

    try:
        left_vector = _embed_live(left, provider=provider, model=model, api_key=api_key, settings=settings)
        right_vector = _embed_live(right, provider=provider, model=model, api_key=api_key, settings=settings)
        return SimilarityResult(
            score=_cosine_vectors(left_vector, right_vector),
            provider=provider,
            model=model,
            live=True,
        )
    except httpx.HTTPError as exc:
        if not settings.embedding_fallback_local:
            raise
        fallback_reason = f"{provider} embedding request failed: {exc}"
        _DISABLED_LIVE_PROVIDERS[(provider, model)] = fallback_reason
        return SimilarityResult(
            score=_cosine_vectors(_local_embed_text(left), _local_embed_text(right)),
            provider=LOCAL_PROVIDER,
            model=LOCAL_MODEL,
            live=False,
            fallbackReason=fallback_reason,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if not settings.embedding_fallback_local:
            raise
        fallback_reason = f"{provider} embedding response could not be parsed: {exc}"
        _DISABLED_LIVE_PROVIDERS[(provider, model)] = fallback_reason
        return SimilarityResult(
            score=_cosine_vectors(_local_embed_text(left), _local_embed_text(right)),
            provider=LOCAL_PROVIDER,
            model=LOCAL_MODEL,
            live=False,
            fallbackReason=fallback_reason,
        )


def cosine_similarity(left: str, right: str) -> float:
    return semantic_similarity(left, right).score


def local_cosine_similarity(left: str, right: str) -> float:
    return _cosine_vectors(_local_embed_text(left), _local_embed_text(right))


def _local_embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    tokens = _tokens(text)
    features = []
    features.extend(tokens)
    features.extend(" ".join(tokens[index : index + 2]) for index in range(max(0, len(tokens) - 1)))
    features.extend(_char_ngrams(" ".join(tokens), size=4))

    for feature in features:
        index = _stable_index(feature)
        vector[index] += 1.0

    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def _resolve_provider(settings: Settings) -> tuple[str, str, str]:
    provider = settings.embedding_provider
    if provider == "auto":
        if settings.llm_provider == "gemini" and _gemini_api_key(settings):
            provider = "gemini"
        elif settings.llm_provider == "openai" and _openai_api_key(settings):
            provider = "openai"
        elif _gemini_api_key(settings):
            provider = "gemini"
        elif _openai_api_key(settings):
            provider = "openai"
        else:
            provider = "local"

    if provider == "gemini":
        return provider, settings.embedding_model or "gemini-embedding-2", _gemini_api_key(settings)
    if provider == "openai":
        return provider, settings.embedding_model or "text-embedding-3-small", _openai_api_key(settings)
    return "local", LOCAL_MODEL, ""


def _embed_live(text: str, provider: str, model: str, api_key: str, settings: Settings) -> list[float]:
    if not api_key:
        raise ValueError(f"Missing API key for embedding provider: {provider}")

    cache_key = (provider, model, text)
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]

    if provider == "gemini":
        vector = _embed_gemini(text, model=model, api_key=api_key, settings=settings)
    elif provider == "openai":
        vector = _embed_openai(text, model=model, api_key=api_key, settings=settings)
    else:
        vector = _local_embed_text(text)

    _EMBEDDING_CACHE[cache_key] = _normalize_vector(vector)
    return _EMBEDDING_CACHE[cache_key]


def _embed_gemini(text: str, model: str, api_key: str, settings: Settings) -> list[float]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    payload: dict[str, object] = {
        "model": f"models/{model}",
        "content": {
            "parts": [
                {
                    "text": _gemini_embedding_text(text, model),
                }
            ]
        },
    }
    if model == "gemini-embedding-001":
        payload["taskType"] = "SEMANTIC_SIMILARITY"

    with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
        response = client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json=payload,
        )
        response.raise_for_status()

    return _parse_gemini_embedding(response.json())


def _embed_openai(text: str, model: str, api_key: str, settings: Settings) -> list[float]:
    with httpx.Client(timeout=settings.embedding_timeout_seconds) as client:
        response = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": text,
                "encoding_format": "float",
            },
        )
        response.raise_for_status()

    return response.json()["data"][0]["embedding"]


def _parse_gemini_embedding(data: dict[str, object]) -> list[float]:
    if "embedding" in data:
        embedding = data["embedding"]
        if isinstance(embedding, dict):
            return list(embedding["values"])

    if "embeddings" in data:
        embeddings = data["embeddings"]
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, dict):
                if "values" in first:
                    return list(first["values"])
                if "embedding" in first and isinstance(first["embedding"], dict):
                    return list(first["embedding"]["values"])

    raise ValueError("Gemini embedding response did not include vector values")


def _gemini_embedding_text(text: str, model: str) -> str:
    if model == "gemini-embedding-001":
        return text
    return f"task: sentence similarity | query: {text}"


def _gemini_api_key(settings: Settings) -> str:
    return settings.gemini_api_key or settings.google_api_key or (
        settings.llm_api_key if settings.llm_provider == "gemini" else ""
    )


def _openai_api_key(settings: Settings) -> str:
    return settings.openai_api_key or (
        settings.llm_api_key if settings.llm_provider == "openai" else ""
    )


def _cosine_vectors(left_vector: list[float], right_vector: list[float]) -> float:
    if not left_vector or not right_vector or len(left_vector) != len(right_vector):
        return 0.0
    return sum(left_value * right_value for left_value, right_value in zip(left_vector, right_vector))


def _normalize_vector(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    normalized = normalized.replace("ci/cd", "cicd")
    normalized = normalized.replace("c#", "csharp")
    return re.findall(r"[a-z0-9+#.]+", normalized)


def _char_ngrams(text: str, size: int) -> list[str]:
    compact = re.sub(r"\s+", " ", text.strip())
    if len(compact) < size:
        return [compact] if compact else []
    return [compact[index : index + size] for index in range(len(compact) - size + 1)]


def _stable_index(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % VECTOR_SIZE
