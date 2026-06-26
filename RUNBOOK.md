# QueueStorm Investigator — Runbook

This runbook provides exact steps to install, test, and run the QueueStorm Investigator API.

## Repository

```text
https://github.com/thevintagecoder/SUST-Hackathon-2026
```

## Required Endpoints

The service exposes:

```text
GET  /health
POST /analyze-ticket
```

A successful health response is:

```json
{
  "status": "ok"
}
```

---

# Option A — Run Locally with Python

## Prerequisites

- Python 3.11 or newer
- Git
- Internet access for the initial dependency installation

No external AI API key is required.

## 1. Clone the repository

```bash
git clone https://github.com/thevintagecoder/SUST-Hackathon-2026.git
cd SUST-Hackathon-2026
```

## 2. Create a virtual environment

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Expected startup output includes:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

Leave this terminal running.

## 5. Test the health endpoint

Open another terminal:

```bash
curl -i http://127.0.0.1:8000/health
```

Expected status:

```text
HTTP/1.1 200 OK
```

Expected response:

```json
{ "status": "ok" }
```

## 6. Test ticket analysis

```bash
curl -sS \
  -X POST \
  http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data '{
    "ticket_id": "RUNBOOK-TEST-001",
    "complaint": "I sent 5000 taka to a wrong number.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-RUNBOOK-001",
        "timestamp": "2026-04-14T14:08:22Z",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "+8801719876543",
        "status": "completed"
      }
    ]
  }'
```

Important expected fields:

```json
{
  "ticket_id": "RUNBOOK-TEST-001",
  "relevant_transaction_id": "TXN-RUNBOOK-001",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "human_review_required": true
}
```

## 7. Open interactive API documentation

Open:

```text
http://127.0.0.1:8000/docs
```

---

# Option B — Run with Docker

## Prerequisites

- Docker Desktop or Docker Engine

No external API key is required.

## 1. Clone the repository

```bash
git clone https://github.com/thevintagecoder/SUST-Hackathon-2026.git
cd SUST-Hackathon-2026
```

## 2. Build the Docker image

```bash
docker build -t queuestorm-investigator:latest .
```

## 3. Run the container

```bash
docker run \
  --rm \
  --name queuestorm-api \
  -p 8000:8000 \
  queuestorm-investigator:latest
```

Expected output includes:

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

## 4. Test Docker health

In another terminal:

```bash
curl -i http://127.0.0.1:8000/health
```

Expected:

```json
{ "status": "ok" }
```

## 5. Check Docker health status

Wait approximately 10 seconds, then run:

```bash
docker inspect \
  --format='{{.State.Health.Status}}' \
  queuestorm-api
```

Expected:

```text
healthy
```

## 6. Stop the container

```bash
docker stop queuestorm-api
```

Because the container was started with `--rm`, it is removed automatically after stopping.

---

# Running Automated Tests

Activate the virtual environment first when running locally.

Run the full test suite:

```bash
python -m pytest -q
```

Run with detailed output:

```bash
python -m pytest -v
```

Run public-sample decision tests only:

```bash
python -m pytest -v -k "public_sample_decisions"
```

Run safety tests only:

```bash
python -m pytest tests/test_safety.py -v
```

Run request-validation and error-handling tests only:

```bash
python -m pytest tests/test_error_handling.py -v
```

---

# Generate the Required Sample Output

The repository already contains:

```text
samples/sample_output.json
```

To regenerate it from the real API implementation:

```bash
python -m scripts.generate_sample_output
```

The script sends the official `SAMPLE-01` input through the FastAPI application and saves the resulting response.

---

# Environment Variables

The current implementation does not require secrets, tokens, or external model API keys.

Optional configuration:

```env
PORT=8000
```

The example file is:

```text
.env.example
```

Do not commit a real `.env` file containing private values.

---

# Production Start Command

For platforms that supply a `PORT` environment variable:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For local execution:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

# Malformed-Input Verification

Send invalid JSON:

```bash
curl -i \
  -X POST \
  http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data '{"ticket_id":"BROKEN","complaint":'
```

Expected status:

```text
HTTP/1.1 400 Bad Request
```

Expected response:

```json
{
  "detail": "Invalid request body. Check the required fields, data types, and enum values."
}
```

Confirm that the service remains available:

```bash
curl http://127.0.0.1:8000/health
```

---

# Empty-Complaint Verification

```bash
curl -i \
  -X POST \
  http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  --data '{
    "ticket_id": "EMPTY-COMPLAINT",
    "complaint": "   "
  }'
```

Expected status:

```text
HTTP/1.1 422 Unprocessable Entity
```

---

# Troubleshooting

## Error: Could not import module `main`

Incorrect command:

```bash
uvicorn main:app --reload
```

Correct command:

```bash
uvicorn app.main:app --reload
```

The `main.py` file is inside the `app` package.

## Error: Port 8000 is already in use

Check which process is using it:

```bash
lsof -i :8000
```

Stop the existing server, or run on another host port.

For local Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

For Docker:

```bash
docker run \
  --rm \
  --name queuestorm-api \
  -p 8001:8000 \
  queuestorm-investigator:latest
```

Then test:

```bash
curl http://127.0.0.1:8001/health
```

## Error: Cannot connect to the Docker daemon

Start Docker Desktop or Docker Engine, wait until it is ready, then run:

```bash
docker info
```

## Error: Container name already exists

Remove the old container:

```bash
docker rm -f queuestorm-api
```

Then run the Docker command again.

## Error: Dependencies are missing

Activate the virtual environment and reinstall:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Verify installed dependencies

```bash
python -m pip check
```

Expected:

```text
No broken requirements found.
```

---

# Readiness Checklist

Before evaluation, confirm:

```bash
python -m pytest -q
```

Then verify:

```bash
curl http://127.0.0.1:8000/health
```

Required result:

```json
{ "status": "ok" }
```

The service is ready when:

- All automated tests pass
- `/health` returns HTTP 200
- `/analyze-ticket` returns structured JSON
- Invalid input returns controlled errors
- No secrets are required
- Docker reports the container as healthy
