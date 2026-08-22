"""MiniMax provider adapter using the documented Anthropic-compatible API."""

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


def request_completion(*, system: str, messages: list[dict[str, object]]) -> MiniMaxReply:
    settings = get_settings()
    if not settings.minimax_api_key.strip():
        raise MiniMaxConfigurationError("MINIMAX_API_KEY is not configured")
    try:
        client = Anthropic(api_key=settings.minimax_api_key, base_url=settings.minimax_base_url)
        response = client.messages.create(
            model=settings.minimax_model,
            max_tokens=settings.ai_max_output_tokens,
            temperature=0.7,
            system=system,
            messages=messages,
            thinking={"type": "disabled"},
        )
    except Exception as error:  # Provider exceptions are intentionally not leaked to API clients.
        raise MiniMaxRequestError(type(error).__name__) from error

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
