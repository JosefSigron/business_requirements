# Licensing Assistant — FastAPI + React 19

An end-to-end demo that parses restaurant licensing requirements (Hebrew source), structures them to JSON/CSV, matches them to a business profile, and generates an AI-assisted report.

## Stack
- Backend: FastAPI (Python)
- Frontend: React 19 + Vite
- Parser: `python-docx` to convert DOCX → JSON/CSV (simple Hebrew heuristics)
- AI: Structured offline report; optional OpenAI integration if `OPENAI_API_KEY` exists

## Quick Start (Windows PowerShell)

Backend:
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Frontend (new terminal):
```powershell
cd frontend
npm i
npm run dev
```

- API docs: `http://127.0.0.1:8000/docs`
- UI: `http://127.0.0.1:5173`

## Data Processing (DOCX → JSON/CSV)
- Place `18-07-2022_4.2A.docx` at the project root.
- On first startup, if processed JSON is missing, the backend attempts to parse automatically.
- Manual parse:
```powershell
. .venv\Scripts\Activate.ps1
python -m backend.cli_parse 18-07-2022_4.2A.docx
```
- Output files:
  - `backend/data/processed/requirements.json`
  - `backend/data/processed/requirements.csv`

## API
- `GET /requirements` → list of structured requirements
- `POST /match` with body:
  ```json
  { "area_sqm": 80, "seats": 40, "uses_gas": false, "serves_meat": true, "offers_delivery": true }
  ```
- `POST /ai-report` with body:
  ```json
  { "business": { ... }, "matched": [ ... ], "language": "he" }
  ```

## Architecture
- `backend/app.py`: FastAPI app, CORS, routes, lazy parse on startup
- `backend/models.py`: Pydantic v2 schemas
- `backend/services/parser.py`: DOCX parsing, simple Hebrew heuristics, save JSON/CSV
- `backend/services/matcher.py`: range and boolean-based matching
- `backend/services/ai.py`: offline report; if `OPENAI_API_KEY` set and `openai` installed, tries OpenAI (`gpt-4o-mini`)
- `backend/cli_parse.py`: CLI to parse the DOCX manually
- `frontend/src/ui/App.tsx`: questionnaire UI, display of requirements, matches, and report

## Configuration
- Frontend: `VITE_API_URL` (optional) to point to the backend. Default: `http://127.0.0.1:8000`.
- Backend: `OPENAI_API_KEY` (optional) to enable OpenAI report generation.

## Notes
- Parser uses heuristics (paragraphs as requirements, keyword detection for delivery/meat/gas, numeric extraction for area/seats). Improve as needed for your specific DOCX structure.

## License
MIT
