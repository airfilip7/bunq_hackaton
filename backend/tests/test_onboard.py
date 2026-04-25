"""Tests for onboarding endpoints."""
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

DEV_HEADERS = {"X-Dev-User-Id": "user_test_123"}


def test_upload_url_unauthenticated():
    """No auth header → 401."""
    response = client.post("/onboard/upload-url")
    assert response.status_code == 401


def test_upload_url_returns_presigned_url():
    """With dev auth, returns expected response shape."""
    fake_url = "https://s3.example.com/presigned?sig=abc"
    fake_key = "payslip-imgs/user_test_123/abc123.jpg"

    with patch("backend.s3.presigned_put_url", return_value=(fake_url, fake_key)):
        response = client.post("/onboard/upload-url", headers=DEV_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"] == fake_url
    assert data["s3_key"] == fake_key
    assert data["required_headers"] == {"Content-Type": "image/jpeg"}
    assert "expires_at" in data


def test_extract_payslip_high_confidence():
    """Bedrock returns valid JSON → fields populated in response."""
    bedrock_payload = {
        "gross_monthly_eur": 5166.67,
        "net_monthly_eur": 3800.0,
        "employer_name": "ACME BV",
        "pay_period": "2026-03",
        "confidence": "high",
    }
    bedrock_response_body = json.dumps({
        "content": [{"text": json.dumps(bedrock_payload)}]
    }).encode()

    mock_bedrock = MagicMock()
    mock_bedrock.invoke_model.return_value = {
        "body": MagicMock(read=MagicMock(return_value=bedrock_response_body))
    }

    s3_key = "payslip-imgs/user_test_123/abc123.jpg"

    with patch("backend.s3.get_object_bytes", return_value=b"fake-image-bytes"), \
         patch("backend.payslip._get_bedrock_client", return_value=mock_bedrock), \
         patch("backend.dynamo.update_profile"):
        response = client.post(
            "/onboard/extract-payslip",
            json={"s3_key": s3_key},
            headers=DEV_HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["gross_monthly_eur"] == 5166.67
    assert data["net_monthly_eur"] == 3800.0
    assert data["employer_name"] == "ACME BV"
    assert data["pay_period"] == "2026-03"
    assert data["confidence"] == "high"
    assert data["source_s3_key"] == s3_key


def test_extract_payslip_bedrock_returns_garbage():
    """Bedrock returns non-JSON text → HTTP 200, all fields null, confidence 'low'."""
    garbage_body = json.dumps({
        "content": [{"text": "Sorry, I cannot read this image."}]
    }).encode()

    mock_bedrock = MagicMock()
    mock_bedrock.invoke_model.return_value = {
        "body": MagicMock(read=MagicMock(return_value=garbage_body))
    }

    s3_key = "payslip-imgs/user_test_123/bad.jpg"

    with patch("backend.s3.get_object_bytes", return_value=b"fake-image-bytes"), \
         patch("backend.payslip._get_bedrock_client", return_value=mock_bedrock), \
         patch("backend.dynamo.update_profile"):
        response = client.post(
            "/onboard/extract-payslip",
            json={"s3_key": s3_key},
            headers=DEV_HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] == "low"
    assert data["gross_monthly_eur"] is None
    assert data["net_monthly_eur"] is None
    assert data["employer_name"] is None
    assert data["pay_period"] is None


def test_extract_payslip_missing_s3_key():
    """Body without s3_key → 422 Unprocessable Entity."""
    response = client.post(
        "/onboard/extract-payslip",
        json={},
        headers=DEV_HEADERS,
    )
    assert response.status_code == 422
