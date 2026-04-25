# bunq Nest

Home-buying readiness coach built for bunq Hackathon 7.0. Photograph your payslip, paste a Funda link, see exactly how far you are from the house.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Chrome installed (used by Playwright for Funda scraping)
- AWS credentials configured (`~/.aws/credentials` or env vars) for Bedrock access

## Local setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Copy the env file and fill in your keys:

```bash
cp .env.example .env
```

Key settings:
- `BUNQ_MODE=fixture` — uses mock transaction data (no bunq API key needed)
- `FUNDA_MODE=fixture` — uses cached HTML fixtures (no network needed)
- `FUNDA_MODE=live` — fetches real Funda pages via Playwright

Start the server:

```bash
uvicorn backend.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Health check: `http://localhost:8000/health`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is now at `http://localhost:5173`.

### 3. Docker (recommended)

The easiest way to run everything:

```bash
cp .env.example .env
# Edit .env with your AWS credentials / bunq API key

docker compose up --build
```

This starts both services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

Source directories are mounted as volumes, so code changes are reflected immediately (backend auto-reloads, frontend has Vite HMR).

To stop:

```bash
docker compose down
```

To rebuild after dependency changes:

```bash
docker compose up --build
```

## Running tests

```bash
# All tests (skips live network tests)
pytest -m "not live"

# Include live Funda fetch tests (requires Chrome + internet)
pytest

# Just the Funda parser tests
pytest tests/test_funda.py -v
```