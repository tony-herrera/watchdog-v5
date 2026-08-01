from langgraph.graph import StateGraph, END
from langgraph.constants import Send
from langgraph.checkpoint.memory import MemorySaver # The Checkpointer

# Import Agents & State
from core.state import StockState, PortfolioState
from core.agents.research import research_node
from core.agents.valuation import valuation_node
from core.agents.consensus import consensus_node
from core.agents.institutional import institutional_node
from core.agents.macro import macro_node
from core.agents.red_team import red_team_node
from core.agents.cro import cro_node
from core.graphs.optimizer import portfolio_optimizer_node
from core.agents.portfolio_manager import portfolio_manager_node

# =====================================================================
# THE STOCK SUBGRAPH (Layers 1, 2, and 3)
# =====================================================================
def build_stock_subgraph():
    workflow = StateGraph(StockState)

    # Note: We split the Data Engine into Fetch and Normalize per your feedback
    workflow.add_node("data_fetch", data_fetch_node)
    workflow.add_node("data_normalize", data_normalize_node)
    
    workflow.add_node("research", research_node)
    workflow.add_node("valuation", valuation_node)
    workflow.add_node("consensus", consensus_node)
    workflow.add_node("institutional", institutional_node)
    workflow.add_node("macro", macro_node)
    workflow.add_node("red_team", red_team_node)
    workflow.add_node("cro", cro_node)

    # 1. The Pipeline
    workflow.set_entry_point("data_fetch")
    workflow.add_edge("data_fetch", "data_normalize")
    
    # 2. The Fan-Out
    workflow.add_edge("data_normalize", "research")
    workflow.add_edge("data_normalize", "valuation")
    workflow.add_edge("data_normalize", "consensus")
    workflow.add_edge("data_normalize", "institutional")
    workflow.add_edge("data_normalize", "macro")

    # 3. The Fan-In (LangGraph native synchronization barrier)
    # The Red Team waits until ALL 5 of these are complete. No merge node needed.
    workflow.add_edge(
        ["research", "valuation", "consensus", "institutional", "macro"], 
        "red_team"
    )

    # 4. Governance
    workflow.add_edge("red_team", "cro")
    workflow.add_edge("cro", END)

    return workflow.compile()

# =====================================================================
# THE MAP-REDUCE ROUTER
# =====================================================================
def map_holdings(state: PortfolioState):
    """Spawns the parallel jobs."""
    return [Send("analyze_stock", holding) for holding in state["holdings"]]

# =====================================================================
# THE PORTFOLIO SUPERGRAPH (Layers 4, 5, 6)
# =====================================================================
def build_portfolio_supergraph():
    workflow = StateGraph(PortfolioState)
    
    stock_subgraph = build_stock_subgraph()

    workflow.add_node("analyze_stock", stock_subgraph)
    workflow.add_node("optimizer", portfolio_optimizer_node) # Layer 4
    workflow.add_node("portfolio_manager", portfolio_manager_node) # Layer 5
    # workflow.add_node("memo_writer", memo_writer_node) # Layer 6

    # Fan out to the subgraphs
    workflow.add_conditional_edges("START", map_holdings, ["analyze_stock"])
    
    # All stocks merge into the deterministic optimizer
    workflow.add_edge("analyze_stock", "optimizer")
    
    # Optimizer feeds the PM
    workflow.add_edge("optimizer", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)

    # Establish Checkpointing (Fault Tolerance)
    checkpointer = MemorySaver()
    # In production, you would use PostgresSaver or RedisSaver
    
    return workflow.compile(checkpointer=checkpointer)

# =====================================================================
# EXECUTION
# =====================================================================
if __name__ == "__main__":
    app = build_portfolio_supergraph()
    
    # A thread ID is required for checkpointing
    config = {"configurable": {"thread_id": "portfolio_review_q3_2026"}}
    
    # Run the graph
    app.invoke(initial_portfolio, config=config)