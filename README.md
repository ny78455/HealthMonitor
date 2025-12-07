
# AI Backend Assignment (All 4 Problem Statements)

This backend-only project implements **all four** problem statements from the SDE Intern assignment in a single FastAPI service.

At the **start**, the API asks you which problem you want to run via the `problem_id` field:

1. AI-Powered Appointment Scheduler Assistant  
2. AI-Powered Health Risk Profiler  
3. AI-Powered Medical Report Simplifier  
4. AI-Powered Amount Detection in Medical Documents  

You then provide either **plain text** or a **document upload**.  
If you upload a document (image/PDF/text), the backend uses a **real OCR pipeline** (pytesseract + pdfplumber) to extract text and then runs the appropriate logic.

---

## Demo Video

https://drive.google.com/file/d/1KZ0aVJ-E2aX4tbzLsO5hptnjXuUwe0Tg/view?usp=sharing

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- pytesseract (real OCR for images)
- pdfplumber (for text extraction from PDFs)
- Pillow

---

## Setup Instructions

1. **Clone / Download**

   ```bash
   cd ai_backend_assignment
   ```

2. **Create virtual environment (recommended)**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install OS-level Tesseract**

   On Ubuntu:

   ```bash
   sudo apt-get update
   sudo apt-get install -y tesseract-ocr
   ```

   On macOS (Homebrew):

   ```bash
   brew install tesseract
   ```

   On Windows, install Tesseract from the official binary package and ensure `tesseract.exe` is on the PATH.

4. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Run the server**

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open docs in browser:

   - Swagger UI: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc

---

## API Overview

### Health Check

```http
GET /health
```

**Response**

```json
{
  "status": "ok"
}
```

---

### Unified Processing Endpoint

```http
POST /process
```

**Content-Type**: `multipart/form-data`

**Fields**

- `problem_id` (required, int):  
  - `1` → Appointment Scheduler  
  - `2` → Health Risk Profiler  
  - `3` → Medical Report Simplifier  
  - `4` → Amount Detection in Medical Documents  

- `text` (optional, string): Raw text input.  
- `file` (optional, file): Uploaded document (image / PDF / text).  
  - One of `text` or `file` is required.
- `debug` (optional, bool): If `true`, returns intermediate pipeline steps (OCR, entity extraction, normalization, etc.).

If `text` is provided, OCR is **skipped** and the text is used directly.  
If only `file` is provided, server performs OCR / text extraction and then runs the pipeline.

---

## Sample curl / Postman Requests

> Replace `localhost:8000` with your ngrok / cloud URL when deploying.

### 1. Appointment Scheduler (Problem 1)

**Text-only example**

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=1" \
  -F "text=Book dentist next Friday at 3pm" \
  -F "debug=true"
```

**File upload example (image/PDF)**

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=1" \
  -F "file=@samples/appointment_note.png" \
  -F "debug=true"
```

---

### 2. Health Risk Profiler (Problem 2)

**JSON-like text**

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=2" \
  -F 'text={"age":42,"smoker":true,"exercise":"rarely","diet":"high sugar"}' \
  -F "debug=true"
```

**Form-like text**

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=2" \
  -F $'text=Age: 42\nSmoker: yes\nExercise: rarely\nDiet: high sugar' \
  -F "debug=true"
```

---

### 3. Medical Report Simplifier (Problem 3)

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=3" \
  -F "text=CBC: Hemoglobin 10.2 g/dL (Low), WBC 11200 /uL (High)" \
  -F "debug=true"
