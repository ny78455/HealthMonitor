
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from .ocr import extract_text_from_upload
from .pipelines.appointment_pipeline import process_appointment_request
from .pipelines.health_risk_pipeline import process_health_risk_request
from .pipelines.report_pipeline import process_report_request
from .pipelines.amount_pipeline import process_amount_request

app = FastAPI(
    title="AI Backend Assignment API",
    description=(
        "Single backend that supports 4 problem statements:\n"
        "1. AI-Powered Appointment Scheduler Assistant\n"
        "2. AI-Powered Health Risk Profiler\n"
        "3. AI-Powered Medical Report Simplifier\n"
        "4. AI-Powered Amount Detection in Medical Documents\n\n"
        "Choose the problem you want to run using the `problem_id` field."
    ),
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/process")
async def process_document(
    problem_id: int = Form(..., description="1, 2, 3 or 4"),
    text: Optional[str] = Form(
        None, description="Optional raw text. If not provided, `file` is required."
    ),
    file: Optional[UploadFile] = File(
        None, description="Optional document (image/PDF/text). Required if `text` is empty."
    ),
    debug: bool = Form(
        False,
        description="If true, returns intermediate pipeline steps for debugging.",
    ),
):
    """
    Unified entry point.

    - At the *start* you choose what you want using `problem_id`:
        1 → Appointment Scheduler
        2 → Health Risk Profiler
        3 → Medical Report Simplifier
        4 → Amount Detection in Medical Documents

    - Provide either:
        * `text` (plain text input), or
        * `file` (image / PDF / text document) which will go through **real OCR**.
    """
    if problem_id not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="Invalid problem_id. Use 1, 2, 3 or 4.")

    if not text and not file:
        raise HTTPException(
            status_code=400,
            detail="Either `text` or `file` is required.",
        )

    # Step 1: OCR / text extraction
    if text:
        extracted_text = text
        ocr_meta = {
            "raw_text": text,
            "confidence": 1.0,
            "source": "raw_text",
        }
    else:
        try:
            extracted_text, confidence = await extract_text_from_upload(file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        ocr_meta = {
            "raw_text": extracted_text,
            "confidence": confidence,
            "source": f"file:{file.filename}",
        }

    # Dispatch to the appropriate pipeline
    try:
        if problem_id == 1:
            result = process_appointment_request(extracted_text, ocr_meta, debug=debug)
        elif problem_id == 2:
            result = process_health_risk_request(extracted_text, ocr_meta, debug=debug)
        elif problem_id == 3:
            result = process_report_request(extracted_text, ocr_meta, debug=debug)
        else:
            result = process_amount_request(extracted_text, ocr_meta, debug=debug)
    except Exception as exc:
        # Production-style guardrail
        raise HTTPException(status_code=500, detail=f"Internal processing error: {exc}")

    return JSONResponse(result)
