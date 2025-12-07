
from typing import Dict, Any, List
import json
import re


EXPECTED_FIELDS = ["age", "smoker", "exercise", "diet"]


def _parse_answers(text: str) -> Dict[str, Any]:
    text_stripped = text.strip()

    # Try JSON first
    try:
        data = json.loads(text_stripped)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Fallback: parse key: value lines
    answers: Dict[str, Any] = {}
    for line in text_stripped.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().lower()
        if key in ("age", "smoker", "exercise", "diet"):
            if key == "age":
                try:
                    answers["age"] = int(re.findall(r"\d+", value)[0])
                except Exception:
                    continue
            elif key == "smoker":
                answers["smoker"] = value in ("yes", "true", "y", "1")
            else:
                answers[key] = value

    return answers


def _extract_factors(answers: Dict[str, Any]) -> List[str]:
    factors: List[str] = []

    if answers.get("smoker"):
        factors.append("smoking")

    exercise = str(answers.get("exercise", "")).lower()
    if any(word in exercise for word in ["rarely", "never", "sedentary", "low"]):
        factors.append("low exercise")

    diet = str(answers.get("diet", "")).lower()
    if any(word in diet for word in ["high sugar", "junk", "fried", "processed"]):
        factors.append("poor diet")

    age = answers.get("age")
    if isinstance(age, int) and age >= 55:
        factors.append("age 55+")

    return factors


def _compute_risk_score(factors: List[str]) -> Dict[str, Any]:
    base = 10
    for f in factors:
        if f == "smoking":
            base += 35
        elif f == "poor diet":
            base += 20
        elif f == "low exercise":
            base += 20
        elif f == "age 55+":
            base += 15

    score = min(base, 100)

    if score < 30:
        level = "low"
    elif score < 60:
        level = "moderate"
    else:
        level = "high"

    rationale = factors or ["no significant lifestyle risk factors identified"]
    return {"risk_level": level, "score": score, "rationale": rationale}


def _build_recommendations(factors: List[str], risk_level: str) -> List[str]:
    recs: List[str] = []

    if "smoking" in factors:
        recs.append("Quit smoking or seek help with a cessation program.")
    if "poor diet" in factors:
        recs.append("Reduce sugar and ultra-processed foods; add more fruits and vegetables.")
    if "low exercise" in factors:
        recs.append("Aim for at least 30 minutes of walking or light activity most days.")
    if "age 55+" in factors:
        recs.append("Schedule regular health check-ups as advised by your doctor.")

    if not recs and risk_level == "low":
        recs.append("Maintain your current healthy habits and get regular check-ups.")

    return recs


def process_health_risk_request(text: str, ocr_meta: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    # Step 1 - OCR/Text Parsing
    answers_raw = _parse_answers(text)
    missing_fields = [f for f in EXPECTED_FIELDS if f not in answers_raw]

    # Guardrail if >50% fields missing
    if len(missing_fields) > len(EXPECTED_FIELDS) / 2:
        return {
            "status": "incomplete_profile",
            "reason": ">50% fields missing",
            "answers": answers_raw,
            "missing_fields": missing_fields,
            "ocr": ocr_meta,
        }

    parsed_output = {
        "answers": answers_raw,
        "missing_fields": missing_fields,
        "confidence": 0.92 if not missing_fields else 0.8,
    }

    # Step 2 - Factor Extraction
    factors = _extract_factors(answers_raw)
    factor_output = {
        "factors": factors,
        "confidence": 0.88 if factors else 0.6,
    }

    # Step 3 - Risk Classification
    risk_info = _compute_risk_score(factors)

    # Step 4 - Recommendations
    recommendations = _build_recommendations(factors, risk_info["risk_level"])

    result = {
        "risk_level": risk_info["risk_level"],
        "factors": factors,
        "score": risk_info["score"],
        "rationale": risk_info["rationale"],
        "recommendations": recommendations,
        "status": "ok",
    }

    if debug:
        result["debug"] = {
            "ocr": ocr_meta,
            "parsed_answers": parsed_output,
            "factor_extraction": factor_output,
        }

    return result
