
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re
from typing import Dict, Any, List

TZ = ZoneInfo("Asia/Kolkata")


def _extract_entities(text: str) -> Dict[str, Any]:
    text_lower = text.lower()

    # Department extraction (very simple keyword-based)
    departments = ["dentist", "cardiology", "orthopedics", "dermatology", "ophthalmology"]
    department = None
    for dept in departments:
        if dept in text_lower:
            department = dept
            break

    # Time extraction: look for patterns like "3pm", "14:30", "3 pm"
    time_phrase = None
    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text_lower)
    if time_match:
        time_phrase = time_match.group(0)

    # Date phrase: basic support for "today", "tomorrow", "next friday", specific dates like 26/09/2025
    date_phrase = None
    if "today" in text_lower:
        date_phrase = "today"
    elif "tomorrow" in text_lower:
        date_phrase = "tomorrow"
    else:
        # next <weekday>
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for wd in weekdays:
            if f"next {wd}" in text_lower:
                date_phrase = f"next {wd}"
                break

    # Specific date like 26-09-2025 or 26/09/25
    if not date_phrase:
        date_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text_lower)
        if date_match:
            date_phrase = date_match.group(0)

    entities = {
        "date_phrase": date_phrase,
        "time_phrase": time_phrase,
        "department": department,
    }
    return entities


def _normalize_datetime(date_phrase: str, time_phrase: str) -> Dict[str, Any]:
    if not date_phrase or not time_phrase:
        return {}

    now = datetime.now(TZ)
    date_value: datetime

    text = date_phrase.lower().strip()
    if text == "today":
        date_value = now
    elif text == "tomorrow":
        date_value = now + timedelta(days=1)
    elif text.startswith("next "):
        target_wd = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"].index(
            text.split()[1]
        )
        days_ahead = (target_wd - now.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        date_value = now + timedelta(days=days_ahead)
    else:
        # Parse dd/mm/yyyy or dd-mm-yyyy
        match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
        if match:
            d, m, y = match.groups()
            if len(y) == 2:
                y = "20" + y
            date_value = datetime(int(y), int(m), int(d), tzinfo=TZ)
        else:
            return {}

    # Time parse
    ttext = time_phrase.lower().strip()
    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", ttext)
    if not match:
        return {}

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3)

    if ampm:
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

    date_value = date_value.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return {
        "date": date_value.strftime("%Y-%m-%d"),
        "time": date_value.strftime("%H:%M"),
        "tz": "Asia/Kolkata",
    }


def process_appointment_request(text: str, ocr_meta: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    # Step 2: Entity extraction
    entities = _extract_entities(text)
    entities_confidence = 0.85 if all(entities.values()) else 0.6

    # Step 3: Normalization
    normalized = {}
    if entities.get("date_phrase") and entities.get("time_phrase"):
        normalized = _normalize_datetime(entities["date_phrase"], entities["time_phrase"])

    if not all([
        entities.get("department"),
        entities.get("date_phrase"),
        entities.get("time_phrase"),
        normalized.get("date"),
        normalized.get("time"),
    ]):
        guardrail = {
            "status": "needs_clarification",
            "message": "Ambiguous date/time or department",
            "ocr": ocr_meta,
            "entities": entities,
        }
        if debug:
            return guardrail
        return guardrail

    normalized_confidence = 0.9

    # Step 4: Final appointment JSON
    appointment = {
        "department": entities["department"].capitalize(),
        "date": normalized["date"],
        "time": normalized["time"],
        "tz": normalized["tz"],
    }

    result: Dict[str, Any] = {
        "appointment": appointment,
        "status": "ok",
    }

    if debug:
        result["debug"] = {
            "ocr": ocr_meta,
            "entities": {
                "entities": entities,
                "entities_confidence": entities_confidence,
            },
            "normalized": {
                "normalized": normalized,
                "normalization_confidence": normalized_confidence,
            },
        }

    return result
