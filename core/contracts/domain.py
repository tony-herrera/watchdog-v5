from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, Any, Optional
from datetime import datetime
from core.contracts.common import DataPoint, DeltaPoint

# ---------------------------------------------------------
# 1. The Lineage Base Class
# ---------------------------------------------------------
class DomainContract(BaseModel):
    """Every analyst input must carry identity, time, and version context."""
    ticker: str
    as_of: datetime = Field(default_factory=datetime.utcnow)
    schema_version: str = "5.0"

# ---------------------------------------------------------
# 2. Valuation (Now with Growth Context & Validation)
# ---------------------------------------------------------
class ValuationInput(DomainContract):
    forward_pe: DeltaPoint
    ev_to_ebitda: DeltaPoint
    
    # Growth Context
    revenue_growth_next_year: DataPoint
    eps_growth_next_year: DataPoint
    
    implied_earnings_yield: DataPoint
    price_to_book: DataPoint

    @field_validator("forward_pe")
    def validate_pe(cls, v: DeltaPoint):
        # We check the current value inside the DeltaPoint
        if isinstance(v.current.value, (int, float)) and v.current.value < 0:
            # Instead of crashing, we can nullify or handle it. 
            # For strictness, raising ValueError flags it as FAILED/PARTIAL in normalization.
            raise ValueError(f"Negative Forward P/E ({v.current.value}) is invalid for standard valuation models.")
        return v

# ---------------------------------------------------------
# 3. Consensus (Now with Revision Velocity & Calculated Spreads)
# ---------------------------------------------------------
class ConsensusInput(DomainContract):
    eps_estimate_next_qtr: DeltaPoint
    revenue_estimate_next_qtr: DeltaPoint
    
    # Revision Velocity
    eps_revision_90d: DeltaPoint
    revenue_revision_90d: DeltaPoint
    
    target_price_high: DataPoint
    target_price_low: DataPoint
    target_price_median: DataPoint
    target_price_spread_pct: Optional[float] = Field(default=None, description="Auto-calculated.")
    
    analyst_coverage_count: DataPoint

    @model_validator(mode="after")
    def calculate_spread(self) -> 'ConsensusInput':
        high = self.target_price_high.value
        low = self.target_price_low.value
        median = self.target_price_median.value
        
        if isinstance(high, (int, float)) and isinstance(low, (int, float)) and isinstance(median, (int, float)):
            if median > 0:
                self.target_price_spread_pct = ((high - low) / median) * 100.0
        return self

# ---------------------------------------------------------
# 4. Institutional Flow (Now with Ownership Change)
# ---------------------------------------------------------
class InstitutionalInput(DomainContract):
    institutional_ownership_pct: DeltaPoint
    institutional_ownership_change_90d: DeltaPoint  # The flow trajectory
    short_interest_pct: DeltaPoint
    insider_net_buying_6m: DataPoint

# ---------------------------------------------------------
# 5. Research Fundamentals (Now with Unit Econ & Sector Extensibility)
# ---------------------------------------------------------
class ResearchInput(DomainContract):
    business_model: DataPoint
    revenue_segments: DataPoint
    competitive_landscape: DataPoint
    management_capital_allocation: DataPoint
    sec_risk_factors: DataPoint
    
    # The new granular primitives
    unit_economics: DataPoint
    
    # Sector Specifics (e.g., {"gpu_supply": DataPoint(...), "datacenter_growth": DataPoint(...)})
    sector_specific_metrics: Dict[str, DataPoint] = Field(default_factory=dict)