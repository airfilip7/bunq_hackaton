"""Payslip extraction: read from S3, invoke Bedrock vision, persist to DynamoDB."""
import base64
import json
import logging
from datetime import datetime, timezone

import boto3
from pydantic import BaseModel

import backend.dynamo as dynamo
import backend.s3 as s3
from backend.config import settings
from backend.prompts import VLM_PAYSLIP as PAYSLIP_EXTRACT_PROMPT

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    return _bedrock_client


class PayslipExtract(BaseModel):
    gross_monthly_eur: float | None = None
    net_monthly_eur: float | None = None
    employer_name: str | None = None
    pay_period: str | None = None
    confidence: str = "low"
    source_s3_key: str | None = None
    extracted_at: str | None = None


def _detect_media_type(image_bytes: bytes, s3_key: str) -> str:
    """Detect image media type from magic bytes, falling back to the S3 key extension."""
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if s3_key.lower().endswith(".png"):
        return "image/png"
    return "image/jpeg"


def extract_and_persist(user_id: str, s3_key: str) -> PayslipExtract:
    """Read image from S3, extract fields via Bedrock vision, persist to DynamoDB."""
    image_bytes = s3.get_object_bytes(s3_key)
    b64_data = base64.b64encode(image_bytes).decode("utf-8")
    media_type = _detect_media_type(image_bytes, s3_key)

    request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {"type": "text", "text": PAYSLIP_EXTRACT_PROMPT},
            ],
        }],
    })

    response = _get_bedrock_client().invoke_model(
        modelId=settings.bedrock_vision_model,
        body=request_body,
        contentType="application/json",
        accept="application/json",
    )
    raw_text = json.loads(response["body"].read())["content"][0]["text"]

    extracted_at = datetime.now(timezone.utc).isoformat()

    try:
        data = json.loads(raw_text)
        extract = PayslipExtract(
            gross_monthly_eur=data.get("gross_monthly_eur"),
            net_monthly_eur=data.get("net_monthly_eur"),
            employer_name=data.get("employer_name"),
            pay_period=data.get("pay_period"),
            confidence=data.get("confidence", "low"),
            source_s3_key=s3_key,
            extracted_at=extracted_at,
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Bedrock returned unparseable JSON for key %s: %s", s3_key, exc)
        extract = PayslipExtract(
            source_s3_key=s3_key,
            extracted_at=extracted_at,
        )

    dynamo.update_profile(user_id, {"payslip": extract.model_dump()})
    return extract