from typing import Literal, List
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import institutional_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class OwnershipAnalysis(BaseModel):
    # The LLM extracts these directly from the deterministic Data Layer
    # for downstream Portfolio Manager consumption.
    institutional_ownership_pct: float = Field(description="Extract directly from deterministic data. Do not invent.")
    insider_activity: str = Field(description="Interpretation of insider buying/selling trends.")
    hedge_fund_activity: str = Field(description="Interpretation of smart money 13F flows.")
    passive_vs_active: str = Field(description="Analysis of passive ETF holding vs active stock picking.")

class MarketExpectations(BaseModel):
    revenue_growth_expected: str = Field(description="Specific revenue growth explicitly priced in.")
    eps_growth_expected: str = Field(description="Specific EPS growth explicitly priced in.")
    margin_expectation: str = Field(description="What the street assumes about future margins.")
    ai_expectation: str = Field(description="What execution/growth is expected regarding AI/Tech themes.")
    pricing_assumption: str = Field(description="What multiples/valuations Wall Street expects to persist.")

class Asymmetry(BaseModel):
    upside_trigger: str = Field(description="Specific catalyst that forces a re-rating higher.")
    downside_trigger: str = Field(description="Specific catalyst that breaks the thesis.")
    upside_magnitude: str = Field(description="Estimated magnitude of the upside move (e.g., '+20% on multiple expansion').")
    downside_magnitude: str = Field(description="Estimated magnitude of downside risk (e.g., '-40% to historical base').")

# ---------------------------------------------------------
# 2. Main Output Model (The Prime Brokerage Report)
# ---------------------------------------------------------

class InstitutionalOutput(BaseModel):
    # Embedded Structured Data
    ownership: OwnershipAnalysis
    expectations: MarketExpectations
    asymmetry: Asymmetry

    # The Alpha Generators ⭐⭐⭐⭐⭐
    expectation_gap: Literal["Positive", "Neutral", "Negative"] = Field(description="Reality vs Consensus. Positive means Reality > Consensus.")
    wall_street_is_wrong_about: str = Field(description="The single biggest mispricing in Wall Street's current narrative.")
    rotation_probability: float = Field(description="Probability (0.0 to 1.0) of institutional capital rotating INTO or OUT OF this stock.")
    time_horizon: Literal["Next Earnings", "12 Months", "3 Years"] = Field(description="The timeframe for which this positioning setup is most relevant.")

    # Surprise Modeling
    positive_surprises: List[str] = Field(description="Specific events that would catch consensus off-guard to the upside.")
    negative_surprises: List[str] = Field(description="Specific events that would catch consensus off-guard to the downside.")

    # Split Confidence Metrics
    data_confidence: float = Field(description="Confidence (0.0 to 1.0) in the raw data provided (e.g., missing 13Fs lowers this).")
    analysis_confidence: float = Field(description="Confidence (0.0 to 1.0) in the interpretation of the setup.")


# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

INSTITUTIONAL_PROMPT = """You are the Head of Prime Brokerage Strategy and Institutional Positioning.
Your clients are top-tier hedge funds.
Your responsibility is NOT to determine whether a company is good. 

Your responsibility is to determine:
1. What expectations are priced in.
2. What expectations are wrong.
3. Where institutional capital is most likely to flow.

CRITICAL CONSTRAINTS:
- Ignore valuation (that is the Valuation Desk's job).
- Ignore management quality (Fidelity handles that).
- Focus entirely on expectations versus reality.
- NEVER invent numeric data (Short Interest, Institutional %). Extract them exactly from the Data Layer context.
- Your goal is to identify asymmetric setups and crowded trades."""

# ---------------------------------------------------------
# 4. The Agent Class 
# ---------------------------------------------------------

class InstitutionalAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # Pulling purely from the deterministic Data Layer and the new Consensus Agent
        if state.get("raw_data"):
            if "institutional_metrics" in state["raw_data"]:
                context += f"\n\n[DETERMINISTIC FLOW DATA]:\n{state['raw_data']['institutional_metrics']}"
            if "consensus_estimates" in state["raw_data"]:
                context += f"\n\n[CONSENSUS ESTIMATES (Whisper & Target)]:\n{state['raw_data']['consensus_estimates']}"
                
        return context

# Instantiate the Node
institutional_node = InstitutionalAgent(
    name="Institutional Flow",
    role_prompt=INSTITUTIONAL_PROMPT,
    llm=institutional_llm,
    output_schema=InstitutionalOutput
)