from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from core.state import StockState

class BaseAgent:
    def __init__(self, name: str, role_prompt: str, llm: Any, output_schema: BaseModel):
        self.name = name
        self.role_prompt = role_prompt
        # Bind the Pydantic schema to the LLM immediately upon initialization
        self.llm = llm.with_structured_output(output_schema)
        
    def build_context(self, state: StockState) -> str:
        """Override this in subclasses if they need specific data."""
        return f"Analyze {state['company_name']} ({state['ticker']})."

    def __call__(self, state: StockState) -> Dict[str, Any]:
        """This makes the class instance callable by LangGraph."""
        print(f"[{self.name}] Initiating analysis for {state['ticker']}...")
        
        context = self.build_context(state)
        messages = [
            SystemMessage(content=self.role_prompt),
            HumanMessage(content=context),
        ]

        try:
            result = self.llm.invoke(messages)
            
            # Use the agent's name (lowercase) as the state key
            state_key = self.name.lower().replace(" ", "_")
            
            return {
                state_key: result.model_dump(),
                "agent_outputs": {
                    state_key: {
                        "status": "success",
                        "model": "Claude 3.5 Sonnet" # Or pull dynamically from self.llm
                    }
                }
            }

        except Exception as e:
            print(f"❌ [{self.name}] Failed: {str(e)}")
            errors = state.get("errors", [])
            errors.append(f"{self.name}: {str(e)}")
            
            state_key = self.name.lower().replace(" ", "_")
            return {
                "errors": errors,
                "agent_outputs": {
                    state_key: {
                        "status": "failed",
                        "error": str(e)
                    }
                }
            }