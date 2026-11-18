import os

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware, ToolCallLimitMiddleware, ToolErrorMiddleware, dynamic_prompt
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent import memory
from agent.prompts import system_prompt
from agent.tools import APPS, WRITE_TOOLS, app_name, approval_text, step_label, step_result, tools_for
from config import config
from connectors import event_loop
from connectors.apps import connected
from connectors.mcp.client import load_tools
from connectors.mcp.servers import SERVERS

# where a paused answer waits for the user's decision; kept in memory only,
# so closing the app lets go of every pending approval
CHECKPOINTS = InMemorySaver()

# put before the result of a call the user changed on the approval card
EDIT_NOTICE = (
    "The user changed this action on the approval card before it ran. The result below is "
    "what was actually done; tell the user that, not what you first asked for."
)

# the most of one tool result the model reads; MCP servers can send a lot
MAX_RESULT_CHARS = 12000

def result_text(content):
    # MCP tools may answer with a list of parts; the model and the screen want one text
    if isinstance(content, str):
        return content
    return "\n".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)

# what is left of a tool result from an older question: enough to know what it was
OLD_RESULT_CHARS = 300
OLD_RESULT_NOTE = "\n\n(Shortened to save space: this came from an earlier question. Call the tool again if you need it in full.)"

def trim_old_results(messages, keep_turns=1):
    # Old questions, answers and tool calls stay, but tool results from before the last
    # `keep_turns` questions are cut short: they fill the model's memory fastest.
    starts = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(starts) <= keep_turns:
        return messages
    cut = starts[-keep_turns]
    trimmed = []
    for i, message in enumerate(messages):
        if i < cut and isinstance(message, ToolMessage):
            text = result_text(message.content)
            if len(text) > OLD_RESULT_CHARS:
                message = message.model_copy(update={"content": text[:OLD_RESULT_CHARS] + OLD_RESULT_NOTE})
        trimmed.append(message)
    return trimmed

class CapToolResults(AgentMiddleware):
    # cuts any tool result that is too long and says so, so one big answer can't fill the model's memory
    def cut(self, message):
        if isinstance(message, ToolMessage):
            text = result_text(message.content)
            if len(text) > MAX_RESULT_CHARS:
                message.content = text[:MAX_RESULT_CHARS] + "\n\n(The result was cut short here.)"
        return message

    def wrap_tool_call(self, request, handler):
        return self.cut(handler(request))

    async def awrap_tool_call(self, request, handler):
        return self.cut(await handler(request))

def approval(name):
    return {
        "allowed_decisions": ["approve", "edit", "reject"],
        "description": lambda call, state, runtime: approval_text(call),
    }

# built agents by (length, connectors, use_memory); building one loads the MCP servers' tools
AGENTS = {}

async def get_agent(length="short", connectors=(), use_memory=False):
    key = (length, connectors, use_memory)
    if key in AGENTS:
        return AGENTS[key]
    tools = tools_for(connectors)
    if use_memory:
        tools = tools + APPS["memory"].TOOLS
    writes = set(WRITE_TOOLS)
    failed = []
    servers = [name for name in connectors if name in SERVERS]
    if servers:
        mcp_tools, mcp_writes, failed = await load_tools(servers)
        tools, writes = tools + mcp_tools, writes | mcp_writes
    agent = build_agent(length, connectors, tools, writes, use_memory)
    # a server that didn't answer is tried again next time instead of being left out for good
    if not failed:
        AGENTS[key] = agent
    return agent

def build_agent(length, connectors, tools, writes, use_memory=False):
    model = ChatOpenAI(
        model=config["model"],
        # OpenRouter sends each request to a provider that is up, so one provider being down doesn't stop the app
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        # only providers that don't store or train on the mail and events we send
        extra_body={"provider": {"data_collection": "deny"}},
        temperature=config["temperature"],
        # each reply says how many tokens it used, for the context meter
        stream_usage=True,
    )

    # made again before every model call, so the time in it is always now
    @dynamic_prompt
    def prompt(request):
        return system_prompt(length, connectors, use_memory)

    return create_agent(
        model=model,
        tools=tools,
        middleware=[
            prompt,
            CapToolResults(),
            ToolErrorMiddleware(on_error=lambda error: f"Error: {error}"),
            ToolCallLimitMiddleware(run_limit=config["max_tool_calls"], exit_behavior="continue"),
            # stops before any tool that changes something, until the user decides
            HumanInTheLoopMiddleware(interrupt_on={name: approval(name) for name in writes}, edit_notice=EDIT_NOTICE),
        ],
        checkpointer=CHECKPOINTS,
    )

def chat(messages, text):
    # the terminal chat: one run, nothing to approve there (write tools stop and are skipped)
    messages = messages + [{"role": "user", "content": text}]
    async def ask():
        agent = await get_agent(connectors=connected(), use_memory=memory.is_on())
        return await agent.ainvoke({"messages": messages}, {"configurable": {"thread_id": "terminal"}})

    found = event_loop.run(ask())
    messages = found["messages"]
    return messages[-1].content.strip(), messages

async def stream_chat(messages, text, runner, run_id, decisions=None):
    # yields step, step_done, token, answer and approval events, then the final history.
    # It is async because tools from MCP servers only run that way.
    # With decisions, it picks up the paused run `run_id` instead of starting a new one.
    settings = {"configurable": {"thread_id": run_id}}
    if decisions is None:
        messages = messages + [{"role": "user", "content": text}]
        start = {"messages": messages}
    else:
        start = Command(resume={"decisions": decisions})
    history = messages

    async for mode, chunk in runner.astream(start, settings, stream_mode=["updates", "messages", "values"]):
        if mode == "values":
            history = chunk["messages"]
        elif mode == "messages":
            piece, meta = chunk
            if isinstance(piece, AIMessageChunk) and meta.get("langgraph_node") == "model" and isinstance(piece.content, str) and piece.content:
                yield {"type": "token", "text": piece.content}
        else:
            for node, update in chunk.items():
                if node == "__interrupt__":
                    # the agent stopped before a write tool and waits for the user
                    for paused in update:
                        requests = paused.value["action_requests"]
                        yield {"type": "approval", "requests": [{"name": r["name"], "args": r["args"], "description": r.get("description", "")} for r in requests]}
                    continue
                for message in (update or {}).get("messages", []):
                    if isinstance(message, AIMessage) and message.usage_metadata:
                        # everything the model held for this call: the prompt, tools, chat and its reply
                        yield {"type": "usage", "tokens": message.usage_metadata["total_tokens"], "limit": config["context_tokens"]}
                    if isinstance(message, ToolMessage):
                        cards = step_result(message.name, message.content, message.artifact)
                        yield {"type": "step_done", "id": message.tool_call_id, "tool": message.name, "app": app_name(message.name), **cards}
                    elif isinstance(message, AIMessage) and message.tool_calls:
                        for call in message.tool_calls:
                            yield {"type": "step", "id": call["id"], "label": step_label(call), "tool": call["name"], "app": app_name(call["name"])}
                    elif isinstance(message, AIMessage) and message.content:
                        yield {"type": "answer", "text": message.content.strip()}

    yield {"type": "history", "messages": history}
