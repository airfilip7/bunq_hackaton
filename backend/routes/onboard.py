import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ulid import ULID

import backend.funda as funda_module
import backend.payslip as payslip_module
import backend.s3 as s3
from backend.auth import get_current_user_id
from backend.config import settings
from backend.deps import get_bunq_client, get_storage
from backend.funda import FundaFetchError
from backend.models import Payslip, Profile, Target, Turn
from backend.projection import compute_projection

router = APIRouter()


# ---------------------------------------------------------------------------
# /upload-url
# ---------------------------------------------------------------------------

class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_at: int
    required_headers: dict[str, str]


@router.post("/upload-url", response_model=UploadUrlResponse)
def upload_url(user_id: str = Depends(get_current_user_id)):
    img_id = uuid.uuid4().hex
    presigned_url, s3_key = s3.presigned_put_url(user_id, img_id)
    expires_at = int((datetime.now(timezone.utc) + timedelta(seconds=settings.s3_presigned_expiry_seconds)).timestamp() * 1000)
    return UploadUrlResponse(
        upload_url=presigned_url,
        s3_key=s3_key,
        expires_at=expires_at,
        required_headers={"Content-Type": "image/jpeg"},
    )


# ---------------------------------------------------------------------------
# /extract-payslip
# ---------------------------------------------------------------------------

class ExtractPayslipRequest(BaseModel):
    s3_key: str


@router.post("/extract-payslip")
def extract_payslip_endpoint(
    request: ExtractPayslipRequest,
    user_id: str = Depends(get_current_user_id),
):
    return payslip_module.extract_and_persist(user_id, request.s3_key)


# ---------------------------------------------------------------------------
# /parse-funda
# ---------------------------------------------------------------------------

class ParseFundaRequest(BaseModel):
    url: str


@router.post("/parse-funda")
async def parse_funda_endpoint(request: ParseFundaRequest):
    try:
        result = await funda_module.parse_funda(request.url)
        return result
    except FundaFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# /onboard  (main endpoint)
# ---------------------------------------------------------------------------

class OnboardRequest(BaseModel):
    s3_key: str
    funda_url: str
    funda_price_override_eur: float | None = None


class PayslipSnapshot(BaseModel):
    gross_monthly_eur: float
    net_monthly_eur: float
    confidence: Literal["high", "medium", "low"]


class TargetSnapshot(BaseModel):
    price_eur: float
    address: str


class ProjectionSnapshot(BaseModel):
    savings_now_eur: float
    deposit_target_eur: float
    gap_eur: float
    monthly_savings_eur: float
    months_to_goal: int
    headroom_range_eur: tuple[int, int]


class ProfileSnapshotResponse(BaseModel):
    payslip: PayslipSnapshot
    target: TargetSnapshot
    projection: ProjectionSnapshot


class OnboardResponse(BaseModel):
    session_id: str
    profile: ProfileSnapshotResponse


@router.post("", response_model=OnboardResponse)
async def onboard(
    request: OnboardRequest,
    user_id: str = Depends(get_current_user_id),
):
    # 1. Extract payslip from S3 via Bedrock vision
    try:
        payslip_extract = await asyncio.to_thread(payslip_module.extract_and_persist, user_id, request.s3_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Payslip extraction failed: {exc}") from exc

    # 2. Parse Funda listing
    try:
        funda_data = await funda_module.parse_funda(request.funda_url)
    except FundaFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 3. Determine property price
    price_eur = request.funda_price_override_eur if request.funda_price_override_eur is not None else funda_data.get("price_eur")
    if price_eur is None:
        raise HTTPException(status_code=422, detail="Could not determine property price — provide funda_price_override_eur")

    # 4. Pull bunq snapshot
    bunq = get_bunq_client()
    tx_result, buckets = await asyncio.gather(bunq.get_transactions(), bunq.get_buckets())
    transactions = tx_result.get("transactions", [])

    # 5. Build profile
    now_ms = int(time.time() * 1000)
    profile = Profile(
        user_id=user_id,
        onboarded_at=now_ms,
        payslip=Payslip(
            gross_monthly_eur=payslip_extract.gross_monthly_eur or 0.0,
            net_monthly_eur=payslip_extract.net_monthly_eur or 0.0,
            employer_name=payslip_extract.employer_name,
            pay_period=payslip_extract.pay_period,
            confidence=payslip_extract.confidence,
            source_s3_key=payslip_extract.source_s3_key,
        ),
        target=Target(
            funda_url=request.funda_url,
            price_eur=float(price_eur),
            address=funda_data.get("address") or "",
            type=funda_data.get("type"),
            size_m2=funda_data.get("size_m2"),
            year_built=funda_data.get("year_built"),
            fetched_at=now_ms,
        ),
    )

    # 6. Compute projection and attach
    projection = compute_projection(profile, transactions, buckets)
    profile.projection = projection

    # 7. Persist profile
    storage = get_storage()
    storage.upsert_profile(profile)

    # 8. Create session
    session = storage.create_session(user_id)

    # 9. Bootstrap hidden turn
    bootstrap_turn = Turn(
        turn_id=str(ULID()),
        session_id=session.session_id,
        ts_ms=int(time.time() * 1000),
        kind="user_message",
        content="<INTERNAL: profile bootstrapped>",
        hidden=True,
    )
    storage.append_turn(session.session_id, bootstrap_turn)

    # 10. Build and return response
    return OnboardResponse(
        session_id=session.session_id,
        profile=ProfileSnapshotResponse(
            payslip=PayslipSnapshot(
                gross_monthly_eur=profile.payslip.gross_monthly_eur or 0.0,
                net_monthly_eur=profile.payslip.net_monthly_eur or 0.0,
                confidence=profile.payslip.confidence,
            ),
            target=TargetSnapshot(
                price_eur=profile.target.price_eur,
                address=profile.target.address or "",
            ),
            projection=ProjectionSnapshot(
                savings_now_eur=projection.savings_now_eur,
                deposit_target_eur=projection.deposit_target_eur,
                gap_eur=projection.gap_eur,
                monthly_savings_eur=projection.monthly_savings_eur,
                months_to_goal=projection.months_to_goal,
                headroom_range_eur=projection.headroom_range_eur,
            ),
        ),
    )
