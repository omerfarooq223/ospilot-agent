# OS Pilot Desktop App

OS Pilot can run as a normal desktop window through Tauri while keeping the React UI and FastAPI backend.

Prerequisites:

- Rust/Cargo installed from [rustup.rs](https://rustup.rs)
- Node dependencies installed in `frontend/`
- Python API dependencies installed in the project virtual environment

Development flow:

```bash
# Terminal 1
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run desktop:dev
```

The desktop shell opens OS Pilot in its own app window instead of a browser tab. The current scaffold expects the API to be running locally on port `8000`, the same as the web development flow.

The desktop shell uses the same backend-governed workflow as the web UI, including Plan & Approval, Safe Autopilot, quarantine, restore, weekly scan settings, and report export.

The app icon and browser tab icon use the speed mark stored in:

```text
frontend/public/favicon.png
frontend/public/os-pilot-icon.svg
frontend/public/os-pilot-icon.png
frontend/src-tauri/icons/
```

For a fully bundled production app, the next step is to package the Python API as a sidecar process and have Tauri start it automatically.
