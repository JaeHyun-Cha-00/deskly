from agent.agent import chat

if __name__ == "__main__":
    messages = []
    while True:
        text = input("\nyou> ").strip()
        if text in ("", "exit", "quit"):
            break
        reply, messages = chat(messages, text)
        print(f"\nassistant> {reply}")
