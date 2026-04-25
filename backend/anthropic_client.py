"""Shared Anthropic Bedrock client for VLM extraction and the chat agent loop.

Uses AsyncAnthropicBedrock so all inference stays within AWS (eu-central-1).
"""

import base64
import json
import re
from contextlib import asynccontextmanager

from anthropic import AsyncAnthropicBedrock

from backend.config import settings
from backend.prompts import VLM_PAYSLIP

client = AsyncAnthropicBedrock(aws_region=settings.aws_region)

MODEL_VISION = settings.bedrock_vision_model
MODEL_CHAT = settings.bedrock_chat_model

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$")


class ExtractionError(Exception):
    """Raised when VLM output cannot be parsed as valid JSON."""


async def extract_payslip(image_bytes: bytes, media_type: str) -> dict:
    """Extract payslip fields via Claude vision on Bedrock.

    Returns a dict matching the VLM_PAYSLIP schema:
    {gross_monthly_eur, net_monthly_eur, employer_name, pay_period, confidence}
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = await client.messages.create(
        model=MODEL_VISION,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": VLM_PAYSLIP},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    cleaned = _JSON_FENCE_RE.sub("", raw_text.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            f"Failed to parse VLM response as JSON: {exc}\nRaw: {raw_text}"
        ) from exc


@asynccontextmanager
async def stream_chat(system: str, messages: list[dict], tools: list[dict]):
    """Open a streaming chat completion via Bedrock.

    Usage::

        async with stream_chat(system, messages, tools) as stream:
            async for event in stream:
                ...  # handle SDK events

    The caller (agent runner) is responsible for interpreting events
    (ContentBlockDeltaEvent, ContentBlockStartEvent, etc.).
    """
    async with client.messages.stream(
        model=MODEL_CHAT,
        system=system,
        messages=messages,
        tools=tools,
        max_tokens=4096,
    ) as stream:
        yield stream
