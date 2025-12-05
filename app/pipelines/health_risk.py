
from typing import Dict, Any, List
from app.models import (
    HealthRawAnswers,
    HealthFactors,
    HealthRiskScore,
    HealthRecommendations,
    HealthPipelineResponse,
)
from app.services.ocr import extract_text_from_input
from app.services.normalization import (
    extract_health_factors,
    score_risk,
    health_recommendations,
)
import json

REQUIRED_FIELDS = ["age", "smoker", "exercise", "diet"]

def parse_answers(text: str) -> Dict[str, Any]:
    # Try to parse as JSON first, else naive key: value parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    answers: Dict[str, Any] = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            answers[key.strip().lower()] = val.strip()
    return answers

def run_health_risk_pipeline(
    input_type: str,
    text: str | None,
    image_base64: str | None,
) -> HealthPipelineResponse:
    # Step 1 - OCR/Text Parsing
    raw_text, conf = extract_text_from_input(input_type, text, image_base64)
    answers = parse_answers(raw_text) if raw_text else {}
    missing = [f for f in REQUIRED_FIELDS if f not in answers or answers[f] in ("", None)]
    profile_conf = 0.92 if not missing else 0.7
    raw = HealthRawAnswers(
        answers=answers,
        missing_fields=missing,
        confidence=profile_conf,
    )

    # Guardrail: incomplete profile
    if len(missing) > len(REQUIRED_FIELDS) / 2:
        factors = HealthFactors(factors=[], confidence=0.0)
        risk = HealthRiskScore(risk_level="unknown", score=0, rationale=[])
        recs = HealthRecommendations(
            risk_level="unknown",
            factors=[],
            recommendations=[],
            status="incomplete_profile",
        )
        return HealthPipelineResponse(
            step1_answers=raw,
            step2_factors=factors,
            step3_risk=risk,
            step4_recommendations=recs,
        )

    # Step 2 - Factor Extraction
    factors_list = extract_health_factors(answers)
    factors = HealthFactors(factors=factors_list, confidence=0.88 if factors_list else 0.6)

    # Step 3 - Risk Classification
    level, score, rationale = score_risk(factors_list)
    risk = HealthRiskScore(
        risk_level=level,
        score=score,
        rationale=rationale,
    )

    # Step 4 - Recommendations
    rec_list = health_recommendations(factors_list)
    recs = HealthRecommendations(
        risk_level=level,
        factors=factors_list,
        recommendations=rec_list,
        status="ok",
    )

    return HealthPipelineResponse(
        step1_answers=raw,
        step2_factors=factors,
        step3_risk=risk,
        step4_recommendations=recs,
    )