from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import research_llm # Assuming you instantiated ChatBedrock here
from core.state import StockState

# Pydantic is amazing here. You can even add Field descriptions to guide the LLM!
class ResearchOutput(BaseModel):
    business_summary: str
    revenue_segments: list[str]
    competitive_moat: str
    industry_trends: list[str]
    management_quality: str
    long_term_thesis: str
    thesis_breakers: list[str]
    catalysts: list[str]
    risks: list[str]
    economic_engine: str
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")

structured_llm = research_llm.with_structured_output(ResearchOutput)

def research_node(state: StockState):
    print(f"🕵️‍♂️ [Research Analyst] Researching {state['ticker']}")

    system_prompt = """You are a Senior Equity Research Analyst.
    Your only responsibility is understanding the business.
    Ignore valuation, stock price, market sentiment, and technical analysis.
    Focus only on business model, competitive advantages, and strategy.
    Do not speculate. Every statement should be based on public information."""

    context = f"Analyze {state['company_name']} ({state['ticker']})."
    
    if state.get("raw_data") and "sec_10k_summary" in state["raw_data"]:
        context += f"\n\n10-K Summary:\n{state['raw_data']['sec_10k_summary']}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context),
    ]

    try:
        # LangChain + Pydantic handles the parsing and validation automatically
        result = structured_llm.invoke(messages)

        return {
            "research": result.model_dump(),
            "agent_outputs": {
                "research": {
                    "status": "success",
                    "model": "Claude 3.5 Sonnet"
                }
            }
        }

    except Exception as e:
        print(f"❌ [Research Analyst] Failed: {str(e)}")
        errors = state.get("errors", [])
        errors.append(f"Research Agent: {str(e)}")
        
        return {
            "errors": errors,
            "agent_outputs": {
                "research": {
                    "status": "failed",
                    "error": str(e)
                }
            }
        }