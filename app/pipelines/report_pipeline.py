
from typing import Dict, Any, List
import re


REF_RANGES = {
    "hemoglobin": {"low": 12.0, "high": 15.0},
    "wbc": {"low": 4000, "high": 11000},
}


def _normalize_test_name(name: str) -> str:
    name = name.lower().strip()
    if "hemo" in name:
        return "Hemoglobin"
    if "wbc" in name or "white blood" in name:
        return "WBC"
    # Fallback: title-cased original
    return name.title()


def _extract_tests(text: str) -> List[str]:
    """
    Extract raw test lines that look like:
    'Hemoglobin 10.2 g/dL (Low)'
    'WBC 11200 /uL (High)'
    """
    tests_raw: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Simple heuristic: if line has a number and a unit, treat as a test line
        if re.search(r"\d", line) and re.search(r"(g/dl|/ul|mg/dl|mmol/l|percent|%)", line.lower()):
            tests_raw.append(line)
    return tests_raw


def _parse_test_line(line: str) -> Dict[str, Any]:
    # Example line: "Hemoglobin 10.2 g/dL (Low)"
    # Capture name, value, unit, status
    name_match = re.match(r"([A-Za-z\s]+)", line)
    if not name_match:
        return {}
    name_raw = name_match.group(1).strip()
    normalized_name = _normalize_test_name(name_raw)

    value_match = re.search(r"(\d+(\.\d+)?)", line)
    if not value_match:
        return {}

    value = float(value_match.group(1))
    unit_match = re.search(r"(g/dL|/uL|mg/dL|mmol/L|percent|%)", line, re.IGNORECASE)
    unit = unit_match.group(1) if unit_match else ""

    status_match = re.search(r"\((low|high|normal)\)", line, re.IGNORECASE)
    status = status_match.group(1).lower() if status_match else "unknown"

    key = normalized_name.lower()
    ref_range = REF_RANGES.get(key, None)

    test = {
        "name": normalized_name,
        "value": value,
        "unit": unit,
        "status": status,
    }
    if ref_range:
        test["ref_range"] = ref_range

    return test


def _build_summary(tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not tests:
        return {
            "summary": "",
            "explanations": [],
        }

    findings = []
    explanations = []

    for t in tests:
        status = t.get("status", "unknown")
        name = t.get("name", "Test")
        if status in ("low", "high"):
            findings.append(f"{status} {name}".lower())
        # Very generic, non-diagnostic explanations
        if name.lower() == "hemoglobin" and status == "low":
            explanations.append("Low hemoglobin may relate to anemia.")
        if name.lower() == "wbc" and status == "high":
            explanations.append("High white blood cell count can occur with infections.")

    summary = ", ".join(set(findings)) or "No clearly abnormal tests in the input."

    return {
        "summary": summary[0].upper() + summary[1:] if summary else summary,
        "explanations": explanations,
    }


def process_report_request(text: str, ocr_meta: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    # Step 1 - OCR/Text Extraction
    tests_raw = _extract_tests(text)

    if not tests_raw:
        return {
            "status": "unprocessed",
            "reason": "no recognizable tests present in input",
            "ocr": ocr_meta,
        }

    ocr_output = {
        "tests_raw": tests_raw,
        "confidence": 0.8 if tests_raw else 0.5,
    }

    # Step 2 - Normalized Tests JSON
    tests_parsed: List[Dict[str, Any]] = []
    for line in tests_raw:
        t = _parse_test_line(line)
        if t:
            tests_parsed.append(t)

    if not tests_parsed:
        return {
            "status": "unprocessed",
            "reason": "hallucinated tests not present in input",
            "ocr": ocr_meta,
        }

    normalized_output = {
        "tests": tests_parsed,
        "normalization_confidence": 0.84,
    }

    # Step 3 - Patient-Friendly Summary
    summary_obj = _build_summary(tests_parsed)

    # Step 4 - Final Output
    result = {
        "tests": tests_parsed,
        "summary": summary_obj["summary"],
        "status": "ok",
    }

    if debug:
        result["debug"] = {
            "ocr": ocr_output,
            "normalized": normalized_output,
            "explanations": summary_obj["explanations"],
        }

    return result
