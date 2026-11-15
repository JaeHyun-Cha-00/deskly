import os
from datetime import date
from functools import cache

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware, ToolErrorMiddleware
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_openai import ChatOpenAI

from agent.demo import DEMO_TOOLS
from agent.prompts import system_prompt
from agent.steps import step_label, step_result
from agent.tools import tools_for
from config import config
from connectors.gmail.client import is_connected

@cache
def build_agent(length="short", connectors=(), demo=False, today=None):
    # `today` is part of the cache key, so the date in the prompt stays current
    model = ChatOpenAI(
        model=config["model"],
        base_url="https://api.deepinfra.com/v1/openai",
        api_key=os.getenv("DEEPINFRA_API_KEY"),
        temperature=config["temperature"],
    )
    return create_agent(
        model=model,
        tools=DEMO_TOOLS if demo else tools_for(connectors),
        system_prompt=system_prompt(length, connectors),
        middleware=[
            ToolErrorMiddleware(on_error=lambda error: f"Error: {error}"),
            ToolCallLimitMiddleware(run_limit=config["max_tool_calls"], exit_behavior="continue"),
        ],
    )

def connected():
    return ("gmail",) if is_connected() else ()

def chat(messages, text):
    messages = messages + [{"role": "user", "content": text}]
    agent = build_agent(connectors=connected(), today=date.today())
    messages = agent.invoke({"messages": messages})["messages"]
    return messages[-1].content.strip(), messages

def stream_chat(messages, text, runner):
    # yields step, step_done, token and answer events, then the final history
    messages = messages + [{"role": "user", "content": text}]
    history = messages

    for mode, chunk in runner.stream({"messages": messages}, stream_mode=["updates", "messages", "values"]):
        if mode == "values":
            history = chunk["messages"]
        elif mode == "messages":
            piece, meta = chunk
            if isinstance(piece, AIMessageChunk) and meta.get("langgraph_node") == "model" and isinstance(piece.content, str) and piece.content:
                yield {"type": "token", "text": piece.content}
        else:
            for update in chunk.values():
                for message in (update or {}).get("messages", []):
                    if isinstance(message, ToolMessage):
                        result, mails = step_result(message.content)
                        yield {"type": "step_done", "id": message.tool_call_id, "tool": message.name, "result": result, "mails": mails}
                    elif isinstance(message, AIMessage) and message.tool_calls:
                        for call in message.tool_calls:
                            yield {"type": "step", "id": call["id"], "label": step_label(call)}
                    elif isinstance(message, AIMessage) and message.content:
                        yield {"type": "answer", "text": message.content.strip()}

    yield {"type": "history", "messages": history}
