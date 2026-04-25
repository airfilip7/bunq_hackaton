# ── Backend ───────────────────────────────────────────────────────────────────
# Includes Playwright + Chromium for live Funda scraping
FROM python:3.11-slim AS backend-builder

WORKDIR /build

COPY pyproject.toml .
COPY backend/ backend/

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS backend

WORKDIR /app

# Playwright/Chromium system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 \
    libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    libu2f-udev libvulkan1 libxkbcommon0 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /install /usr/local
COPY backend/ backend/

# Install Playwright browsers (as root, before switching user)
RUN playwright install chromium

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
