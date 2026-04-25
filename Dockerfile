# ── Backend ───────────────────────────────────────────────────────────────────
# Includes Playwright + Chromium for live Funda scraping
FROM python:3.11-slim AS backend-builder

WORKDIR /build

COPY pyproject.toml .
COPY backend/ backend/

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS backend

WORKDIR /app

COPY --from=backend-builder /install /usr/local
COPY backend/ backend/

# Install Playwright's bundled Chromium + system dependencies into a
# world-readable path so appuser can find it at runtime.
# (Google Chrome has no Linux ARM64 build)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium \
    && chmod -R o+rx /ms-playwright

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
