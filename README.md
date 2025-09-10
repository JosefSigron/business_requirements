# Licensing Assistant — FastAPI + React 19

An end-to-end demo that parses restaurant licensing requirements (Hebrew source), structures them to JSON, matches them to a business profile, and generates an AI-assisted report.

## Stack
- Backend: FastAPI (Python)
- Frontend: React 19 + Vite
- Parser: `python-docx` to convert DOCX → structured JSON (with section levels)
- AI: Offline formatter or OpenAI (if `OPENAI_API_KEY` in `.env`)

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

## Data Processing (DOCX → JSON)
- Put `18-07-2022_4.2A.docx` at project root.
- To build the flat list (simple requirements):
  - `http://127.0.0.1:8000/docs` → `parse-docx` → “Try it out” → Execute
  - Output JSON file: `backend/data/processed/requirements.json`
- To build the hierarchical structure:
  - `http://127.0.0.1:8000/docs` → `parse-structure` → “Try it out” → Execute
  - Output JSON file: `backend/data/processed/structure.json`

## The hierarchical JSON
- Each section has an id like `1` (level 1), `1.2` (level 2), `1.2.3` (level 3).
- Example item:
```json
{
  "id": "1.2.3",
  "level": 3,
  "title": "Short title…",
  "text": "Full text of the requirement",
  "min_area_sqm": 50,
  "max_area_sqm": 200,
  "min_seats": 20,
  "max_seats": 80,
  "requires_gas": true,
  "serves_meat": false,
  "offers_delivery": true,
  "children": []
}
```
- The tree is a list of level‑1 nodes, each with `children` for level‑2, and each level‑2 has `children` for level‑3.

## What the user can see (two modes)
1) Exact requirements
   - Show the items (especially level‑3) directly from the JSON tree.
   - Filter by: area, seats, gas, meat, delivery to show only relevant nodes.
2) AI summarized requirements
   - Send user inputs + the relevant nodes to the AI endpoint to receive a clean summary.

## API (Plain Language)
- See all flat requirements: open `http://127.0.0.1:8000/requirements`.
- See the hierarchical structure: open `http://127.0.0.1:8000/structure`.
- Find which requirements apply to your business:
  - Open `http://127.0.0.1:8000/docs`, click `match`, “Try it out”, fill fields, Execute.
- Create an AI report:
  - In the same docs, click `ai-report`, “Try it out”, fill `business` and paste relevant `matched` items (or empty), set `language`.

## Configuration
- Backend: `.env` with `OPENAI_API_KEY` to use OpenAI; otherwise offline formatter is used.
- Frontend: optional `VITE_API_URL` to point to backend (default `http://127.0.0.1:8000`).

## Notes
- The parser uses numbering patterns `1`, `1.2`, `1.2.3` to build the tree. It extracts the five key attributes when found in text: area, seats, gas, meat, delivery.

## License
MIT
