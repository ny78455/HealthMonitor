
import io
from typing import Tuple
from fastapi import UploadFile
from PIL import Image
import pytesseract
import pdfplumber

# NOTE:
# - This is a **real OCR** implementation using pytesseract for images.
# - For PDFs, we first try pdfplumber's text extraction (for digital PDFs).
#   For fully scanned PDFs, you may extend this to render pages as images
#   and call pytesseract on each page.


async def extract_text_from_upload(file: UploadFile) -> Tuple[str, float]:
    filename = file.filename or "upload"
    content = await file.read()
    if not content:
        raise ValueError("Empty file uploaded.")

    lower_name = filename.lower()
    if lower_name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")):
        return _extract_from_image_bytes(content)
    elif lower_name.endswith(".pdf"):
        return _extract_from_pdf_bytes(content)
    elif lower_name.endswith((".txt", ".md", ".csv")):
        text = content.decode(errors="ignore")
        return text, 1.0
    else:
        # Fallback: try treating it as text first, then as image
        try:
            text = content.decode(errors="ignore")
            if text.strip():
                return text, 0.9
        except Exception:
            pass
        # Try image OCR as a last resort
        return _extract_from_image_bytes(content)


def _extract_from_image_bytes(data: bytes) -> Tuple[str, float]:
    image = Image.open(io.BytesIO(data))
    # Basic preprocessing could be added here if needed
    text = pytesseract.image_to_string(image)
    # Very naive confidence heuristic based on text length
    confidence = 0.6 if len(text.strip()) < 20 else 0.8
    return text, confidence


def _extract_from_pdf_bytes(data: bytes) -> Tuple[str, float]:
    text_chunks = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

    text = "\n".join(text_chunks).strip()
    if not text:
        # Could optionally implement OCR on rendered pages here.
        # For now, return a guardrail-like low confidence.
        return "", 0.1

    confidence = 0.85 if len(text) > 50 else 0.7
    return text, confidence
