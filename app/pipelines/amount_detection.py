
from typing import List
from app.models import (
    RawTokens,
    NormalizedAmounts,
    LabeledAmount,
    AmountsByContext,
    AmountFinal,
    AmountPipelineResponse,
)
from app.services.ocr import extract_text_from_input
from app.services.normalization import (
    extract_amount_tokens,
    detect_currency_hint,
    classify_amounts,
)

def run_amount_pipeline(
    input_type: str,
    text: str | None,
    image_base64: str | None,
) -> AmountPipelineResponse:
    # Step 1 - OCR/Text Extraction
    raw_text, conf = extract_text_from_input(input_type, text, image_base64)
    tokens = extract_amount_tokens(raw_text) if raw_text else []
    currency_hint = detect_currency_hint(raw_text) if raw_text else None
    raw = RawTokens(
        raw_tokens=tokens,
        currency_hint=currency_hint,
        confidence=conf if tokens else 0.0,
    )

    # Guardrail: no amounts found
    if not tokens:
        normalized = NormalizedAmounts(normalized_amounts=[], normalization_confidence=0.0)
        classified = AmountsByContext(amounts=[], confidence=0.0)
        final = AmountFinal(currency=currency_hint or "INR", amounts=[], status="no_amounts_found")
        return AmountPipelineResponse(
            step1_raw_tokens=raw,
            step2_normalized=normalized,
            step3_classified=classified,
            step4_final=final,
        )

    # Step 2 - Normalization
    amounts: List[float] = []
    for t in tokens:
        try:
            amounts.append(float(t.replace(",", "")))
        except Exception:
            continue
    normalization_conf = 0.82 if amounts else 0.6
    normalized = NormalizedAmounts(
        normalized_amounts=amounts,
        normalization_confidence=normalization_conf,
    )

    # Step 3 - Classification by Context
    labeled_dicts = classify_amounts(raw_text, amounts)
    labeled = [LabeledAmount(**a) for a in labeled_dicts]
    classified = AmountsByContext(
        amounts=labeled,
        confidence=0.8 if labeled else 0.6,
    )

    # Step 4 - Final Output
    final = AmountFinal(
        currency=currency_hint or "INR",
        amounts=labeled,
        status="ok",
    )

    return AmountPipelineResponse(
        step1_raw_tokens=raw,
        step2_normalized=normalized,
        step3_classified=classified,
        step4_final=final,
    )