
from typing import Dict, Any, List
import re


def _extract_raw_tokens(text: str) -> Dict[str, Any]:
    # Extract raw numeric tokens including percentages
    tokens = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?", text)
    currency_hint = None
    text_lower = text.lower()
    if "inr" in text_lower or "₹" in text_lower or "rs" in text_lower:
        currency_hint = "INR"
    elif "usd" in text_lower or "$" in text_lower:
        currency_hint = "USD"

    return {
        "raw_tokens": tokens,
        "currency_hint": currency_hint or "INR",  # default to INR per problem statement
        "confidence": 0.74 if tokens else 0.3,
    }


def _normalize_amounts(raw_tokens: List[str]) -> Dict[str, Any]:
    normalized: List[float] = []
    for tok in raw_tokens:
        if tok.endswith("%"):
            # Skip percentage for numeric normalization step
            continue
        clean = tok.replace(",", "")
        try:
            value = float(clean)
            normalized.append(value)
        except ValueError:
            continue

    return {
        "normalized_amounts": normalized,
        "normalization_confidence": 0.82 if normalized else 0.4,
    }


def _classify_amounts(text: str, normalized_amounts: List[float]) -> Dict[str, Any]:
    amounts: List[Dict[str, Any]] = []

    # To keep provenance, we look around each numeric match in the original text
    for match in re.finditer(r"\d+(?:,\d{3})*(?:\.\d+)?", text):
        value_str = match.group(0).replace(",", "")
        try:
            value = float(value_str)
        except ValueError:
            continue
        if value not in normalized_amounts:
            # If the same number appears multiple times, we still handle it once
            # but this avoids mismatches with skipped tokens.
            pass

        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end].lower()

        type_ = "other"
        if "total" in context:
            type_ = "total_bill"
        elif "paid" in context:
            type_ = "paid"
        elif "due" in context or "balance" in context:
            type_ = "due"
        elif "discount" in context:
            type_ = "discount"

        source_snippet = text[start:end].strip()

        amounts.append(
            {
                "type": type_,
                "value": value,
                "source": f"text: '{source_snippet}'",
            }
        )

    confidence = 0.8 if amounts else 0.4
    return {
        "amounts": amounts,
        "confidence": confidence,
    }


def process_amount_request(text: str, ocr_meta: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    # Step 1 - OCR/Text Extraction
    raw_tokens_output = _extract_raw_tokens(text)
    raw_tokens = raw_tokens_output["raw_tokens"]

    if not raw_tokens:
        return {
            "status": "no_amounts_found",
            "reason": "document too noisy or no numeric tokens",
            "ocr": ocr_meta,
        }

    # Step 2 - Normalization
    normalized_output = _normalize_amounts(raw_tokens)
    normalized_amounts = normalized_output["normalized_amounts"]

    # Step 3 - Classification by Context
    classified_output = _classify_amounts(text, normalized_amounts)

    # Step 4 - Final Output
    result = {
        "currency": raw_tokens_output["currency_hint"],
        "amounts": classified_output["amounts"],
        "status": "ok",
    }

    if debug:
        result["debug"] = {
            "ocr": {
                "raw_tokens": raw_tokens_output["raw_tokens"],
                "currency_hint": raw_tokens_output["currency_hint"],
                "confidence": raw_tokens_output["confidence"],
            },
            "normalized": normalized_output,
            "classified": classified_output,
        }

    return result
