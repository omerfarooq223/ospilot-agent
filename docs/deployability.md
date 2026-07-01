# Deployability

OS Pilot is designed to be reproducible locally for judging and packageable as a desktop app.

## Local Web App

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Desktop Shell

The Tauri shell opens the same React UI as a normal desktop window while the Python API runs locally on port `8000`.

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

```bash
cd frontend
npm run desktop:dev
```

Build command:

```bash
cd frontend
npm run desktop:build
```

## Deployment Boundary

OS Pilot intentionally runs local-first because it scans user-selected folders and quarantines local files. The project is therefore submitted as a reproducible local app rather than a public hosted endpoint. No API keys are required for deterministic fallback mode, and `.env.example` contains no secrets.
