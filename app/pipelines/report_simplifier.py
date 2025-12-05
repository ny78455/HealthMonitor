
from typing import List
from app.models import (
    RawTests,
    NormalizedTest,
    NormalizedTests,
    PatientSummary,
    ReportPipelineResponse,
)
from app.services.ocr import extract_text_from_input
from app.services.normalization import (
    split_tests,
    normalize_test_line,
    build_patient_summary,
    explanations_from_tests,
)

def run_report_pipeline(
    input_type: str,
    text: str | None,
    image_base64: str | None,
) -> ReportPipelineResponse:
    # Step 1 - OCR/Text extraction
    raw_text, conf = extract_text_from_input(input_type, text, image_base64)
    if not raw_text:
        tests_raw: List[str] = []
        raw = RawTests(tests_raw=tests_raw, confidence=0.0)
        normalized = NormalizedTests(tests=[], normalization_confidence=0.0)
        summary = PatientSummary(
            summary="",
            explanations=[],
            status="unprocessed",
        )
        return ReportPipelineResponse(
            step1_raw_tests=raw,
            step2_normalized=normalized,
            step3_summary=summary,
        )

    tests_raw = split_tests(raw_text)
    raw = RawTests(tests_raw=tests_raw, confidence=conf)

    # Step 2 - Normalized Tests JSON
    norm_tests: List[NormalizedTest] = []
    for line in tests_raw:
        parsed = normalize_test_line(line)
        if parsed:
            norm_tests.append(NormalizedTest(**parsed))

    normalization_conf = 0.84 if norm_tests else 0.0
    normalized = NormalizedTests(tests=norm_tests, normalization_confidence=normalization_conf)

    # Guardrail: hallucination check - we never add tests beyond those derived from input lines,
    # so if norm_tests is empty but we had text, mark as unprocessed.
    if not norm_tests:
        summary = PatientSummary(
            summary="",
            explanations=[],
            status="unprocessed",
        )
        return ReportPipelineResponse(
            step1_raw_tests=raw,
            step2_normalized=normalized,
            step3_summary=summary,
        )

    # Step 3 - Patient-Friendly Summary
    summary_text = build_patient_summary([t.model_dump() for t in norm_tests])
    explanations = explanations_from_tests([t.model_dump() for t in norm_tests])
    summary = PatientSummary(
        summary=summary_text,
        explanations=explanations,
        status="ok",
    )

    return ReportPipelineResponse(
        step1_raw_tests=raw,
        step2_normalized=normalized,
        step3_summary=summary,
    )