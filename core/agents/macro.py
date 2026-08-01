from typing import Literal, List
from pydantic import BaseModel, Field
from core.agents.base_agent import BaseAgent
from core.llm import macro_llm
from core.state import StockState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Data Contract)
# ---------------------------------------------------------

class Theme(BaseModel):
    name: str = Field(description="Name of the macro theme (e.g., 'AI Infrastructure Buildout').")
    impact: Literal["Major", "Moderate", "Minor"]
    duration: Literal["Short-term", "Medium-term", "Long-term", "Secular"]

class RateSensitivity(BaseModel):
    sensitivity_level: Literal["Extremely High", "High", "Moderate", "Low", "Beneficiary"]
    primary_driver: Literal[
        "High Debt / Refinancing Risk",
        "Consumer Financing Reliance",
        "Capital Intensive CapEx",
        "Long Duration Cash Flows",
        "Minimal Rate Exposure",
        "Net Interest Income Beneficiary"
    ] = Field(description="The structural reason for their rate sensitivity.")
    rationale: str = Field(description="Brief explanation of the primary driver.")

class CyclePositioning(BaseModel):
    economic_bucket: Literal[
        "Early-Cycle", 
        "Mid-Cycle", 
        "Late-Cycle", 
        "Defensive/Recession", 
        "Secular Growth (Non-Cyclical)"
    ]
    macro_beta: Literal["High", "Moderate", "Low"] = Field(
        description="How aggressively does this stock swing relative to broader economic momentum?"
    )
    current_alignment: Literal["Strongly Aligned", "Aligned", "Neutral", "Misaligned", "Strongly Misaligned"] = Field(
        description="How well the company's bucket fits the CURRENT macroeconomic regime."
    )

class ThematicExposure(BaseModel):
    tailwinds: List[Theme] = Field(description="Specific macro trends helping the company.")
    headwinds: List[Theme] = Field(description="Specific macro trends hurting the company.")

class MacroConfidence(BaseModel):
    score: float = Field(description="Confidence from 0.0 to 1.0 based on data completeness.")
    reasoning: Literal[
        "Clear macro linkage", 
        "Complex/mixed macro linkage", 
        "Company is idiosyncratic/macro-agnostic", 
        "Missing critical sector data"
    ]

# ---------------------------------------------------------
# 2. Main Output Model (The Strategist's Report)
# ---------------------------------------------------------

class MacroOutput(BaseModel):
    # The Weighting Hook for the PM
    macro_dependency: Literal["Very High", "High", "Moderate", "Low", "Minimal"] = Field(
        description="How much does the macro environment actually matter to this specific company's survival/growth?"
    )

    # Core Analysis
    rates: RateSensitivity
    cycle: CyclePositioning
    themes: ThematicExposure

    # The Alpha Signals ⭐⭐⭐⭐⭐
    macro_score: int = Field(
        description="Quantitative score from -100 (Severe Headwind) to +100 (Massive Tailwind)."
    )
    macro_regime_impact: Literal["Massive Tailwind", "Tailwind", "Neutral", "Headwind", "Severe Headwind"] = Field(
        description="Categorical mapping of the macro score."
    )
    
    # Portfolio Manager Hook
    thesis_break_condition: str = Field(
        description="What specific macroeconomic shift (e.g., 'AI CapEx slowing') would destroy this stock's setup?"
    )

    confidence: MacroConfidence

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

MACRO_PROMPT = """You are the Chief Global Macro Strategist at a Tier-1 Asset Manager.
Your job is to read deterministic data regarding the current Normalized Macro State.

Your mission is to answer EXACTLY ONE QUESTION:
"Given today's macro regime, is this company swimming with or against the current?"

CRITICAL CONSTRAINTS:
- Do NOT evaluate if the stock is a good investment (that is the PM's job).
- Do NOT evaluate valuation multiples or price targets.
- Focus entirely on how much the macro environment is helping or hurting the business.
- If the company is a niche biotech or software firm, explicitly set `macro_dependency` to 'Low' or 'Minimal'."""

# ---------------------------------------------------------
# 4. The Agent Class 
# ---------------------------------------------------------

class MacroAgent(BaseAgent):
    def build_context(self, state: StockState) -> str:
        context = super().build_context(state)
        
        # Consuming the Normalized Central Macro State
        if state.get("raw_data") and "normalized_macro_state" in state["raw_data"]:
            context += f"\n\n[NORMALIZED GLOBAL MACRO REGIME]:\n{state['raw_data']['normalized_macro_state']}"
                
        return context

# Instantiate the Node
macro_node = MacroAgent(
    name="Macro",
    role_prompt=MACRO_PROMPT,
    llm=macro_llm,
    output_schema=MacroOutput
)