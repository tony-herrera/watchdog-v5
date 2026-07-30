import operator
from typing import TypedDict, List, Dict, Any, Annotated

# 1. Define nested structured types FIRST
class Recommendation(TypedDict):
    rating: str               # "BUY", "HOLD", "TRIM", "SELL"
    confidence: float         # 0.0 to 100.0
    target_weight: float      # e.g., 5.5 for 5.5%
    expected_return: float    # e.g., 12.4 for 12.4% CAGR

# 2. The Single Stock State (The Analyst Pipeline)
class StockState(TypedDict):
    """
    The strict data contract for a single stock moving through the pipeline.
    """
    # ---------- INPUT ----------
    ticker: str
    company_name: str
    shares: float
    cost_basis: float
    market_value: float
    portfolio_weight: float

    # ---------- WORKING (Data & Diagnostics) ----------
    raw_data: Dict[str, Any]       # Store raw API responses here (SEC, Multiples, etc.)
    errors: List[str]              # Non-fatal errors to prevent batch pipeline crashes

    # ---------- AGENT OUTPUTS ----------
    research: Dict[str, Any]       # Fidelity Analyst
    fundamentals: Dict[str, Any]   # CFA Agent
    valuation: Dict[str, Any]      # Valuation Specialist
    expectations: Dict[str, Any]   # Goldman Flow Desk
    macro: Dict[str, Any]          # Macro Desk
    risk: Dict[str, Any]           # Risk Committee
    devils_advocate: Dict[str, Any]# The bear thesis attack

    # ---------- COMMITTEE DECISION ----------
    committee_votes: List[Dict[str, Any]] # Audit trail of individual agent votes
    thesis: Dict[str, Any]         
    rationale: str                 # The written narrative
    evidence_needed: List[str]     # What would change their mind
    recommendation: Recommendation # Strongly typed output!
    scorecard: Dict[str, Any]      # Formatted data for UI tables


# 3. The Portfolio State (The CIO Supervisor)
class PortfolioState(TypedDict):
    """
    The Map-Reduce aggregator for the entire portfolio.
    """
    # Input
    holdings: List[Dict[str, Any]] 
    analysis_version: str          # Great for tracking model versions (e.g., "v5.1-nova")
    
    # Map-Reduce Aggregator
    analyzed_stocks: Annotated[List[StockState], operator.add]
    
    # CIO Outputs
    allocation_plan: Dict[str, Any]
    sector_exposure: Dict[str, Any]
    
    # By making these List[Dict], the UI can render rich "Sell Candidate" cards
    # rather than just a list of ticker strings.
    sell_candidates: List[Dict[str, Any]] 
    buy_candidates: List[Dict[str, Any]]
    
    final_cio_memo: str