from typing import Literal
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import red_team_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Stress Tests)
# ---------------------------------------------------------

class BusinessRisk(BaseModel):
    thesis_dependency: str = Field(description="The core operational assumption the entire bull thesis depends on (e.g., 'AI CapEx remains elevated').")
    weakest_business_pillar: str = Field(description="The most fragile part of the company's revenue model or moat.")
    management_blindspot: str = Field(description="What the executive team is ignoring or misallocating capital toward.")
    competition_threat: str = Field(description="Exactly how a competitor could commoditize this business based on Research data.")

class ValuationRisk(BaseModel):
    required_assumption: str = Field(description="The specific mathematical assumption (e.g., '35% CAGR for 10 years') required to justify the current multiple.")
    assumption_plausibility: Literal["Reasonable", "Aggressive", "Very Aggressive", "Implausible"] = Field(
        description="Assessment of the required assumption based on historical/peer context."
    )
    multiple_compression_catalyst: str = Field(description="The specific event that will cause Wall Street to aggressively slash the multiple.")
    expected_market_reaction: Literal["Minor", "Moderate", "Severe"] = Field(
        description="If the compression catalyst occurs, how violently will the stock re-rate?"
    )

class ExternalRisk(BaseModel):
    macro_kill_switch: str = Field(description="The exact macroeconomic shift that would destroy this setup. MUST BE CITED directly from the Macro report.")
    unwind_risk: Literal["Extreme", "High", "Moderate", "Low"] = Field(
        description="Risk of a violent institutional sell-off. MUST BE DERIVED directly from the Institutional report's crowdedness metrics."
    )

# ---------------------------------------------------------
# 2. Main Output Model (The Red Team Report)
# ---------------------------------------------------------

class RedTeamOutput(BaseModel):
    # The TL;DR for the Portfolio Manager goes at the TOP
    fatal_flaw: str = Field(
        description="The single biggest point of failure in the prevailing thesis. If this breaks, the stock collapses."
    )
    primary_bear_thesis: str = Field(
        description="A ruthless, 2-to-3 sentence summary of why owning this stock is a trap. Do not exceed 3 sentences."
    )

    # Component Stress Tests
    business_risk: BusinessRisk
    valuation_risk: ValuationRisk
    external_risk: ExternalRisk

    # The PM Routing Hooks ⭐⭐⭐⭐⭐
    risk_severity: Literal["Low", "Moderate", "Elevated", "Critical"] = Field(
        description="Overall severity of the identified structural risks."
    )
    bear_case_strength_score: int = Field(
        description="Score from 0 to 100 indicating how strong/likely the bear thesis is based purely on the evidence."
    )

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

RED_TEAM_PROMPT = """You are the Lead Red Team Analyst for an elite Investment Committee.
You are about to read 5 highly detailed reports (Research, Valuation, Consensus, Institutional, Macro) about a stock.

Assume the prevailing bull thesis is incomplete. Your job is to stress-test it and identify:
- Hidden assumptions
- Nonlinear risks
- Overlooked competition
- Regime changes
- Second-order effects

CRITICAL CONSTRAINTS:
- Use EVIDENCE from the provided reports. Do not invent unsupported risks.
- For Macro risks, you MUST cite the Macro report. Do not manufacture an oil shock if oil isn't mentioned.
- For Unwind Risk, you MUST derive it from the Institutional report's crowdedness and positioning metrics.
- Be ruthless, objective, and analytical. If the company is fundamentally flawless but wildly overvalued, focus your attack purely on valuation."""

# ---------------------------------------------------------
# 4. The Agent Class (The Layer 3 Consumer)
# ---------------------------------------------------------

class RedTeamAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # The Red Team only consumes Layer 2 Normalized Outputs, not raw data.
        context += "\n\n=== LAYER 2 ANALYSIS REPORTS ==="
        
        # Safely pull from the strict StockState keys defined earlier
        if state.get("research"):
            context += f"\n\n[FUNDAMENTAL RESEARCH]:\n{state['research']}"
        if state.get("valuation"):
            context += f"\n\n[VALUATION DESK]:\n{state['valuation']}"
        if state.get("consensus"): # Assuming Consensus Agent writes to 'consensus' key
            context += f"\n\n[STREET CONSENSUS]:\n{state['consensus']}"
        if state.get("expectations"): # Institutional Flow Agent's key
            context += f"\n\n[INSTITUTIONAL POSITIONING]:\n{state['expectations']}"
        if state.get("macro"):
            context += f"\n\n[MACROECONOMIC SETUP]:\n{state['macro']}"
            
        return context

# Instantiate the Node
red_team_node = RedTeamAgent(
    name="Red Team",
    role_prompt=RED_TEAM_PROMPT,
    llm=red_team_llm,
    output_schema=RedTeamOutput
)