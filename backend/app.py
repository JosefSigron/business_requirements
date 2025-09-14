from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from .models import BusinessInput, Requirement, MatchResponse, ParseResponse, AIReportRequest, AIReportResponse, AIReportStructureRequest
from .services.parser import parse_txt_and_save, load_requirements, parse_structure_and_save, load_structure
from .services.matcher import match_requirements
from .services.matcher import match_structure as match_structure_tree
from .services.matcher import match_structure_advanced
from .services.ai import generate_ai_report, generate_ai_report_from_nodes


def create_app() -> FastAPI:
    # Load environment variables from .env if present
    load_dotenv()
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
        txt_path = Path.cwd() / "18-07-2022_4.2A.txt"
        if not json_path.exists():
            if txt_path.exists():
                parse_txt_and_save(str(txt_path))
            else:
                # No data yet; that's okay, user can trigger parse endpoint later
                pass

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/parse-text", response_model=ParseResponse)
    def parse_text(txt_path: Optional[str] = None) -> ParseResponse:
        if txt_path is None:
            default_txt = Path.cwd() / "18-07-2022_4.2A.txt"
            if not default_txt.exists():
                raise HTTPException(status_code=400, detail="Source TXT file not found. Provide 'txt_path' explicitly.")
            txt_path = str(default_txt)

        parsed = parse_txt_and_save(txt_path)
        return ParseResponse(total_requirements=len(parsed), sample=parsed[:5])

    @app.post("/parse-structure")
    def parse_structure(txt_path: Optional[str] = None) -> dict:
        if txt_path is None:
            default_txt = Path.cwd() / "18-07-2022_4.2A.txt"
            if not default_txt.exists():
                raise HTTPException(status_code=400, detail="Source TXT file not found. Provide 'txt_path' explicitly.")
            txt_path = str(default_txt)
        tree = parse_structure_and_save(txt_path)
        return {"nodes": [n.dict() for n in tree], "count": len(tree)}

    @app.get("/requirements", response_model=List[Requirement])
    def get_requirements() -> List[Requirement]:
        reqs = load_requirements()
        return reqs

    @app.post("/match", response_model=MatchResponse)
    def match(input_data: BusinessInput) -> MatchResponse:
        reqs = load_requirements()
        matched = match_requirements(input_data, reqs)
        return MatchResponse(total_requirements=len(reqs), matched_count=len(matched), matched=matched)

    @app.get("/structure")
    def get_structure() -> dict:
        tree = load_structure()
        return {"nodes": [n.dict() for n in tree], "count": len(tree)}

    @app.post("/structure-match")
    def structure_match(input_data: BusinessInput) -> dict:
        tree = load_structure()
        matched = match_structure_advanced(input_data, tree)
        return {"nodes": [n.dict() for n in matched], "count": len(matched)}

    @app.post("/ai-report", response_model=AIReportResponse)
    def ai_report(payload: AIReportRequest) -> AIReportResponse:
        text = generate_ai_report(payload)
        return AIReportResponse(report=text)

    @app.post("/ai-report-structure", response_model=AIReportResponse)
    def ai_report_structure(payload: AIReportStructureRequest) -> AIReportResponse:
        text = generate_ai_report_from_nodes(payload)
        return AIReportResponse(report=text)

    return app


app = create_app()



