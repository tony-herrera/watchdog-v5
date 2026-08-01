from typing import Dict, List, Any
from core.state import PortfolioState

# ---------------------------------------------------------
# 1. Hard Constraints (The Governance Rules)
# ---------------------------------------------------------
MAX_WEIGHT_BY_TIER = {
    "Tier 1 (Core Compounder / Low Risk)": 10.0,
    "Tier 2 (Standard Allocation / Moderate Risk)": 7.0,
    "Tier 3 (Satellite / Elevated Risk)": 3.0,
    "Tier 4 (Speculative / Strictly Capped)": 1.0
}

MAX_SECTOR_EXPOSURE = 35.0  # Cannot exceed 35% in one sector

# ---------------------------------------------------------
# 2. The Deterministic Engine
# ---------------------------------------------------------
def portfolio_optimizer_node(state: PortfolioState) -> dict:
    print("⚙️ [Optimization Engine] Running deterministic constraints and risk-adjusted ranking...")
    
    viable_candidates = []
    rejected_candidates = []
    constraint_violations = []
    
    # 1. Tally Current Portfolio Sector Exposure
    sector_weights = {}
    for stock in state["analyzed_stocks"]:
        sector = stock.get("sector", "Unknown") # Assuming sector is pulled in Layer 1
        weight = stock.get("portfolio_weight", 0.0)
        sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

    # 2. Score Every Stock
    for stock in state["analyzed_stocks"]:
        ticker = stock["ticker"]
        
        # Skip failed pipelines
        if stock.get("status") == "FAILED":
            rejected_candidates.append({"ticker": ticker, "reason": "Layer 2 Analysis Failed"})
            continue

        # Extract Canonical Normalized Scores (0-100)
        scores = stock.get("normalized_scores", {})
        quality = scores.get("quality_score", 50)
        valuation = scores.get("valuation_score", 50)
        macro = scores.get("macro_score", 50)
        institutional = scores.get("institutional_score", 50)
        risk_score = scores.get("risk_score", 50) # Lower is riskier for scoring purposes
        
        # Extract Confidence & CRO Data
        confidence = stock.get("overall_confidence", 0.5)
        cro = stock.get("cro", {})
        risk_tier = cro.get("risk_budget_tier", "Tier 4 (Speculative / Strictly Capped)")
        max_drawdown = cro.get("capital_preservation", {}).get("max_drawdown_estimate_pct", -100.0)
        
        # --- A. BASE COMPOSITE SCORE ---
        base_composite = (
            (quality * 0.25) +
            (valuation * 0.25) +
            (macro * 0.20) +
            (institutional * 0.15) +
            (risk_score * 0.15)
        )
        
        # --- B. CONFIDENCE WEIGHTING ---
        # e.g., 0.5 confidence = 90% multiplier, 1.0 = 100% multiplier
        confidence_multiplier = 0.8 + (confidence * 0.2)
        confidence_adjusted_score = base_composite * confidence_multiplier
        
        # --- C. RISK-ADJUSTED SCORE (The Denominator) ---
        # A -60% drawdown creates a penalty of 3.0. A -15% drawdown creates a penalty of 0.75.
        # We clamp it to 0.5 minimum to prevent divide-by-zero or massive artificial inflation.
        risk_penalty = max(abs(max_drawdown) / 20.0, 0.5)
        risk_adjusted_score = confidence_adjusted_score / risk_penalty
        
        # --- D. OPPORTUNITY COST (Marginal Capital) ---
        current_weight = stock.get("portfolio_weight", 0.0)
        target_max_weight = MAX_WEIGHT_BY_TIER.get(risk_tier, 1.0)
        
        # Bonus for stocks we are severely underweight in relative to their allowed risk
        underweight_bonus = target_max_weight - current_weight
        final_alpha_score = risk_adjusted_score + (underweight_bonus * 1.5) # Tune this multiplier
        
        # --- E. SECTOR CONCENTRATION PENALTY ---
        sector = stock.get("sector", "Unknown")
        if sector_weights.get(sector, 0) > MAX_SECTOR_EXPOSURE:
            final_alpha_score -= 20.0
            constraint_violations.append(f"{ticker} penalized: {sector} exceeds {MAX_SECTOR_EXPOSURE}% limit.")

        # --- F. HARD CONSTRAINT GATE ---
        if current_weight >= target_max_weight:
            rejected_candidates.append({
                "ticker": ticker, 
                "reason": f"At or above CRO Max Weight ({target_max_weight}%)"
            })
            continue
            
        if max_drawdown < -50.0 and risk_tier not in ["Tier 1", "Tier 2"]:
            rejected_candidates.append({
                "ticker": ticker, 
                "reason": f"Unacceptable Drawdown ({max_drawdown}%) for {risk_tier}"
            })
            continue

        # If it passes, it is a viable candidate for capital
        viable_candidates.append({
            "ticker": ticker,
            "final_alpha_score": final_alpha_score,
            "risk_adjusted_score": risk_adjusted_score,
            "current_weight": current_weight,
            "recommended_max_weight": target_max_weight,
            "risk_tier": risk_tier,
            "sector": sector
        })

    # 3. Sort Descending by Final Alpha Score
    viable_candidates.sort(key=lambda x: x["final_alpha_score"], reverse=True)
    
    return {
        "optimized_candidates": viable_candidates,
        "rejected_candidates": rejected_candidates,
        "constraint_violations": constraint_violations
    }