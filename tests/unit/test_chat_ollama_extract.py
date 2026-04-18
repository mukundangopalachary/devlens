from __future__ import annotations

from types import SimpleNamespace

from devlens.chat.service import _extract_chat_text, _extract_stream_token


def test_extract_chat_text_from_namespace_response() -> None:
    response = SimpleNamespace(
        message=SimpleNamespace(content="Hello from model\n"),
        response=None,
    )
    assert _extract_chat_text(response) == "Hello from model"


def test_extract_chat_text_from_dict_response() -> None:
    response = {"message": {"content": "Hi there\n"}}
    assert _extract_chat_text(response) == "Hi there"


def test_extract_stream_token_from_namespace_chunk() -> None:
    chunk = SimpleNamespace(message=SimpleNamespace(content="token"))
    assert _extract_stream_token(chunk) == "token"
