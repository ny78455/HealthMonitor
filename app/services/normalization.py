
from __future__ import annotations
from datetime import datetime
from typing import Optional, Tuple, List, Dict
import re

import pytz
from dateutil import parser as date_parser

IST = pytz.timezone("Asia/Kolkata")

# ------- Problem 1: Appointment helpers -------

DEPARTMENT_ALIASES = {
    "dentist": "Dentistry",
    "dentistry": "Dentistry",
    "cardio": "Cardiology",
    "cardiologist": "Cardiology",
    "eye": "Ophthalmology",
    "eye doctor": "Ophthalmology",
}

TIME_PATTERN = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)

def normalize_department(raw_text: str) -> Optional[str]:
    text = raw_text.lower()
    for key, val in DEPARTMENT_ALIASES.items():
        if key in text:
            return val
    return None

def extract_time_phrase(raw_text: str) -> Optional[str]:
    # very simple: first time-like pattern
    m = TIME_PATTERN.search(raw_text)
    if m:
        return m.group(0)
    return None

def extract_date_phrase(raw_text: str) -> Optional[str]:
    # naive heuristic: look for words like today, tomorrow, next <weekday>, or explicit dates
    patterns = [
        r"today",
        r"tomorrow",
        r"next\s+\w+",
        r"on\s+\w+day",
        r"\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?",
    ]
    for p in patterns:
        m = re.search(p, raw_text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None

def normalize_date_time(date_phrase: Optional[str], time_phrase: Optional[str]) -> Tuple[Optional[str], Optional[str], float]:
    if not date_phrase or not time_phrase:
        return None, None, 0.0

    try:
        # Let dateutil parse the combined string relative to now in IST
        now = datetime.now(IST)
        dt = date_parser.parse(
            f"{date_phrase} {time_phrase}",
            dayfirst=True,
            default=now,
        )
        dt_ist = dt.astimezone(IST)
        return dt_ist.date().isoformat(), dt_ist.strftime("%H:%M"), 0.9
    except Exception:
        return None, None, 0.0

# ------- Problem 2: Health Risk helpers -------

def extract_health_factors(answers: Dict[str, object]) -> List[str]:
    factors: List[str] = []
    smoker = str(answers.get("smoker", "")).lower()
    if smoker in {"true", "yes", "y", "1"} or smoker is True:
        factors.append("smoking")
    exercise = str(answers.get("exercise", "")).lower()
    if exercise in {"never", "rarely", "sedentary"}:
        factors.append("low exercise")
    diet = str(answers.get("diet", "")).lower()
    if "sugar" in diet or "junk" in diet or "fried" in diet:
        factors.append("poor diet")
    age_val = answers.get("age")
    try:
        age = int(age_val)
        if age >= 45:
            factors.append("age_over_45")
    except Exception:
        pass
    return factors

def score_risk(factors: List[str]) -> Tuple[str, int, List[str]]:
    score = 0
    rationale: List[str] = []
    weights = {
        "smoking": 30,
        "poor diet": 20,
        "low exercise": 20,
        "age_over_45": 10,
    }
    for f in factors:
        score += weights.get(f, 5)
        rationale.append(f)
    level = "low"
    if score >= 70:
        level = "high"
    elif score >= 40:
        level = "medium"
    return level, score, rationale

def health_recommendations(factors: List[str]) -> List[str]:
    recs: List[str] = []
    if "smoking" in factors:
        recs.append("Quit smoking or seek help to reduce.")
    if "poor diet" in factors:
        recs.append("Reduce sugar and processed foods; add more fruits and vegetables.")
    if "low exercise" in factors:
        recs.append("Aim for at least 30 minutes of walking or light activity daily.")
    if "age_over_45" in factors:
        recs.append("Schedule regular health checkups as recommended by your doctor.")
    if not recs:
        recs.append("Maintain a balanced diet, regular activity, and regular checkups.")
    return recs

# ------- Problem 3: Report simplifier helpers -------

def split_tests(raw_text: str) -> List[str]:
    # Split by newline or comma
    parts = re.split(r"[\n,]+", raw_text)
    return [p.strip() for p in parts if p.strip()]

def normalize_test_line(line: str) -> Optional[Dict[str, object]]:
    line_lower = line.lower()
    # Very simple normalizer for demo for Hemoglobin and WBC
    if "hemoglobin" in line_lower or "hemglobin" in line_lower:
        m = re.search(r"(\d+(?:\.\d+)?)", line)
        if not m:
            return None
        value = float(m.group(1))
        status = "low" if value < 12 else ("high" if value > 15 else "normal")
        return {
            "name": "Hemoglobin",
            "value": value,
            "unit": "g/dL",
            "status": status,
            "ref_range": {"low": 12.0, "high": 15.0},
        }
    if "wbc" in line_lower:
        m = re.search(r"(\d+(?:,\d+)*)", line)
        if not m:
            return None
        value = float(m.group(1).replace(",", ""))
        status = "low" if value < 4000 else ("high" if value > 11000 else "normal")
        return {
            "name": "WBC",
            "value": value,
            "unit": "/uL",
            "status": status,
            "ref_range": {"low": 4000.0, "high": 11000.0},
        }
    # Unknown test: we ignore rather than hallucinating
    return None

def build_patient_summary(tests: List[Dict[str, object]]) -> str:
    bits: List[str] = []
    for t in tests:
        if t["status"] == "low":
            bits.append(f"Low {t['name']}")
        elif t["status"] == "high":
            bits.append(f"High {t['name']}")
    if not bits:
        return "All available test values appear within the reference range provided."
    return ", ".join(bits) + "."

def explanations_from_tests(tests: List[Dict[str, object]]) -> List[str]:
    exp: List[str] = []
    for t in tests:
        if t["name"] == "Hemoglobin" and t["status"] == "low":
            exp.append("Low hemoglobin may relate to anemia or blood loss; discuss with your doctor.")
        if t["name"] == "WBC" and t["status"] == "high":
            exp.append("High white blood cell count can occur with infections or inflammation.")
    if not exp:
        exp.append("These explanations are general and not a diagnosis. Please consult your doctor for medical advice.")
    return exp

# ------- Problem 4: Amount detection helpers -------

AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?")

def extract_amount_tokens(raw_text: str) -> List[str]:
    return AMOUNT_RE.findall(raw_text)

def detect_currency_hint(raw_text: str) -> Optional[str]:
    if any(c in raw_text.lower() for c in ["inr", "rs", "₹"]):
        return "INR"
    if any(c in raw_text.lower() for c in ["usd", "$"]):
        return "USD"
    return None

def classify_amounts(raw_text: str, amounts: List[float]) -> List[Dict[str, object]]:
    labeled: List[Dict[str, object]] = []
    # Simple heuristic based on keywords and ordering
    contexts = [
        ("total_bill", ["total", "bill", "amount"]),
        ("paid", ["paid"]),
        ("due", ["due", "balance"]),
        ("discount", ["discount"]),
    ]
    # We'll look around each amount for context words
    for value in amounts:
        s_val = str(int(value)) if float(value).is_integer() else str(value)
        idx = raw_text.find(s_val)
        window = raw_text[max(0, idx - 20): idx + 20].lower() if idx != -1 else ""
        chosen_type = "unknown"
        for t, kws in contexts:
            if any(k in window for k in kws):
                chosen_type = t
                break
        source = f"text window: '{window.strip()}'"
        labeled.append({"type": chosen_type, "value": value, "source": source})
    return labeled