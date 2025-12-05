
from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --------- Common ---------

class MenuItem(BaseModel):
    id: int
    name: str
    description: str

class MenuResponse(BaseModel):
    message: str
    options: List[MenuItem]

class BaseStatusResponse(BaseModel):
    status: str = Field(..., description="ok | needs_clarification | incomplete_profile | unprocessed | no_amounts_found")
    message: Optional[str] = None

class ProcessRequest(BaseModel):
    problem_id: int = Field(..., ge=1, le=4, description="Which pipeline to run (1-4)")
    input_type: str = Field("text", description="text or image")
    text: Optional[str] = None
    # In a real system we'd accept a file; here we allow base64 or a simple hint
    image_base64: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

# --------- Problem 1: Appointment ---------

class AppointmentRawText(BaseModel):
    raw_text: str
    confidence: float

class AppointmentEntities(BaseModel):
    date_phrase: Optional[str] = None
    time_phrase: Optional[str] = None
    department: Optional[str] = None
    entities_confidence: float = 0.0

class AppointmentNormalized(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    tz: str = "Asia/Kolkata"
    normalization_confidence: float = 0.0

class AppointmentFinal(BaseModel):
    appointment: Optional[Dict[str, Any]] = None
    status: str
    message: Optional[str] = None

class AppointmentPipelineResponse(BaseModel):
    step1_raw: AppointmentRawText
    step2_entities: AppointmentEntities
    step3_normalized: AppointmentNormalized
    step4_final: AppointmentFinal

# --------- Problem 2: Health Risk ---------

class HealthRawAnswers(BaseModel):
    answers: Dict[str, Any]
    missing_fields: List[str]
    confidence: float

class HealthFactors(BaseModel):
    factors: List[str]
    confidence: float

class HealthRiskScore(BaseModel):
    risk_level: str
    score: int
    rationale: List[str]

class HealthRecommendations(BaseModel):
    risk_level: str
    factors: List[str]
    recommendations: List[str]
    status: str

class HealthPipelineResponse(BaseModel):
    step1_answers: HealthRawAnswers
    step2_factors: HealthFactors
    step3_risk: HealthRiskScore
    step4_recommendations: HealthRecommendations

# --------- Problem 3: Report Simplifier ---------

class RawTests(BaseModel):
    tests_raw: List[str]
    confidence: float

class NormalizedTest(BaseModel):
    name: str
    value: float
    unit: str
    status: str
    ref_range: Dict[str, float]

class NormalizedTests(BaseModel):
    tests: List[NormalizedTest]
    normalization_confidence: float

class PatientSummary(BaseModel):
    summary: str
    explanations: List[str]
    status: str = "ok"

class ReportPipelineResponse(BaseModel):
    step1_raw_tests: RawTests
    step2_normalized: NormalizedTests
    step3_summary: PatientSummary

# --------- Problem 4: Amount Detection ---------

class RawTokens(BaseModel):
    raw_tokens: List[str]
    currency_hint: Optional[str]
    confidence: float

class NormalizedAmounts(BaseModel):
    normalized_amounts: List[float]
    normalization_confidence: float

class LabeledAmount(BaseModel):
    type: str
    value: float
    source: str

class AmountsByContext(BaseModel):
    amounts: List[LabeledAmount]
    confidence: float

class AmountFinal(BaseModel):
    currency: str
    amounts: List[LabeledAmount]
    status: str

class AmountPipelineResponse(BaseModel):
    step1_raw_tokens: RawTokens
    step2_normalized: NormalizedAmounts
    step3_classified: AmountsByContext
    step4_final: AmountFinal

# --------- Unified pipeline response ---------

class PipelineResult(BaseModel):
    problem_id: int
    result: Any