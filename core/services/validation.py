import yaml
from datetime import datetime
from typing import List, Tuple, Dict, Any
from core.contracts.stock import (
    StockNormalizedData, 
    ValidationMetadata, 
    ValidationEvent,
    ValidationSeverity,
    ValidationEventType,
    DataStatus,
    ConfidenceAssessment
)
from core.contracts.domain import ValuationInput, ConsensusInput, ResearchInput, InstitutionalInput
from core.contracts.common import DataPoint

class DataValidationService:
    """
    The strict 4D Gatekeeper. Evaluates Completeness, Freshness, 
    Source Trust, and Sanity/Agreement before the LLMs see the data.
    """
    def __init__(self, config_path: str = "core/config/validation_weights.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.source_trust = self.config.get("source_confidence", {})

    # ---------------------------------------------------------
    # 1. Core Dimension Checks
    # ---------------------------------------------------------
    def _check_freshness(self, timestamp: Any) -> Tuple[float, Optional[ValidationEvent]]:
        """Calculates decay penalty based on data age."""
        # Handle both string (JSON parsed) and datetime (Pydantic objects)
        if isinstance(timestamp, str):
            parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            parsed_time = timestamp

        age_days = (datetime.utcnow() - parsed_time.replace(tzinfo=None)).days
        
        if age_days > 90:
            return 0.0, ValidationEvent(
                type=ValidationEventType.STALE_DATA, field="Multiple", 
                severity=ValidationSeverity.HIGH, message=f"Data is {age_days} days old."
            )
        elif age_days > 30:
            return 0.5, ValidationEvent(
                type=ValidationEventType.STALE_DATA, field="Multiple", 
                severity=ValidationSeverity.MEDIUM, message=f"Data is {age_days} days old."
            )
        return 1.0, None

    def _sanity_check_number(self, point: DataPoint, field_name: str, min_val: float, max_val: float) -> Optional[ValidationEvent]:
        """Prevents statistically absurd numbers from entering the agent context."""
        val = point.value
        if val is None:
            return None
            
        if not isinstance(val, (int, float)):
            return ValidationEvent(
                type=ValidationEventType.SANITY_FAILED, field=field_name, 
                severity=ValidationSeverity.CRITICAL, message=f"{field_name} must be a number."
            )

        if val < min_val or val > max_val:
            return ValidationEvent(
                type=ValidationEventType.SANITY_FAILED, field=field_name, 
                severity=ValidationSeverity.CRITICAL, 
                message=f"{field_name} ({val}) is outside plausible bounds [{min_val}, {max_val}]."
            )
        return None

    # ---------------------------------------------------------
    # 2. Domain Evaluators
    # ---------------------------------------------------------
    def _evaluate_valuation(self, val: ValuationInput) -> Tuple[float, List[ValidationEvent], Dict[str, float]]:
        events = []
        
        # A. Sanity Checks (Blockers)
        sanity_event = self._sanity_check_number(val.forward_pe.current, "forward_pe", 0.0, 500.0)
        if sanity_event: events.append(sanity_event)

        # B. Freshness
        freshness, fresh_event = self._check_freshness(val.forward_pe.current.timestamp)
        if fresh_event: events.append(fresh_event)

        # C. Source Trust
        source = val.forward_pe.current.source
        trust = self.source_trust.get(source, 0.5)
        if trust < 0.8:
            events.append(ValidationEvent(
                type=ValidationEventType.LOW_TRUST_SOURCE, field="forward_pe", 
                severity=ValidationSeverity.LOW, message=f"Source {source} is low confidence."
            ))

        # D. Completeness
        completeness = 1.0 if val.forward_pe.historical_90d.value else 0.5
        
        # E. Agreement (Mocked for single-source currently, defaults to 1.0)
        agreement = 1.0

        # Calculate Breakdown
        score = (completeness * 0.35) + (trust * 0.25) + (freshness * 0.20) + (agreement * 0.20)
        breakdown = {"completeness": completeness, "source_trust": trust, "freshness": freshness, "agreement": agreement}
        
        return score, events, breakdown

    def _evaluate_consensus(self, con: ConsensusInput) -> Tuple[float, List[ValidationEvent], Dict[str, float]]:
        events = []
        score = 1.0
        
        coverage = con.analyst_coverage_count.value
        if coverage is None or coverage < 5:
            score -= 0.3
            events.append(ValidationEvent(
                type=ValidationEventType.MISSING_FIELD, field="analyst_coverage_count", 
                severity=ValidationSeverity.MEDIUM, message="Low analyst coverage (<5). Street baseline is murky."
            ))

        spread = con.target_price_spread_pct
        if spread is not None and spread > 50.0:
            score -= 0.2
            events.append(ValidationEvent(
                type=ValidationEventType.SANITY_FAILED, field="target_price_spread_pct", 
                severity=ValidationSeverity.MEDIUM, message="Target price dispersion > 50%. High uncertainty."
            ))
            
        breakdown = {"completeness": score, "source_trust": 0.85, "freshness": 1.0, "agreement": 1.0} # Simplified
        return max(0.0, score), events, breakdown

    def _evaluate_research(self, res: ResearchInput) -> Tuple[float, List[ValidationEvent], Dict[str, float]]:
        events = []
        score = 1.0
        
        if res.sec_risk_factors.value is None:
            score -= 0.4
            events.append(ValidationEvent(
                type=ValidationEventType.MISSING_FIELD, field="sec_risk_factors", 
                severity=ValidationSeverity.HIGH, message="SEC Risk Factors unavailable. Fundamental blindspot."
            ))
            
        breakdown = {"completeness": score, "source_trust": 1.0, "freshness": 1.0, "agreement": 1.0}
        return max(0.0, score), events, breakdown

    # ---------------------------------------------------------
    # 3. The Main Pipeline Orchestrator
    # ---------------------------------------------------------
    def validate_pipeline(
        self, 
        ticker: str, 
        run_id: str,
        sector: str = "General", 
        valuation: ValuationInput = None, 
        consensus: ConsensusInput = None,
        research: ResearchInput = None,
        institutional: InstitutionalInput = None
    ) -> StockNormalizedData:
        
        print(f"🛡️ [Validation Engine] Running 4D Audit for {ticker}...")
        
        all_events = []
        weights = self.config["sector_weights"].get(sector, self.config["sector_weights"]["General"])
        
        # 1. Run Domain Evaluators
        val_score, val_events, val_breakdown = self._evaluate_valuation(valuation) if valuation else (0.0, [], {})
        con_score, con_events, con_breakdown = self._evaluate_consensus(consensus) if consensus else (0.0, [], {})
        res_score, res_events, res_breakdown = self._evaluate_research(research) if research else (0.0, [], {})
        
        all_events.extend(val_events + con_events + res_events)

        # 2. Compile Confidences
        val_conf = ConfidenceAssessment(score=round(val_score, 2), reasons=[f"{k}: {v}" for k, v in val_breakdown.items()])
        con_conf = ConfidenceAssessment(score=round(con_score, 2), reasons=[f"{k}: {v}" for k, v in con_breakdown.items()])
        res_conf = ConfidenceAssessment(score=round(res_score, 2), reasons=[f"{k}: {v}" for k, v in res_breakdown.items()])

        # 3. Calculate Global Quality Score
        quality_score = (
            (val_score * weights.get("valuation", 0.0)) + 
            (con_score * weights.get("consensus", 0.0)) + 
            (res_score * weights.get("research", 0.0))
        )

        # 4. Routing Logic (Warnings vs. Blockers)
        has_critical = any(e.severity == ValidationSeverity.CRITICAL for e in all_events)
        has_high = any(e.severity == ValidationSeverity.HIGH for e in all_events)
        
        status = DataStatus.VALIDATED
        failure_reason = None
        
        if has_critical or quality_score < 0.4:
            status = DataStatus.FAILED
            failure_reason = "Critical sanity check failed or Global Quality < 0.4"
            quality_score = 0.0
        elif has_high or quality_score < 0.85:
            status = DataStatus.PARTIAL

        # 5. Build Final Immutable Contract
        return StockNormalizedData(
            run_id=run_id,
            ticker=ticker,
            sector=sector,
            status=status,
            failure_reason=failure_reason,
            data_quality_score=round(quality_score, 2),
            overall_confidence=round(quality_score, 2), # Can be adjusted by LLM later
            valuation_confidence=val_conf,
            consensus_confidence=con_conf,
            research_confidence=res_conf,
            validation_metadata=ValidationMetadata(events=all_events),
            valuation=valuation,
            consensus=consensus,
            research=research,
            institutional=institutional
        )