```

Expected style of final output:

```json
{
  "tests": [
    {
      "name": "Hemoglobin",
      "value": 10.2,
      "unit": "g/dL",
      "status": "low",
      "ref_range": { "low": 12.0, "high": 15.0 }
    },
    {
      "name": "WBC",
      "value": 11200.0,
      "unit": "/uL",
      "status": "high",
      "ref_range": { "low": 4000, "high": 11000 }
    }
  ],
  "summary": "Low hemoglobin and high wbc.",
  "status": "ok"
}
```

If no valid tests can be extracted, the service uses a guardrail-style response:

```json
{
  "status": "unprocessed",
  "reason": "no recognizable tests present in input",
  "ocr": {...}
}
```

---

### 4. Amount Detection (Problem 4)

```bash
curl -X POST "http://localhost:8000/process" \
  -F "problem_id=4" \
  -F "text=Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%" \
  -F "debug=true"
```

Expected style of final output:

```json
{
  "currency": "INR",
  "amounts": [
    { "type": "total_bill", "value": 1200, "source": "text: 'Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%'" },
    { "type": "paid", "value": 1000, "source": "text: 'Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%'" },
    { "type": "due", "value": 200, "source": "text: 'Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%'" }
  ],
  "status": "ok"
}
```

If no numeric amounts are detected, the service responds with the guardrail:

```json
{
  "status": "no_amounts_found",
  "reason": "document too noisy or no numeric tokens",
  "ocr": {...}
}
```

---

## Architecture Notes

- **`app/main.py`**  
  - FastAPI application entry point.  
  - `/health` endpoint for health checks.  
  - `/process` endpoint that:
    - Accepts `problem_id`, `text`, `file`, `debug`.
    - Runs OCR via `app/ocr.py` when `file` is present.
    - Dispatches to the correct pipeline based on `problem_id`.

- **`app/ocr.py`**  
  - Real OCR implementation using:
    - `pytesseract` on images.
    - `pdfplumber` for PDFs (digital PDFs).  
  - For purely scanned PDFs, you can extend this by rendering pages to images and running pytesseract.

- **`app/pipelines/appointment_pipeline.py`**  
  - Implements Problem 1:
    - Entity extraction (department, date phrase, time phrase).
    - Normalization to ISO date/time in `Asia/Kolkata`.
    - Guardrails for ambiguous date/time/department.

- **`app/pipelines/health_risk_pipeline.py`**  
  - Implements Problem 2:
    - Parses JSON-like or line-based survey answers.
    - Detects missing fields and triggers guardrail if >50% are missing.
    - Extracts lifestyle risk factors.
    - Computes non-diagnostic risk score and recommendations.

- **`app/pipelines/report_pipeline.py`**  
  - Implements Problem 3:
    - Extracts raw test lines from the report.
    - Normalizes names, values, units, and reference ranges (for Hemoglobin, WBC).
    - Produces simple patient-friendly summary and explanations.
    - Guardrail when no valid tests are present or hallucination would be required.

- **`app/pipelines/amount_pipeline.py`**  
  - Implements Problem 4:
    - Extracts numeric tokens and a `currency_hint`.
    - Normalizes OCR digits to floats.
    - Uses local context (`Total`, `Paid`, `Due`, `Discount`, etc.) to classify amounts.
    - Returns final structured JSON with provenance.

---

## Production Considerations

- Add logging (e.g., Python `logging` module) for each pipeline step.
- Add request/response validation using Pydantic models if strict schemas are required.
- Rate limiting, authentication, and request size limits can be configured at the reverse-proxy or API-gateway level.
- For large-scale OCR on PDFs, consider:
  - Caching results.
  - Asynchronous background tasks for heavy documents.
  - Rendering each page as an image and running pytesseract to handle purely scanned PDFs.

---

## How This Matches the Assignment

- **Single backend** that supports all four problem statements and lets the user select which one to run at the beginning (`problem_id`).
- **Real OCR** via pytesseract and pdfplumber when documents are uploaded.
- **Guardrails** for:
  - Incomplete health profiles.
  - Ambiguous appointment date/time/department.
  - Unprocessed or hallucinated tests.
  - No amounts found / too noisy receipts.
- **Clear and modular code**:
  - Separate pipelines per problem.
  - A unified router and OCR module.
- **Easy to demo** using curl/Postman and the autogenerated Swagger UI.

