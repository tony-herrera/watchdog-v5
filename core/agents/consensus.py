from typing import Literal, List
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import consensus_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class RevisionMomentum(BaseModel):
    trend: Literal["Strongly Upward", "Upward", "Flat", "Downward", "Strongly Downward"] = Field(description="The directional momentum of EPS and Revenue revisions over the last 90 days.")
    magnitude: str = Field(description="How severe are the revisions? (e.g., 'EPS cut by 15% across the board').")
    driver: str = Field(description="The fundamental reason analysts are citing for these revisions (if determinable from context).")

class PriceTargetAnalysis(BaseModel):
    dispersion: Literal["Tight Consensus", "Moderate Dispersion", "Wide Disagreement"] = Field(description="How clustered are the analyst price targets? Wide disagreement implies high uncertainty.")
    implied_upside_to_median: str = Field(description="The percentage gap between current price and median target (e.g., '+12%').")
    bull_bear_skew: str = Field(description="Is the current price closer to the lowest bear target or the highest bull target?")

class EarningsSetup(BaseModel):
    official_consensus: str = Field(description="The official EPS and Revenue estimates for the next print.")
    whisper_setup: str = Field(description="Interpretation of the 'whisper number' or buy-side expectations relative to the official sell-side consensus.")
    bar_to_clear: Literal["Very Low", "Low", "Normal", "High", "Priced for Perfection"] = Field(description="How difficult will it be for the company to impress the street?")

# ---------------------------------------------------------
# 2. Main Output Model (The Analyst Consensus Report)
# ---------------------------------------------------------

class ConsensusOutput(BaseModel):
    revisions: RevisionMomentum
    targets: PriceTargetAnalysis
    earnings_setup: EarningsSetup

    # The Synthesis
    street_sentiment: Literal["Extremely Bullish", "Bullish", "Mixed/Neutral", "Bearish", "Capitulation"] = Field(description="Overall sentiment of the sell-side analyst community.")
    contrarian_setup: str = Field(description="If the street is 'Extremely Bullish', what is the contrarian bear case? If 'Capitulation', what is the contrarian bull case?")
    
    confidence: float = Field(description="Confidence (0.0 to 1.0) in this consensus read.")

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

CONSENSUS_PROMPT = """You are the Director of Equity Research Strategy.
Your job is to read deterministic data regarding sell-side analyst estimates, price targets, and earnings revisions.

Your mission is to establish the 'Baseline Expectation' of Wall Street.
1. Are analysts upgrading or downgrading?
2. How high is the bar for the next earnings print?
3. Is there wide disagreement (dispersion) or are all analysts huddled around the same thesis?

CRITICAL CONSTRAINTS:
- Do NOT evaluate if the stock is a good investment.
- Do NOT evaluate valuation multiples.
- Do NOT evaluate institutional fund flows (The Prime Brokerage desk handles that).
- Your output must simply establish EXACTLY what Wall Street expects to happen."""

# ---------------------------------------------------------
# 4. The Agent Class 
# ---------------------------------------------------------

class ConsensusAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # Pulling purely from the deterministic Data Layer
        if state.get("raw_data"):
            if "analyst_estimates" in state["raw_data"]:
                context += f"\n\n[SELL-SIDE ESTIMATES (EPS/Rev)]:\n{state['raw_data']['analyst_estimates']}"
            if "estimate_revisions" in state["raw_data"]:
                context += f"\n\n[90-DAY REVISION HISTORY]:\n{state['raw_data']['estimate_revisions']}"
            if "price_targets" in state["raw_data"]:
                context += f"\n\n[PRICE TARGET DISPERSION]:\n{state['raw_data']['price_targets']}"
                
        return context

# Instantiate the Node
consensus_node = ConsensusAgent(
    name="Consensus",
    role_prompt=CONSENSUS_PROMPT,
    llm=consensus_llm,
    output_schema=ConsensusOutput
)