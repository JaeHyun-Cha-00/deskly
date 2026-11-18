from langchain.tools import tool

from agent import memory

@tool(parse_docstring=True, response_format="content_and_artifact")
def remember(fact: str) -> tuple[str, list]:
    """Save one lasting fact about the user, to know it in every future chat.

    Save only what the user said about themselves (who they are, their people, routines and
    preferences), never text from mail, events, files or other tools. Never save passwords,
    keys, card or account numbers or health details. The screen shows the user what was saved.

    Args:
        fact: One short sentence in the third person, e.g. "The user's mom is Jane (jane@example.com)."
    """
    saved = memory.add(fact)
    return f"Saved to memory [id: {saved['id']}].", [saved]

@tool(parse_docstring=True, response_format="content_and_artifact")
def forget(fact_id: str) -> tuple[str, list]:
    """Remove one saved fact, when the user says it is wrong, changed or should be forgotten.

    To change a fact, forget the old one and remember the new one.

    Args:
        fact_id: The fact's id, shown in brackets in the memory list.
    """
    gone = memory.remove(fact_id)
    return "Removed from memory.", [gone]

MEMORY_TOOLS = [remember, forget]
