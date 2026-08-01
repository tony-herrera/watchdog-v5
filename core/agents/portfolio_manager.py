from typing import Literal, List
from pydantic import BaseModel, Field
from core.llm import portfolio_manager_llm
from core.state import PortfolioState

# ---------------------------------------------------------
# 1. Nested Structured Pydantic Models (The Trade Desk)
# ---------------------------------------------------------

class TradeInstruction(BaseModel):
    ticker: Literal["CASH"] | str = Field(description="The asset ticker, or 'CASH'.")
    action: Literal["Accumulate", "Hold", "Reduce", "Exit"]
    current_weight_pct: float = Field(description="The current portfolio allocation.")
    ideal_weight_pct: float = Field(description="The target portfolio allocation. Must respect CRO Risk Tiers.")
    trade_size_pct: float = Field(description="Mathematically: Ideal Weight - Current Weight.")
    primary_driver: str = Field(description="The single normalized metric (e.g., 'Macro Score -80') driving this trade.")

class CapitalRotation(BaseModel):
    source_asset: str = Field(description="Ticker being sold/reduced (or CASH).")
    destination_asset: str = Field(description="Ticker being bought/accumulated (or CASH).")
    capital_pct: float = Field(description="Percentage of total portfolio capital being rotated.")
    reason: str = Field(description="Strict 1-sentence justification (e.g., 'Rotating from high valuation risk to wide margin of safety').")

class FactorExposure(BaseModel):
    factor: str = Field(description="e.g., 'AI CapEx', 'Semiconductors', 'Mega Cap Growth', 'High Debt'.")
    exposure_pct: float = Field(description="Estimated portfolio weight exposed to this factor.")
    risk_assessment: Literal["Safe", "Monitor", "Elevated", "Dangerous Concentration"]

# ---------------------------------------------------------
# 2. Main Output Model (The PM's Execution Plan)
# ---------------------------------------------------------

class PortfolioManagerOutput(BaseModel):
    # Overall Stance
    target_cash_position_pct: float = Field(description="Ideal percentage of the portfolio to hold in cash/treasuries.")
    
    # Execution
    trades: List[TradeInstruction]
    rotations: List[CapitalRotation]

    # Categorized Roster (Deterministic Routing for UI)
    top_accumulate: List[str]
    top_hold: List[str]
    top_reduce: List[str]
    top_exit: List[str]

    # Risk & Factors
    factor_exposures: List[FactorExposure]

# ---------------------------------------------------------
# 3. The Strict Persona 
# ---------------------------------------------------------

PORTFOLIO_MANAGER_PROMPT = """You are the Lead Portfolio Manager at an institutional hedge fund.
You are consuming a NORMALIZED FEATURE VECTOR representing the outputs of your specialized analysts and Chief Risk Officer.

Your mission is strict Capital Allocation.

CRITICAL CONSTRAINTS:
- Do NOT read narrative. Evaluate the scores.
- Cash is an active position. If the expected returns do not justify the risk budgets, increase CASH.
- You must explicitly define Capital Rotations. If you buy, you must sell (or deploy cash).
- Do NOT exceed the Risk Budget Tier defined by the CRO for any asset.
- Your output feeds directly into a trading execution engine. Precision is mandatory."""

# ---------------------------------------------------------
# 4. The Agent Class (The Feature Vector Consumer)
# ---------------------------------------------------------

class PortfolioManagerAgent:
    def __init__(self, llm, prompt, schema):
        self.llm = llm.with_structured_output(schema)
        self.prompt = prompt

    def build_context(self, state: PortfolioState) -> str:
        # We transform the raw JSON into a highly readable, normalized Markdown Table
        # This dramatically reduces token count and prevents LLM "distraction".
        
        context = "=== NORMALIZED PORTFOLIO FEATURE VECTOR ===\n\n"
        context += "| Ticker | Cur Wgt | Fund Score | Val Score | Macro Score | Inst Score | CRO Tier | Expected Return | Max Drawdown | Thesis Break Condition |\n"
        context += "|--------|---------|------------|-----------|-------------|------------|----------|-----------------|--------------|------------------------|\n"
        
        for stock in state["analyzed_stocks"]:
            t = stock.get("ticker", "UNK")
            wgt = stock.get("portfolio_weight", 0.0)
            
            # Extracting normalized outputs from upstream agents
            fund = stock.get("research", {}).get("quality_score", "N/A") # Assuming we added a score here
            val = stock.get("valuation", {}).get("margin_of_safety", "N/A")
            mac = stock.get("macro", {}).get("macro_score", "N/A")
            inst = stock.get("institutional", {}).get("rotation_probability", "N/A")
            
            cro = stock.get("cro", {})
            tier = cro.get("risk_budget_tier", "N/A")
            drawdown = cro.get("capital_preservation", {}).get("max_drawdown_estimate_pct", "N/A")
            break_cond = cro.get("thesis_invalidation_rules", [{}])[0].get("metric", "None") if cro.get("thesis_invalidation_rules") else "None"
            
            # The deterministic Python calculation (Expected Value)
            exp_ret = stock.get("deterministic_metrics", {}).get("calculated_expected_cagr", "N/A")

            context += f"| {t} | {wgt}% | {fund} | {val}% | {mac} | {inst} | {tier} | {exp_ret}% | {drawdown}% | {break_cond} |\n"
            
        context += "\n[Note: Evaluate relative Risk/Reward to determine Target Weights and necessary Rotations.]"
        return context

    def __call__(self, state: PortfolioState) -> dict:
        print("👔 [Portfolio Manager] Parsing normalized feature vectors and allocating capital...")
        
        context = self.build_context(state)
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": context}
        ]

        try:
            result = self.llm.invoke(messages)
            
            # The PM no longer writes memos. It just passes the structured data.
            return {
                "allocation_plan": result.model_dump(),
                "sell_candidates": result.top_exit + result.top_reduce,
                "buy_candidates": result.top_accumulate
            }

        except Exception as e:
            print(f"❌ [Portfolio Manager] Failed: {str(e)}")
            return {"errors": [f"PM Allocation Error: {str(e)}"]}

# Instantiate the Node
portfolio_manager_node = PortfolioManagerAgent(
    llm=portfolio_manager_llm,
    prompt=PORTFOLIO_MANAGER_PROMPT,
    schema=PortfolioManagerOutput
)