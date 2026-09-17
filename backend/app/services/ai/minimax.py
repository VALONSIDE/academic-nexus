"""MiniMax provider adapter using the documented Anthropic-compatible API."""

from collections.abc import Iterator
from dataclasses import dataclass

from anthropic import Anthropic

from app.core.config import get_settings


class MiniMaxConfigurationError(RuntimeError):
    pass


class MiniMaxRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class MiniMaxReply:
    content: str
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class MiniMaxStreamEvent:
    text: str = ""
    completed: bool = False
    input_tokens: int | None = None
    output_tokens: int | None = None


def _client() -> Anthropic:
    settings = get_settings()
    if not settings.minimax_api_key.strip():
        raise MiniMaxConfigurationError("MINIMAX_API_KEY is not configured")
    return Anthropic(api_key=settings.minimax_api_key, base_url=settings.minimax_base_url, timeout=120.0, max_retries=0)


def request_completion(*, system: str, messages: list[dict[str, object]], model: str) -> MiniMaxReply:
    settings = get_settings()
    client = _client()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=settings.ai_max_output_tokens,
            temperature=0.7,
            system=system,
            messages=messages,
            thinking={"type": "disabled"},
        )
    except Exception as error:  # Provider exceptions are intentionally not leaked to API clients.
        raise MiniMaxRequestError(type(error).__name__) from error
    finally:
        client.close()

    text_blocks = [getattr(block, "text", "") for block in response.content if getattr(block, "type", "") == "text"]
    content = "\n".join(block for block in text_blocks if block).strip()
    if not content:
        raise MiniMaxRequestError("empty_provider_response")
    usage = getattr(response, "usage", None)
    return MiniMaxReply(
        content=content,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
    )


def stream_completion(*, system: str, messages: list[dict[str, object]], model: str) -> Iterator[MiniMaxStreamEvent]:
    """Yield public text deltas only; provider reasoning is never exposed to the client."""
    settings = get_settings()
    client = None
    stream = None
    try:
        client = _client()
        stream = client.messages.create(
            model=model,
            max_tokens=settings.ai_max_output_tokens,
            temperature=0.7,
            system=system,
            messages=messages,
            thinking={"type": "disabled"},
            stream=True,
        )
        has_text = False
        stopped = False
        input_tokens: int | None = None
        output_tokens: int | None = None
        for chunk in stream:
            chunk_type = getattr(chunk, "type", "")
            if chunk_type == "message_start":
                usage = getattr(getattr(chunk, "message", None), "usage", None)
                input_tokens = getattr(usage, "input_tokens", input_tokens)
            elif chunk_type == "message_delta":
                usage = getattr(chunk, "usage", None)
                output_tokens = getattr(usage, "output_tokens", output_tokens)
            elif chunk_type == "content_block_delta":
                delta = getattr(chunk, "delta", None)
                text = getattr(delta, "text", "") if getattr(delta, "type", "") == "text_delta" else ""
                if text:
                    has_text = True
                    yield MiniMaxStreamEvent(text=text)
            elif chunk_type == "message_stop":
                stopped = True
        if not stopped:
            raise MiniMaxRequestError("incomplete_provider_response")
        if not has_text:
            raise MiniMaxRequestError("empty_provider_response")
        yield MiniMaxStreamEvent(completed=True, input_tokens=input_tokens, output_tokens=output_tokens)
    except MiniMaxConfigurationError:
        raise
    except MiniMaxRequestError:
        raise
    except Exception as error:  # Provider exceptions are intentionally not leaked to API clients.
        raise MiniMaxRequestError(type(error).__name__) from error
    finally:
        try:
            if stream is not None:
                stream.close()
        finally:
            if client is not None:
                client.close()
