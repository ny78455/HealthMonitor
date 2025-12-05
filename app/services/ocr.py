from typing import Tuple, Optional

def extract_text_from_input(input_type: str, text: Optional[str], image_base64: Optional[str]) -> Tuple[str, float]:
    if input_type == "image":
        return text or "", 0.6
    return text.strip(), 0.95 if text else ("", 0.0)
