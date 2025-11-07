from langchain.agents.middleware import after_model
from langchain.agents.middleware import AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from loguru import logger


@after_model
def validate_output(state: AgentState, runtime: Runtime) -> None:  # noqa: ARG001
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage):
        if response := last_message.content:
            logger.info(f"AI response: {response}")
        elif getattr(last_message, "tool_calls", []):
            pass
