from types import SimpleNamespace

from app.services.ai import minimax


def test_stream_completion_emits_public_text_but_not_provider_thinking(monkeypatch) -> None:
    chunks = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(usage=SimpleNamespace(input_tokens=12)),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="thinking_delta", thinking="internal reasoning"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="A practical next step is "),
        ),
        SimpleNamespace(
            type="content_block_delta",
            delta=SimpleNamespace(type="text_delta", text="to outline your research question."),
        ),
        SimpleNamespace(
            type="message_delta",
            usage=SimpleNamespace(output_tokens=9),
        ),
    ]
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_: chunks))
    monkeypatch.setattr(minimax, "_client", lambda: client)

    events = list(
        minimax.stream_completion(
            system="You are helpful.",
            messages=[{"role": "user", "content": [{"type": "text", "text": "Help me plan."}]}],
            model="MiniMax-M2.7",
        )
    )

    assert "".join(event.text for event in events) == "A practical next step is to outline your research question."
    assert events[-1].completed is True
    assert events[-1].input_tokens == 12
    assert events[-1].output_tokens == 9
