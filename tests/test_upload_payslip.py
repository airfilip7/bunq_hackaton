"""Tests for image_utils, number_utils, and the /onboard/upload-payslip endpoint."""

import io
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.anthropic_client import ExtractionError
from backend.image_utils import normalize_image
from backend.main import app
from backend.number_utils import normalize_dutch_numbers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_bytes(width: int, height: int, fmt: str = "JPEG") -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_image_with_exif() -> bytes:
    """Create a JPEG with minimal EXIF data."""
    img = Image.new("RGB", (200, 200), color=(10, 20, 30))
    buf = io.BytesIO()
    # piexif isn't a dependency; instead use PIL's built-in EXIF injection
    # We embed raw EXIF bytes to verify stripping works.
    exif_bytes = b"Exif\x00\x00II*\x00\x08\x00\x00\x00"  # minimal EXIF header
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# image_utils tests
# ---------------------------------------------------------------------------

def test_normalize_image_resize():
    raw = _make_image_bytes(3000, 2000)
    out_bytes, media_type = normalize_image(raw)
    out_img = Image.open(io.BytesIO(out_bytes))
    assert max(out_img.size) == 1568
    assert media_type == "image/jpeg"


def test_normalize_image_small_passthrough():
    raw = _make_image_bytes(800, 600)
    out_bytes, _ = normalize_image(raw)
    out_img = Image.open(io.BytesIO(out_bytes))
    assert out_img.size == (800, 600)


def test_normalize_image_jpeg_output():
    raw = _make_image_bytes(400, 300, fmt="PNG")
    out_bytes, media_type = normalize_image(raw)
    assert out_bytes[:2] == b"\xff\xd8"
    assert media_type == "image/jpeg"


def test_normalize_image_strips_exif():
    raw = _make_image_with_exif()
    out_bytes, _ = normalize_image(raw)
    out_img = Image.open(io.BytesIO(out_bytes))
    exif_data = out_img.info.get("exif", b"")
    assert exif_data == b""


def test_normalize_image_bad_bytes():
    with pytest.raises(ValueError, match="Unsupported image format"):
        normalize_image(b"not an image at all")


# ---------------------------------------------------------------------------
# number_utils tests
# ---------------------------------------------------------------------------

def test_dutch_number_string():
    data = {"gross_monthly_eur": "4.850,00", "net_monthly_eur": "3.200,50"}
    result = normalize_dutch_numbers(data)
    assert result["gross_monthly_eur"] == 4850.0
    assert result["net_monthly_eur"] == 3200.5


def test_already_float():
    data = {"gross_monthly_eur": 4850.0}
    result = normalize_dutch_numbers(data)
    assert result["gross_monthly_eur"] == 4850.0


def test_none_passthrough():
    data = {"gross_monthly_eur": None}
    result = normalize_dutch_numbers(data)
    assert result["gross_monthly_eur"] is None


def test_other_keys_untouched():
    data = {"employer_name": "ACME", "confidence": "high"}
    result = normalize_dutch_numbers(data)
    assert result == {"employer_name": "ACME", "confidence": "high"}


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

_SAMPLE_VLM_RESULT = {
    "gross_monthly_eur": 5166.67,
    "net_monthly_eur": 3800.0,
    "employer_name": "ACME BV",
    "pay_period": "2026-03",
    "confidence": "high",
}

client = TestClient(app)


def test_upload_payslip_happy_path():
    image_bytes = _make_image_bytes(400, 300)

    with patch(
        "backend.routes.onboard.extract_payslip",
        new=AsyncMock(return_value=dict(_SAMPLE_VLM_RESULT)),
    ):
        resp = client.post(
            "/onboard/upload-payslip",
            files={"file": ("payslip.jpg", image_bytes, "image/jpeg")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "payslip" in body
    assert "confidence" in body
    assert body["confidence"] == "high"
    assert body["payslip"]["gross_monthly_eur"] == 5166.67
    assert "confidence" not in body["payslip"]


def test_upload_payslip_bad_content_type():
    resp = client.post(
        "/onboard/upload-payslip",
        files={"file": ("data.csv", b"a,b,c", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_payslip_extraction_error():
    image_bytes = _make_image_bytes(400, 300)

    with patch(
        "backend.routes.onboard.extract_payslip",
        new=AsyncMock(side_effect=ExtractionError("VLM returned garbage")),
    ):
        resp = client.post(
            "/onboard/upload-payslip",
            files={"file": ("payslip.jpg", image_bytes, "image/jpeg")},
        )

    assert resp.status_code == 422
