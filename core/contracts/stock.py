from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from core.contracts.domain import ValuationInput, ConsensusInput, InstitutionalInput, ResearchInput

# ---------------------------------------------------------
# 1. Enums (Strict Type Safety)
# ---------------------------------------------------------
class DataStatus(str, Enum):
    FETCHED = "FETCHED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"

class ValidationEventType(str, Enum):
    MISSING_FIELD = "MISSING_FIELD"
    STALE_DATA = "STALE_DATA"
    SANITY_FAILED = "SANITY_FAILED"
    LOW_TRUST_SOURCE = "LOW_TRUST_SOURCE"

class ValidationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# ---------------------------------------------------------
# 2. Metadata & Observability
# ---------------------------------------------------------
class RunMetadata(BaseModel):
    run_id: str = Field(description="Unique UUID for the portfolio batch run.")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ConfidenceAssessment(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0 trust metric.")
    reasons: List[str] = Field(default_factory=list, description="Why this score was assigned.")

class ValidationEvent(BaseModel):
    type: ValidationEventType
    field: str
    severity: ValidationSeverity
    message: str

class ValidationMetadata(BaseModel):
    validator_version: str = "5.0"
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    events: List[ValidationEvent] = Field(default_factory=list)

# ---------------------------------------------------------
# 3. The Ultimate Stock Contract
# ---------------------------------------------------------
class StockNormalizedData(BaseModel):
    """
    The canonical payload. 
    Every LLM reasoning step can trace back to this exact validated reality.
    """
    schema_version: str = "5.0"
    
    # Identity & Context
    run_metadata: RunMetadata
    ticker: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: str = "USD"
    
    # State & Quality (The Validation Engine Outputs)
    status: DataStatus = DataStatus.FETCHED
    failure_reason: Optional[str] = Field(default=None, description="Populated if status is FAILED.")
    
    data_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Can we trust the inputs?")
    validation_metadata: ValidationMetadata = Field(default_factory=ValidationMetadata)
    
    # Confidence Routing (The Adapter/Validation assessments passed to the LLMs)
    valuation_confidence: ConfidenceAssessment
    consensus_confidence: ConfidenceAssessment
    research_confidence: ConfidenceAssessment
    
    # Pointer to raw data for auditing (Prevents state bloat)
    raw_data_s3_uri: Optional[str] = None
    
    # The Sub-Contracts
    valuation: Optional[ValuationInput] = None
    consensus: Optional[ConsensusInput] = None
    institutional: Optional[InstitutionalInput] = None
    research: Optional[ResearchInput] = None