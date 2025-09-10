from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Optional

from .models import BusinessInput, Requirement, MatchResponse, ParseResponse, AIReportRequest, AIReportResponse
from .services.parser import parse_docx_and_save, load_requirements
from .services.matcher import match_requirements
from .services.ai import generate_ai_report


def create_app() -> FastAPI:
    app = FastAPI(title="Licensing Assistant API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    data_dir = Path(__file__).parent / "data" / "processed"
    data_dir.mkdir(parents=True, exist_ok=True)

    @app.on_event("startup")
    def ensure_requirements_loaded() -> None:
        json_path = data_dir / "requirements.json"
        docx_path = Path.cwd() / "18-07-2022_4.2A.docx"
        if not json_path.exists():
            if docx_path.exists():
                parse_docx_and_save(str(docx_path))
            else:
                # No data yet; that's okay, user can trigger parse endpoint later
                pass

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/parse-docx", response_model=ParseResponse)
    def parse_docx(docx_path: Optional[str] = None) -> ParseResponse:
        if docx_path is None:
            default_path = Path.cwd() / "18-07-2022_4.2A.docx"
            if not default_path.exists():
                raise HTTPException(status_code=400, detail="DOCX file not found. Provide 'docx_path' explicitly.")
            docx_path = str(default_path)

        parsed = parse_docx_and_save(docx_path)
        return ParseResponse(total_requirements=len(parsed), sample=parsed[:5])

    @app.get("/requirements", response_model=List[Requirement])
    def get_requirements() -> List[Requirement]:
        reqs = load_requirements()
        return reqs

    @app.post("/match", response_model=MatchResponse)
    def match(input_data: BusinessInput) -> MatchResponse:
        reqs = load_requirements()
        matched = match_requirements(input_data, reqs)
        return MatchResponse(total_requirements=len(reqs), matched_count=len(matched), matched=matched)

    @app.post("/ai-report", response_model=AIReportResponse)
    def ai_report(payload: AIReportRequest) -> AIReportResponse:
        text = generate_ai_report(payload)
        return AIReportResponse(report=text)

    return app


app = create_app()



