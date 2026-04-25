"""Onboarding endpoints: presigned S3 upload URL and payslip extraction."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

import backend.payslip as payslip_module
import backend.s3 as s3
from backend.auth import get_current_user_id
from backend.payslip import PayslipExtract

router = APIRouter()


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_at: str
    required_headers: dict[str, str]


class ExtractPayslipRequest(BaseModel):
    s3_key: str


@router.post("/upload-url", response_model=UploadUrlResponse)
def upload_url(user_id: str = Depends(get_current_user_id)):
    img_id = uuid.uuid4().hex
    presigned_url, s3_key = s3.presigned_put_url(user_id, img_id)
    from backend.config import settings
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=settings.s3_presigned_expiry_seconds)
    ).isoformat()
    return UploadUrlResponse(
        upload_url=presigned_url,
        s3_key=s3_key,
        expires_at=expires_at,
        required_headers={"Content-Type": "image/jpeg"},
    )


@router.post("/extract-payslip", response_model=PayslipExtract)
def extract_payslip(
    request: ExtractPayslipRequest = Body(...),
    user_id: str = Depends(get_current_user_id),
):
    return payslip_module.extract_and_persist(user_id, request.s3_key)
