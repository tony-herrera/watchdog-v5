from typing import Literal
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import consensus_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class RevisionMomentum(BaseModel):
    trend: Literal["Strongly Upward", "Upward", "Flat", "Downward", "Strongly Downward"] = Field(description="Direction of EPS/Rev revisions over the last 90 days.")
    magnitude: str = Field(description="Severity of revisions (e.g., 'EPS up 8%').")
    analyst_breadth: Literal["Broad Based", "Moderate", "Narrow", "Unknown"] = Field(description="Are many analysts revising, or just one outlier?")
    revision_count: str = Field(description="Ratio or number of upward vs downward estimate revisions.")
    driver: str = Field(description="The primary fundamental reason for the revisions.")

class PriceTargetAnalysis(BaseModel):
    dispersion: Literal["Tight Consensus", "Moderate Dispersion", "Wide Disagreement"] = Field(description="Clustering of price targets.")
    median_target_upside_pct: float = Field(description="Percentage gap from current price to median target. Extract from data layer, do not calculate.")
    high_low_spread_pct: float = Field(description="Percentage spread between highest and lowest target. Extract from data layer.")
    skew: Literal["Bullish Skew", "Neutral", "Bearish Skew"] = Field(description="Is the current price trading closer to the street's high or low target?")

class EarningsSetup(BaseModel):
    official_consensus: str = Field(description="The explicit EPS and Revenue estimates for the next print.")
    bar_to_clear: Literal["Very Low", "Low", "Normal", "High", "Priced for Perfection"] = Field(description="How difficult it is for the company to impress the street.")
    earnings_surprise_risk: Literal["Low", "Moderate", "High"] = Field(description="Risk of a negative surprise given current expectations and comps.")

class ConsensusConfidence(BaseModel):
    score: float = Field(description="Confidence from 0.0 to 1.0.")
    reasoning: Literal[
        "High analyst coverage", 
        "Limited analyst coverage", 
        "Stale estimates", 
        "Conflicting data"
    ] = Field(description="The primary reason for this confidence score.")

# ---------------------------------------------------------
# 2. Main Output Model (The Consensus Report)
# ---------------------------------------------------------

class ConsensusOutput(BaseModel):
    revisions: RevisionMomentum
    targets: PriceTargetAnalysis
    earnings_setup: EarningsSetup

    # The Alpha Signals ⭐⭐⭐⭐⭐
    expectation_vs_price: Literal[
        "Expectations Improving Faster Than Price",
        "Price Leading Expectations",
        "Aligned",
        "Unknown"
    ] = Field(description="Are estimate revisions outpacing the stock's actual price movement?")
    
    contrarian_setup: str = Field(description="What is the contrarian trade against the current consensus?")

    # Calibrated Quantitative Sentiment
    street_sentiment_score: int = Field(
        description="Score from -100 (Extremely Bearish) to +100 (Extremely Bullish) based on target upside and revision breadth."
    )

    confidence: ConsensusConfidence

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

CONSENSUS_PROMPT = """You are the Director of Equity Research Strategy.
Your job is to read deterministic data regarding sell-side analyst estimates, price targets, and earnings revisions.

Your mission is to establish EXACTLY what the market already believes.

CRITICAL CONSTRAINTS:
- Do NOT evaluate if the stock is a good investment.
- Do NOT evaluate valuation multiples.
- You are producing an input for a Portfolio Manager agent. 
- Do NOT make recommendations. 
- Do NOT use adjectives implying attractiveness (e.g., 'great opportunity').
- Your entire existence is to quantify the Street's baseline expectations so downstream agents can determine if the Street is wrong."""

# ---------------------------------------------------------
# 4. The Agent Class 
# ---------------------------------------------------------

class ConsensusAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # Moving toward V5 Normalized Data Consumption
        # Assuming the Python Data Engine has injected a clean `normalized_consensus` JSON object
        if state.get("raw_data") and "normalized_consensus" in state["raw_data"]:
            context += f"\n\n[NORMALIZED CONSENSUS DATA]:\n{state['raw_data']['normalized_consensus']}"
        elif state.get("raw_data") and "analyst_estimates" in state["raw_data"]:
            # Fallback for un-normalized data if the pipeline hasn't caught up
            context += f"\n\n[SELL-SIDE ESTIMATES]:\n{state['raw_data']['analyst_estimates']}"
            
        return context

# Instantiate the Node
consensus_node = ConsensusAgent(
    name="Consensus",
    role_prompt=CONSENSUS_PROMPT,
    llm=consensus_llm,
    output_schema=ConsensusOutput
)