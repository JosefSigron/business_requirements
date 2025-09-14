from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from .models import BusinessInput, AIReportResponse, AIReportStructureRequest
from .services.parser import parse_structure_and_save, load_structure
from .services.matcher import match_structure as match_structure_tree
from .services.matcher import match_structure_advanced
from .services.ai import generate_ai_report_from_nodes


def create_app() -> FastAPI:
    """Create and configure FastAPI app.

    Notes:
    - CORS is open for local development.
    - We operate in structure-only mode (TXT → structure.json).
    - Startup ensures structure is parsed once if missing.
    """
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
    def ensure_structure_loaded() -> None:
        """Parse TXT into structure.json on first run if file exists.

        This avoids forcing the user to call the parse endpoint manually
        during local development.
        """
        struct_path = data_dir / "structure.json"
        txt_path = Path.cwd() / "18-07-2022_4.2A.txt"
        if not struct_path.exists() and txt_path.exists():
            parse_structure_and_save(str(txt_path))

    @app.get("/health")
    def health() -> dict:
        """Simple liveness probe."""
        return {"status": "ok"}

    # Removed flat requirements parsing; use structure only

    @app.post("/parse-structure")
    def parse_structure(txt_path: Optional[str] = None) -> dict:
        """Parse the TXT source into a hierarchical section tree.

        If no path is provided, we look for the default TXT at project root.
        """
        if txt_path is None:
            default_txt = Path.cwd() / "18-07-2022_4.2A.txt"
            if not default_txt.exists():
                raise HTTPException(status_code=400, detail="Source TXT file not found. Provide 'txt_path' explicitly.")
            txt_path = str(default_txt)
        tree = parse_structure_and_save(txt_path)
        return {"nodes": [n.dict() for n in tree], "count": len(tree)}

    # Removed flat requirements endpoints (/requirements, /match)

    @app.get("/structure")
    def get_structure() -> dict:
        """Return the pre-parsed hierarchical structure."""
        tree = load_structure()
        return {"nodes": [n.dict() for n in tree], "count": len(tree)}

    @app.post("/structure-match")
    def structure_match(input_data: BusinessInput) -> dict:
        """Filter the structure to sections relevant to the business profile.

        Uses a combination of structured bounds and lightweight text heuristics.
        """
        tree = load_structure()
        matched = match_structure_advanced(input_data, tree)
        return {"nodes": [n.dict() for n in matched], "count": len(matched)}

    # Removed flat AI report endpoint (/ai-report)

    @app.post("/ai-report-structure", response_model=AIReportResponse)
    def ai_report_structure(payload: AIReportStructureRequest) -> AIReportResponse:
        """Create a Hebrew business-friendly report from matched structure nodes."""
        text = generate_ai_report_from_nodes(payload)
        return AIReportResponse(report=text)

    return app


app = create_app()



