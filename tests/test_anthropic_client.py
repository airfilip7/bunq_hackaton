"""Unit tests for backend/anthropic_client.py."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.anthropic_client import (
    MODEL_CHAT,
    MODEL_VISION,
    ExtractionError,
    extract_payslip,
    stream_chat,
)
from backend.prompts import VLM_PAYSLIP

_SAMPLE_PAYLOAD = {
    "gross_monthly_eur": 5166.67,
    "net_monthly_eur": 3800.0,
    "employer_name": "ACME BV",
    "pay_period": "2026-03",
    "confidence": "high",
}


def _make_response(text: str) -> MagicMock:
    """Build a fake Anthropic messages.create response with .content[0].text."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


@pytest.mark.asyncio
async def test_extract_payslip_clean_json():
    """Clean JSON in response text is parsed and returned as dict."""
    mock_create = AsyncMock(return_value=_make_response(json.dumps(_SAMPLE_PAYLOAD)))

    with patch("backend.anthropic_client.client") as mock_client:
        mock_client.messages.create = mock_create
        result = await extract_payslip(b"fake-image-bytes", "image/jpeg")

    assert result == _SAMPLE_PAYLOAD


@pytest.mark.asyncio
async def test_extract_payslip_json_fenced():
    """JSON wrapped in ```json fences is stripped and parsed correctly."""
    fenced = f"```json\n{json.dumps(_SAMPLE_PAYLOAD)}\n```"
    mock_create = AsyncMock(return_value=_make_response(fenced))

    with patch("backend.anthropic_client.client") as mock_client:
        mock_client.messages.create = mock_create
        result = await extract_payslip(b"fake-image-bytes", "image/jpeg")

    assert result == _SAMPLE_PAYLOAD


@pytest.mark.asyncio
async def test_extract_payslip_garbage():
    """Non-JSON response text raises ExtractionError."""
    mock_create = AsyncMock(
        return_value=_make_response("Sorry, I cannot read this image.")
    )

    with patch("backend.anthropic_client.client") as mock_client:
        mock_client.messages.create = mock_create
        with pytest.raises(ExtractionError):
            await extract_payslip(b"fake-image-bytes", "image/jpeg")


@pytest.mark.asyncio
async def test_extract_payslip_api_call_shape():
    """messages.create is called with the correct model, max_tokens, and message shape."""
    mock_create = AsyncMock(return_value=_make_response(json.dumps(_SAMPLE_PAYLOAD)))

    with patch("backend.anthropic_client.client") as mock_client:
        mock_client.messages.create = mock_create
        await extract_payslip(b"hello", "image/png")

    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args

    assert kwargs["model"] == MODEL_VISION
    assert kwargs["max_tokens"] == 1024

    messages = kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"

    content = messages[0]["content"]
    assert len(content) == 2

    image_block = content[0]
    assert image_block["type"] == "image"
    assert image_block["source"]["type"] == "base64"

    text_block = content[1]
    assert text_block["type"] == "text"
    assert text_block["text"] == VLM_PAYSLIP


@pytest.mark.asyncio
async def test_stream_chat_delegates_to_sdk():
    """stream_chat calls client.messages.stream with correct params and yields the stream."""
    mock_stream = MagicMock()
    captured: dict = {}

    @asynccontextmanager
    async def fake_stream_ctx(**kwargs):
        captured.update(kwargs)
        yield mock_stream

    system = "You are a coach."
    messages = [{"role": "user", "content": "Hello"}]
    tools = [{"name": "get_projection", "description": "...", "input_schema": {}}]

    with patch("backend.anthropic_client.client") as mock_client:
        mock_client.messages.stream = fake_stream_ctx

        async with stream_chat(system, messages, tools) as stream:
            assert stream is mock_stream

    assert captured["model"] == MODEL_CHAT
    assert captured["system"] == system
    assert captured["messages"] == messages
    assert captured["tools"] == tools
    assert captured["max_tokens"] == 4096
