import io

from PIL import Image


def normalize_image(raw_bytes: bytes) -> tuple[bytes, str]:
    try:
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise ValueError("Unsupported image format") from exc

    # Strip EXIF by copying pixel data into a fresh RGB image
    img = img.convert("RGB")

    max_edge = 1568
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"
