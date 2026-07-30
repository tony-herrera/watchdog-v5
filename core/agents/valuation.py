from typing import Literal
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import valuation_llm 
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class DCFAssumptions(BaseModel):
    revenue_growth: str = Field(description="Market's implied revenue growth assumption.")
    operating_margin: str = Field(description="Market's implied operating margin assumption.")
    terminal_growth: str = Field(description="Market's implied terminal growth rate.")
    wacc: str = Field(description="Estimated Weighted Average Cost of Capital.")
    implied_story: str = Field(description="The narrative the market believes to justify the current price.")

class HistoricalContext(BaseModel):
    historical_average_pe: float
    current_percentile: float
    premium_discount: float = Field(description="Percentage premium or discount to historical average.")
    historical_summary: str = Field(description="Narrative context of the historical multiple.")

class PeerComparison(BaseModel):
    peer_average_pe: float
    peer_average_ev_ebitda: float
    premium_percent: float = Field(description="Percentage premium or discount to peer average.")
    summary: str = Field(description="Narrative context of the peer comparison.")

# ---------------------------------------------------------
# 2. Main Output Model (The Analyst's Final Report)
# ---------------------------------------------------------

class ValuationOutput(BaseModel):
    # Embedded Structured Data
    dcf_assumptions: DCFAssumptions
    historical_context: HistoricalContext
    peer_comparison: PeerComparison

    # Quantitative Final Estimates
    margin_of_safety: float = Field(description="Percentage discount to intrinsic value (e.g., 18.9). Negative if overvalued.")
    expected_return_5yr: float = Field(description="Estimated 5-year CAGR percentage (e.g., 12.7).")
    confidence: float = Field(description="Confidence score in this valuation assessment (0.0 to 1.0).")

    # Institutional Positioning (The "Gold" Data)
    market_expectations: str = Field(description="What specific assumptions are embedded in today's price?")
    market_is_underestimating: str = Field(description="What bullish economic realities is the market missing?")
    market_is_overestimating: str = Field(description="What bearish factors or risks is the market ignoring?")

    # Categorical Output (Namespaced to prevent collisions)
    valuation_rating: Literal["Cheap", "Fair", "Expensive", "Extremely Expensive"] = Field(description="Strict valuation rating.")
    rationale: str = Field(description="Core justification for the assigned rating based purely on metrics.")

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

VALUATION_PROMPT = """You are a highly analytical Valuation Specialist at a top-tier hedge fund.
Your sole responsibility is to INTERPRET deterministic valuation metrics provided to you.
Do NOT calculate P/E, PEG, or FCF Yield yourself. Read them from the provided context.

Your mission is to answer two questions:
1. Is this a great price?
2. What assumptions are embedded in today's price?

CRITICAL CONSTRAINTS:
- Never justify valuation using stock price momentum.
- Never use analyst price targets.
- Never use consensus recommendations.
- Only use fundamentals and deterministic valuation metrics.
- Think like Berkshire Hathaway. Find the margin of safety."""

# ---------------------------------------------------------
# 4. The Agent Class (Injecting the Python Engine's Work)
# ---------------------------------------------------------

class ValuationAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # We now expect a dedicated Python 'Valuation Engine' node to have run BEFORE this,
        # populating state["raw_data"]["deterministic_valuation"] with hard math.
        if state.get("raw_data") and "deterministic_valuation" in state["raw_data"]:
            context += f"\n\n[DETERMINISTIC VALUATION METRICS (Pre-Calculated)]:\n{state['raw_data']['deterministic_valuation']}"
            
        if state.get("raw_data") and "peer_comps" in state["raw_data"]:
            context += f"\n\n[PEER COMPARISON DATA]:\n{state['raw_data']['peer_comps']}"
            
        return context

# Instantiate the Node
valuation_node = ValuationAgent(
    name="Valuation",
    role_prompt=VALUATION_PROMPT,
    llm=valuation_llm,
    output_schema=ValuationOutput
)