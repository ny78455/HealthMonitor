
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.models import (
    MenuItem,
    MenuResponse,
    ProcessRequest,
    PipelineResult,
)
from app.pipelines.appointment import run_appointment_pipeline
from app.pipelines.health_risk import run_health_risk_pipeline
from app.pipelines.report_simplifier import run_report_pipeline
from app.pipelines.amount_detection import run_amount_pipeline
from app.services.logging_config import configure_logging
import logging
from fastapi import UploadFile, File, Form


logger = logging.getLogger(__name__)

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="""Backend service for 4 AI-powered pipelines:
    1. Appointment Scheduler
    2. Health Risk Profiler
    3. Medical Report Simplifier
    4. Amount Detection in Medical Documents

    At startup, use the `/menu` endpoint to see available options, then POST to `/process`.
    """,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/menu", response_model=MenuResponse)
async def menu() -> MenuResponse:
    """
    Returns the list of available problem statements.
    This is the 'starting point' that asks you which of the four tasks you want.
    """
    options = [
        MenuItem(
            id=1,
            name="AI-Powered Appointment Scheduler Assistant",
            description="OCR -> Entity Extraction -> Normalization (Asia/Kolkata)",
        ),
        MenuItem(
            id=2,
            name="AI-Powered Health Risk Profiler",
            description="OCR -> Factor Extraction -> Risk & Recommendations",
        ),
        MenuItem(
            id=3,
            name="AI-Powered Medical Report Simplifier",
            description="OCR -> Test Extraction -> Plain-Language Explanation",
        ),
        MenuItem(
            id=4,
            name="AI-Powered Amount Detection in Medical Documents",
            description="OCR -> Numeric Normalization -> Context Classification",
        ),
    ]
    return MenuResponse(
        message="Select a problem_id (1-4) and call POST /process with your input.",
        options=options,
    )

@app.post("/process", response_model=PipelineResult)
async def process(req: ProcessRequest) -> PipelineResult:
    """
    Unified entrypoint. You specify which of the four problem statements you want to solve
    via `problem_id`, and this endpoint runs the corresponding pipeline.
    """
    problem_id = req.problem_id
    logger.info("Processing request for problem_id=%s, input_type=%s", problem_id, req.input_type)

    if req.input_type not in {"text", "image"}:
        raise HTTPException(status_code=400, detail="input_type must be 'text' or 'image'")

    if not req.text and not req.image_base64:
        raise HTTPException(status_code=400, detail="Provide at least 'text' or 'image_base64'.")

    if problem_id == 1:
        result = run_appointment_pipeline(req.input_type, req.text, req.image_base64)
    elif problem_id == 2:
        result = run_health_risk_pipeline(req.input_type, req.text, req.image_base64)
    elif problem_id == 3:
        result = run_report_pipeline(req.input_type, req.text, req.image_base64)
    elif problem_id == 4:
        result = run_amount_pipeline(req.input_type, req.text, req.image_base64)
    else:
        raise HTTPException(status_code=400, detail="problem_id must be between 1 and 4")

    return PipelineResult(problem_id=problem_id, result=result)

@app.post("/process-file", response_model=PipelineResult)
async def process_file(
    problem_id: int = Form(...),
    file: UploadFile = File(...),
):
    contents = await file.read()

    if problem_id == 1:
        result = run_appointment_pipeline("image", None, None, contents)
    elif problem_id == 2:
        result = run_health_risk_pipeline("image", None, None, contents)
    elif problem_id == 3:
        result = run_report_pipeline("image", None, None, contents)
    elif problem_id == 4:
        result = run_amount_pipeline("image", None, None, contents)
    else:
        raise HTTPException(status_code=400, detail="Invalid problem_id")

    return PipelineResult(problem_id=problem_id, result=result)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Welcome to the AI Assistant Backend. Call /menu to choose a problem, then POST /process.",
    }