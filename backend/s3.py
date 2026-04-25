"""S3 client and presigned URL helpers."""
import boto3

from backend.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=settings.aws_region)
    return _client


def presigned_put_url(user_id: str, img_id: str, content_type: str = "image/jpeg", max_bytes: int = 10 * 1024 * 1024) -> tuple[str, str]:
    """Return (presigned_url, s3_key). Max 10 MB by default."""
    key = f"payslip-imgs/{user_id}/{img_id}.jpg"
    url = _get_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.s3_presigned_expiry_seconds,
    )
    return url, key


def get_object_bytes(key: str) -> bytes:
    resp = _get_client().get_object(Bucket=settings.s3_bucket, Key=key)
    return resp["Body"].read()
