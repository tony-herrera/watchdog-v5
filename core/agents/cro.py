from typing import Literal, List
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import cro_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Governance Contract)
# ---------------------------------------------------------

class Scenario(BaseModel):
    probability_pct: int = Field(description="Integer 0-100. Bull, Base, and Bear MUST sum to 100.")
    price_movement_estimate_pct: float = Field(description="Estimated percentage move (e.g., 25.0 for upside, -40.0 for downside).")
    confidence: Literal["High", "Moderate", "Low"] = Field(description="Confidence in this specific scenario occurring.")
    narrative_trigger: str = Field(description="The exact chain of events that triggers this scenario (e.g., 'CapEx slows -> Multiple compresses -> EPS miss').")

class ScenarioMatrix(BaseModel):
    bull_case: Scenario
    base_case: Scenario
    bear_case: Scenario

class CapitalPreservation(BaseModel):
    permanent_loss_risk: Literal["Negligible", "Low", "Moderate", "High", "Extreme"] = Field(
        description="Risk of permanent capital impairment (bankruptcy or >70% structural decline), distinct from standard drawdowns."
    )
    unmodelable_risk: str = Field(
        description="The biggest 'Black Swan' or unquantifiable risk (e.g., 'Taiwan geopolitical conflict', 'Regulatory ban')."
    )

class StressTest(BaseModel):
    inflation_shock: Literal["Severe", "Moderate", "Minor", "Beneficial"]
    interest_rate_shock: Literal["Severe", "Moderate", "Minor", "Beneficial"]
    recession: Literal["Severe", "Moderate", "Minor", "Beneficial"]
    sector_capex_slowdown: Literal["Severe", "Moderate", "Minor", "Beneficial"]
    credit_tightening: Literal["Severe", "Moderate", "Minor", "Beneficial"]

class InvalidationRule(BaseModel):
    metric: str = Field(description="The exact KPI to monitor (e.g., 'Gross Margin', 'Revenue Growth').")
    threshold: str = Field(description="The numeric threshold that breaks the thesis (e.g., '< 48%').")
    duration: str = Field(description="How long it must persist to trigger a sell (e.g., '2 consecutive quarters').")

# ---------------------------------------------------------
# 2. Main Output Model (The Risk Framework)
# ---------------------------------------------------------

class CROOutput(BaseModel):
    scenarios: ScenarioMatrix
    capital_preservation: CapitalPreservation
    stress_tests: StressTest
    thesis_invalidation_rules: List[InvalidationRule]

    # The Sizing Hook for the Portfolio Manager
    risk_budget_tier: Literal[
        "Tier 1 (Core Compounder / Low Risk)", 
        "Tier 2 (Standard Allocation / Moderate Risk)", 
        "Tier 3 (Satellite / Elevated Risk)", 
        "Tier 4 (Speculative / Strictly Capped)"
    ] = Field(description="Classification of risk to govern maximum portfolio sizing.")

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

CRO_PROMPT = """You are the Chief Risk Officer (CRO) of an elite institutional fund.
You are reviewing the complete fundamental dossier (Layer 2) and the Red Team attack (Layer 3) for a prospective asset.

CRITICAL CONSTRAINTS:
- You are FORBIDDEN from making investment recommendations.
- You do NOT decide whether the stock is purchased; that is the Portfolio Manager's job.
- Your sole responsibility is to quantify uncertainty, structure downside scenarios, and define strict thesis invalidation rules.
- Do NOT calculate expected CAGR. Provide the probability and percentage movement for the scenarios; downstream quantitative systems will compute Expected Value.
- Assume things will go wrong. Protect the fund's capital."""

# ---------------------------------------------------------
# 4. The Agent Class (Consuming Layers 2 & 3)
# ---------------------------------------------------------

class CROAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # The CRO consumes EVERYTHING to build the full risk matrix
        context += "\n\n=== LAYER 2: FUNDAMENTAL SETUP ==="
        if state.get("research"): context += f"\n\n[RESEARCH]:\n{state['research']}"
        if state.get("valuation"): context += f"\n\n[VALUATION]:\n{state['valuation']}"
        if state.get("consensus"): context += f"\n\n[CONSENSUS]:\n{state['consensus']}"
        if state.get("expectations"): context += f"\n\n[FLOWS]:\n{state['expectations']}"
        if state.get("macro"): context += f"\n\n[MACRO]:\n{state['macro']}"
            
        context += "\n\n=== LAYER 3: ADVERSARIAL STRESS TEST ==="
        if state.get("red_team"): context += f"\n\n[RED TEAM TAKEDOWN]:\n{state['red_team']}"
            
        return context

# Instantiate the Node
cro_node = CROAgent(
    name="Chief Risk Officer",
    role_prompt=CRO_PROMPT,
    llm=cro_llm,
    output_schema=CROOutput
)