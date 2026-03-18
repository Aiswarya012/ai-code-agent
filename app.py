import json
import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AI Code Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    defaults = {
        "messages": [],
        "agent": None,
        "workspace": str(Path.cwd()),
        "agent_workspace": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_agent(workspace: Path):  # type: ignore[no-untyped-def]
    if st.session_state.agent is not None and st.session_state.agent_workspace == str(workspace):
        return st.session_state.agent

    from agent.core import AgentCore

    agent = AgentCore(workspace=workspace)
    st.session_state.agent = agent
    st.session_state.agent_workspace = str(workspace)
    return agent


def render_sidebar() -> Path:
    with st.sidebar:
        st.title("AI Code Agent")
        st.divider()

        api_key = st.text_input(
            "Groq API Key",
            value=os.environ.get("GROQ_API_KEY", ""),
            type="password",
            placeholder="gsk_...",
        )
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
            from config import settings

            settings.groq_api_key = api_key

        st.divider()

        workspace_path = st.text_input(
            "Workspace Path",
            value=st.session_state.workspace,
            placeholder="/path/to/your/codebase",
        )
        st.session_state.workspace = workspace_path
        workspace = Path(workspace_path).resolve()

        if not workspace.is_dir():
            st.error(f"Invalid directory: {workspace}")
            st.stop()

        st.caption(f"Resolved: `{workspace}`")

        st.divider()

        from config import settings as cfg
        from memory.vector_store import VectorStore

        data_dir = cfg.resolve_data_dir(workspace)
        store = VectorStore(data_dir=data_dir)

        col1, col2 = st.columns(2)
        with col1:
            if store.is_built:
                st.success("Index: Ready", icon="✅")
            else:
                st.warning("Index: Not built", icon="⚠️")
        with col2:
            if st.button("Build Index", use_container_width=True):
                with st.spinner("Indexing codebase..."):
                    count = store.build_index(workspace)
                if count > 0:
                    st.success(f"Indexed {count} chunks")
                    st.session_state.agent = None
                else:
                    st.warning("No indexable files found")
                st.rerun()

        st.divider()

        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.agent:
                st.session_state.agent.memory.clear()
            st.rerun()

        st.divider()
        st.caption("Powered by Groq + LLaMA 3.3 70B")

    return workspace


def render_chat_history() -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("tool_calls"):
                with st.expander(
                    f"🔧 {len(msg['tool_calls'])} tool call(s)",
                    expanded=False,
                ):
                    for tc in msg["tool_calls"]:
                        st.markdown(f"**{tc['name']}**")
                        st.code(json.dumps(tc["args"], indent=2), language="json")
                        if tc.get("result_preview"):
                            st.text(tc["result_preview"][:300])
                        st.divider()
            st.markdown(msg["content"])


def process_query(query: str, workspace: Path) -> None:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        with st.chat_message("assistant"):
            st.error("GROQ_API_KEY is not set. Enter it in the sidebar.")
        return

    agent = get_agent(workspace)
    tool_calls_log: list[dict] = []  # type: ignore[type-arg]

    with st.chat_message("assistant"):
        status = st.status("Thinking...", expanded=True)

        def handle_event(event_type: str, data: dict) -> None:  # type: ignore[type-arg]
            if event_type == "iteration":
                status.update(label=f"Iteration {data['number']} — {data['tool_count']} tool(s)")
            elif event_type == "tool_call_start":
                status.write(f"**→ {data['name']}**")
                status.code(json.dumps(data["args"], indent=2), language="json")
            elif event_type == "tool_call_end":
                preview = data["result_preview"][:300]
                status.text(preview)
                status.divider()
                tool_calls_log.append(
                    {
                        "name": data["name"],
                        "args": {},
                        "result_preview": data["result_preview"],
                    }
                )

        agent.on_event = handle_event

        try:
            response = agent.run(query)
        except Exception as exc:
            status.update(label="Error", state="error")
            st.error(f"Agent error: {exc}")
            return
        finally:
            agent.on_event = None

        label = f"Done — {len(tool_calls_log)} tool call(s)"
        status.update(label=label, state="complete", expanded=False)
        st.markdown(response)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "tool_calls": tool_calls_log if tool_calls_log else None,
        }
    )


def main() -> None:
    init_session_state()
    workspace = render_sidebar()
    render_chat_history()

    query = st.chat_input("Ask about your codebase...")
    if query:
        process_query(query, workspace)


main()
