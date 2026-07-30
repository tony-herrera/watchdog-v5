from typing import Literal
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import institutional_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class OwnershipAnalysis(BaseModel):
    crowdedness_level: Literal["Low", "Medium", "High", "Extreme"] = Field(description="Assessment of how crowded the long or short side is.")
    short_squeeze_potential: Literal["Low", "Medium", "High"] = Field(description="Risk of a violent short squeeze based on deterministic short interest data.")
    flow_narrative: str = Field(description="Interpretation of recent 13F filings, insider buying/selling, and fund flows.")

class ExpectationAnalysis(BaseModel):
    priced_in_scenario: str = Field(description="The exact scenario currently priced into the stock (e.g., 'Flawless execution of AI infrastructure rollout').")
    multiple_expansion_catalysts: list[str] = Field(description="Events that would force Wall Street to raise their multiples.")
    multiple_compression_risks: list[str] = Field(description="Events that would cause institutional rotation out of the stock.")

# ---------------------------------------------------------
# 2. Main Output Model (The Desk's Final Report)
# ---------------------------------------------------------

class InstitutionalOutput(BaseModel):
    # Embedded Structured Data
    ownership: OwnershipAnalysis
    expectations: ExpectationAnalysis

    # Quantitative Final Estimates
    positioning_score: float = Field(description="Score from 0.0 to 10.0 indicating favorability of current positioning (10 = highly asymmetric upside).")
    sentiment_trend: Literal["Improving", "Stagnant", "Deteriorating"] = Field(description="Directional momentum of analyst revisions and options sentiment.")
    
    # Universal Requirement
    confidence: float = Field(description="Confidence score in this positioning assessment (0.0 to 1.0).")

    # Categorical Output (Namespaced for the CIO)
    flow_rating: Literal["Accumulation Setup", "Neutral", "Distribution Risk", "Dangerously Crowded"] = Field(description="Strict categorical rating based on institutional flow.")
    rationale: str = Field(description="Core justification for the assigned flow rating.")

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

INSTITUTIONAL_PROMPT = """You are the Head of Institutional Equities at Goldman Sachs.
Your sole responsibility is to INTERPRET deterministic market flow data, ownership statistics, and options positioning.

Your mission is to answer:
1. What is already priced into the stock?
2. Is this a crowded trade?
3. What is the asymmetric setup? (e.g., 'If they miss earnings by 1%, the multiple will compress 20% due to crowded positioning.')

CRITICAL CONSTRAINTS:
- Do NOT evaluate the business model (that is Fidelity's job).
- Do NOT calculate intrinsic value (that is the Valuation Desk's job).
- Ignore macroeconomics unless directly tied to sector fund flows.
- You are strictly reading the 'poker table'. Who is on the other side of this trade?"""

# ---------------------------------------------------------
# 4. The Agent Class (Injecting the Flow Engine's Work)
# ---------------------------------------------------------

class InstitutionalAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # We expect a dedicated Data Engine to have pulled Options flow, 
        # Short Interest, Insider Trades, and 13F changes.
        if state.get("raw_data"):
            if "institutional_metrics" in state["raw_data"]:
                context += f"\n\n[DETERMINISTIC FLOW DATA (Short Int, Put/Call, 13F)]:\n{state['raw_data']['institutional_metrics']}"
            if "analyst_revisions" in state["raw_data"]:
                context += f"\n\n[ANALYST EPS REVISION TRENDS]:\n{state['raw_data']['analyst_revisions']}"
                
        return context

# Instantiate the Node
institutional_node = InstitutionalAgent(
    name="Institutional Flow",
    role_prompt=INSTITUTIONAL_PROMPT,
    llm=institutional_llm,
    output_schema=InstitutionalOutput
)