from fastapi import APIRouter, HTTPException, UploadFile

from backend.anthropic_client import ExtractionError, extract_payslip
from backend.image_utils import normalize_image
from backend.number_utils import normalize_dutch_numbers

router = APIRouter()


@router.post("/upload-payslip")
async def upload_payslip(file: UploadFile):
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are accepted")

    raw_bytes = await file.read()

    try:
        image_bytes, media_type = normalize_image(raw_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await extract_payslip(image_bytes, media_type)
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = normalize_dutch_numbers(result)
    confidence = result.pop("confidence", "low")
    return {"payslip": result, "confidence": confidence}
