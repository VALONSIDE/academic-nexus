"""Provider routing; only final answer content enters public conversations."""
import json
from collections.abc import Iterator

import httpx

from app.core.config import get_settings
from app.services.ai import minimax
from app.services.ai.minimax import MiniMaxConfigurationError, MiniMaxRequestError, MiniMaxReply, MiniMaxStreamEvent


def _request(model: str, system: str, messages: list, stream: bool):
    provider, tier, name = model.split(":", 2)
    settings = get_settings()
    secret = getattr(settings, f"{provider}_api_key").get_secret_value()
    if not secret.strip():
        raise MiniMaxConfigurationError("provider_not_configured")
    url = getattr(settings, f"{provider}_base_url").rstrip("/") + "/chat/completions"
    body = {"model": name, "messages": [{"role": "system", "content": system}, *messages], "stream": stream}
    body["max_completion_tokens" if provider == "openai" else "max_tokens"] = settings.ai_max_output_tokens
    if provider == "deepseek":
        body["thinking"] = {"type": "disabled" if tier == "light" else "enabled"}
        if tier != "light":
            body["reasoning_effort"] = "high"
            body["max_tokens"] = max(8192, settings.ai_max_output_tokens)
    if stream:
        body["stream_options"] = {"include_usage": True}
    return url, {"Authorization": f"Bearer {secret}"}, body


def request_completion(*, model: str, system: str, messages: list) -> MiniMaxReply:
    if ":" not in model:
        return minimax.request_completion(model=model, system=system, messages=messages)
    if model.startswith("minimax:"):
        _, tier, name = model.split(":", 2)
        return minimax.request_completion(model=name, system=system, messages=messages, effort={"light": "low", "standard": "medium", "expert": "high"}[tier])
    url, headers, body = _request(model, system, messages, False)
    try:
        with httpx.Client(timeout=httpx.Timeout(180, connect=10), follow_redirects=False) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        content = choice["message"].get("content") or ""
        if choice.get("finish_reason") != "stop" or not content.strip():
            raise MiniMaxRequestError("incomplete_provider_response")
        usage = data.get("usage") or {}
        return MiniMaxReply(content.strip(), usage.get("prompt_tokens"), usage.get("completion_tokens"))
    except MiniMaxRequestError:
        raise
    except Exception as error:
        code = "provider_insufficient_balance" if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 402 else type(error).__name__
        raise MiniMaxRequestError(code) from error


def stream_completion(*, model: str, system: str, messages: list) -> Iterator[MiniMaxStreamEvent]:
    if ":" not in model:
        yield from minimax.stream_completion(model=model, system=system, messages=messages)
        return
    if model.startswith("minimax:"):
        _, tier, name = model.split(":", 2)
        yield from minimax.stream_completion(model=name, system=system, messages=messages, effort={"light": "low", "standard": "medium", "expert": "high"}[tier])
        return
    url, headers, body = _request(model, system, messages, True)
    try:
        usage = {}
        stopped = False
        has_text = False
        done = False
        with httpx.Client(timeout=httpx.Timeout(180, connect=10), follow_redirects=False) as client:
            with client.stream("POST", url, headers=headers, json=body) as response:
                response.raise_for_status()
                # SSE permits blank keepalives and multiline data records.
                lines = []
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        lines.append(line[5:].lstrip())
                    elif not line and lines:
                        raw = "\n".join(lines)
                        lines = []
                        if raw == "[DONE]":
                            done = True
                            break
                        event = json.loads(raw)
                        if event.get("error"):
                            raise MiniMaxRequestError("provider_error")
                        usage = event.get("usage") or usage
                        for choice in event.get("choices", []):
                            reason = choice.get("finish_reason")
                            if reason is not None:
                                if reason != "stop":
                                    raise MiniMaxRequestError("incomplete_provider_response")
                                stopped = True
                            text = (choice.get("delta") or {}).get("content")
                            if text:
                                has_text = True
                                yield MiniMaxStreamEvent(text=text)
        if not done or not stopped or not has_text:
            raise MiniMaxRequestError("incomplete_provider_response")
        yield MiniMaxStreamEvent(completed=True, input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"))
    except MiniMaxRequestError:
        raise
    except Exception as error:
        code = "provider_insufficient_balance" if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 402 else type(error).__name__
        raise MiniMaxRequestError(code) from error
