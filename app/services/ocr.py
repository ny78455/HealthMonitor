from typing import Tuple, Optional
import base64
import io
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes


def extract_text_from_input(
    input_type: str,
    text: Optional[str],
    image_base64: Optional[str],
    file_bytes: Optional[bytes] = None,
) -> Tuple[str, float]:
    """
    Extract text from:
    - raw text
    - base64 image
    - uploaded file (image/pdf)
    """

    if input_type == "text":
        return text.strip(), 0.95 if text else ("", 0.0)

    try:
        images = []

        # Case 1: File upload (PDF / image)
        if file_bytes:
            if file_bytes[:4] == b"%PDF":
                images = convert_from_bytes(file_bytes)
            else:
                images = [Image.open(io.BytesIO(file_bytes))]

        # Case 2: Base64 image
        elif image_base64:
            image_data = base64.b64decode(image_base64)
            images = [Image.open(io.BytesIO(image_data))]

        else:
            return "", 0.0

        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img)

        confidence = 0.90 if full_text.strip() else 0.0
        return full_text.strip(), confidence

    except Exception as e:
        print("OCR error:", e)
        return "", 0.0
