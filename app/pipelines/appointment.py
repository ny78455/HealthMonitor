
from typing import Tuple
from app.models import (
    AppointmentRawText,
    AppointmentEntities,
    AppointmentNormalized,
    AppointmentFinal,
    AppointmentPipelineResponse,
)
from app.services.ocr import extract_text_from_input
from app.services.normalization import (
    normalize_department,
    extract_time_phrase,
    extract_date_phrase,
    normalize_date_time,
)

def run_appointment_pipeline(
    input_type: str,
    text: str | None,
    image_base64: str | None,
) -> AppointmentPipelineResponse:
    # Step 1 - OCR/Text Extraction
    raw_text, conf = extract_text_from_input(input_type, text, image_base64)
    raw = AppointmentRawText(raw_text=raw_text, confidence=conf)

    # Guardrail: no text -> needs clarification
    if not raw_text:
        entities = AppointmentEntities(entities_confidence=0.0)
        normalized = AppointmentNormalized(normalization_confidence=0.0)
        final = AppointmentFinal(
            appointment=None,
            status="needs_clarification",
            message="Could not extract any text from input.",
        )
        return AppointmentPipelineResponse(
            step1_raw=raw,
            step2_entities=entities,
            step3_normalized=normalized,
            step4_final=final,
        )

    # Step 2 - Entity Extraction
    date_phrase = extract_date_phrase(raw_text)
    time_phrase = extract_time_phrase(raw_text)
    department = normalize_department(raw_text)
    entities_conf = 0.85 if all([date_phrase, time_phrase, department]) else 0.6
    entities = AppointmentEntities(
        date_phrase=date_phrase,
        time_phrase=time_phrase,
        department=department,
        entities_confidence=entities_conf,
    )

    # Step 3 - Normalization
    date_iso, time_iso, norm_conf = normalize_date_time(date_phrase, time_phrase)
    normalized = AppointmentNormalized(
        date=date_iso,
        time=time_iso,
        tz="Asia/Kolkata",
        normalization_confidence=norm_conf,
    )

    # Guardrail: ambiguity
    if not date_iso or not time_iso or not department:
        final = AppointmentFinal(
            appointment=None,
            status="needs_clarification",
            message="Ambiguous or incomplete date/time/department in appointment request.",
        )
    else:
        final = AppointmentFinal(
            appointment={
                "department": department,
                "date": date_iso,
                "time": time_iso,
                "tz": "Asia/Kolkata",
            },
            status="ok",
            message=None,
        )

    return AppointmentPipelineResponse(
        step1_raw=raw,
        step2_entities=entities,
        step3_normalized=normalized,
        step4_final=final,
    )