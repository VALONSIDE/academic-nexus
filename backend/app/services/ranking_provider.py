"""Strict SiliconFlow free-model adapter. Never log request bodies or credentials."""

import json
import math
import time

import httpx

from app.core.config import get_settings

DIMENSIONS = 1024


class RankingProviderError(RuntimeError):
    pass


def _post(endpoint: str, payload: dict, deadline: float) -> dict:
    settings = get_settings()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RankingProviderError("deadline_exceeded")
    base_url = settings.siliconflow_base_url.rstrip("/")
    if base_url != "https://api.siliconflow.cn/v1":
        raise RankingProviderError("unsupported_provider_url")
    key = settings.siliconflow_api_key.get_secret_value().strip()
    if not key:
        raise RankingProviderError("not_configured")
    try:
        with httpx.Client(timeout=min(remaining, 10), follow_redirects=False) as client:
            with client.stream("POST", f"{base_url}/{endpoint}",
                               headers={"Authorization": f"Bearer {key}"}, json=payload) as response:
                if response.status_code != 200:
                    raise RankingProviderError(f"provider_http_{response.status_code}")
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > 2_000_000 or time.monotonic() > deadline:
                        raise RankingProviderError("response_limit_exceeded")
                body = json.loads(chunks)
                if not isinstance(body, dict):
                    raise RankingProviderError("invalid_response")
                return body
    except (httpx.HTTPError, ValueError):
        # Exceptions may contain provider response bodies: expose only a fixed code.
        raise RankingProviderError("provider_unavailable") from None


def embeddings(texts: list[str], deadline: float) -> list[list[float]]:
    body = _post("embeddings", {"model": get_settings().siliconflow_embedding_model,
                              "input": texts, "encoding_format": "float"}, deadline)
    try:
        data = body["data"]
        if len(data) != len(texts):
            raise ValueError
        result = [None] * len(texts)
        for row in data:
            index, vector = row["index"], row["embedding"]
            if type(index) is not int or not 0 <= index < len(texts) or result[index] is not None:
                raise ValueError
            if len(vector) != DIMENSIONS or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
                raise ValueError
            norm = math.sqrt(sum(value * value for value in vector))
            if not math.isfinite(norm) or norm <= 0:
                raise ValueError
            result[index] = [float(value / norm) for value in vector]
        return result
    except (KeyError, TypeError, ValueError, OverflowError):
        raise RankingProviderError("invalid_embeddings") from None


def rerank(query: str, documents: list[str], deadline: float) -> list[float]:
    body = _post("rerank", {"model": get_settings().siliconflow_rerank_model,
                           "query": query, "documents": documents, "top_n": len(documents),
                           "return_documents": False, "max_chunks_per_doc": 1}, deadline)
    try:
        rows = body["results"]
        if len(rows) != len(documents):
            raise ValueError
        scores = [None] * len(documents)
        for row in rows:
            index, score = row["index"], row["relevance_score"]
            if type(index) is not int or not 0 <= index < len(documents) or scores[index] is not None:
                raise ValueError
            if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError
            scores[index] = float(score)
        return scores
    except (KeyError, TypeError, ValueError):
        raise RankingProviderError("invalid_rerank") from None
