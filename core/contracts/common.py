from pydantic import BaseModel, Field, model_validator
from typing import Any, Literal, Optional
from datetime import datetime

class DataPoint(BaseModel):
    """The atomic unit of truth in Watchdog. Every metric carries its lineage."""
    value: Any
    source: Literal["Yahoo Finance", "SEC Edgar", "FRED", "Polygon", "Manual", "Calculated"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0,
        description="Reliability of this source. SEC = 0.98, Whisper Number = 0.60."
    )

class DeltaPoint(BaseModel):
    """Tracks momentum. The delta is mathematically guaranteed, not scraped."""
    current: DataPoint
    historical_90d: DataPoint
    delta_pct: Optional[float] = Field(default=None, description="Auto-calculated. Do not pass in.")

    @model_validator(mode="after")
    def calculate_delta(self) -> 'DeltaPoint':
        # Safely calculate truth to prevent vendor data contradictions
        curr_val = self.current.value
        hist_val = self.historical_90d.value
        
        if isinstance(curr_val, (int, float)) and isinstance(hist_val, (int, float)):
            if hist_val != 0:
                self.delta_pct = ((curr_val - hist_val) / abs(hist_val)) * 100.0
            else:
                self.delta_pct = 0.0 # Handle division by zero gracefully
        return self