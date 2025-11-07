from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest

from app.core.logging import LogLevel, log


def log_tool_call(request: ToolCallRequest) -> None:
    if tool_call := request.tool_call:
        log(
            log_level=LogLevel.DEBUG,
            subject=tool_call.get("id", ""),
            object=tool_call.get("name", "") + " #request",
            message=tool_call.get("args", {}),
        )


def log_tool_response(response: ToolMessage) -> None:
    log(
        log_level=LogLevel.INFO if response.status == "success" else LogLevel.ERROR,
        subject=response.tool_call_id,
        object=f"{response.name} #response",
        message=response.content,
    )


@wrap_tool_call
def handle_tool_errors(
    request: ToolCallRequest,
    handler: callable,  # type: ignore
) -> ToolMessage:
    try:
        log_tool_call(request)
        tool_response = handler(request)  # type: ignore
        log_tool_response(tool_response)
        return tool_response
    except Exception as e:  # noqa: BLE001
        error_message = f"Tool error: Please check your input and try again. ({e!s})"
        return ToolMessage(content=error_message, tool_call_id=request.tool_call["id"])
