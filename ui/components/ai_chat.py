"""AI chat interface (v0.2).

A conversational front-end to Athena that:
- Uses the configured provider (deterministic by default — no AI call on v0.1)
- Respects explicit tool permissions (user approves which tools the AI can use)
- Retrieves relevant approved memories for context
- Applies context limits (max messages retained)
- Handles model errors gracefully
- NEVER executes model-generated text as Python or shell code

Security: all tool calls are validated, approved by the user, and executed
safely through the domain services.  Nothing the model says is executed as
code.
"""

from __future__ import annotations

import streamlit as st

from athena.ai import AIProvider, load_provider, ToolCall, ToolDefinition
from athena.database import connect
from athena.domain import memory_service
from athena.domain import task_service, project_service
from athena.domain.memory_service import MemoryUpdate
from athena.config import AI_API_KEY

# ---------------------------------------------------------------------------
# Tool definitions (declared, not executed by the model)
# ---------------------------------------------------------------------------

TOOLS = {
    "create_task": ToolDefinition(
        name="create_task",
        description="Create a new task with a title, priority, estimated minutes, and optional due date.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title (1-200 chars)"},
                "description": {"type": "string", "description": "Optional description"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Priority level",
                },
                "estimated_minutes": {"type": "integer", "minimum": 0, "default": 0},
                "due_date": {"type": "string", "description": "ISO date (YYYY-MM-DD), optional"},
            },
            "required": ["title"],
        },
        permission_required=True,
    ),
    "search_memories": ToolDefinition(
        name="search_memories",
        description="Search stored memories by keyword to retrieve relevant context.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword"},
                "kind": {"type": "string", "enum": ["profile_fact", "goal", "event", "knowledge_note"], "description": "Optional kind filter"},
                "approved_only": {"type": "boolean", "description": "Only approved memories"},
            },
            "required": ["query"],
        },
        permission_required=True,
    ),
    "update_memory": ToolDefinition(
        name="update_memory",
        description="Edit or approve a saved memory.",
        parameters={
            "type": "object",
            "properties": {
                "memory_id": {"type": "integer", "description": "Memory ID to update"},
                "content": {"type": "string", "description": "New content"},
                "approved": {"type": "boolean", "description": "Set approval flag"},
            },
            "required": ["memory_id"],
        },
        permission_required=True,
    ),
    "delete_memory": ToolDefinition(
        name="delete_memory",
        description="Permanently delete a saved memory.",
        parameters={
            "type": "object",
            "properties": {
                "memory_id": {"type": "integer", "description": "Memory ID to delete"},
            },
            "required": ["memory_id"],
        },
        permission_required=True,
    ),
    "create_project": ToolDefinition(
        name="create_project",
        description="Create a new project.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Project title"},
                "description": {"type": "string", "description": "Optional description"},
                "status": {"type": "string", "enum": ["planning", "active", "on_hold", "completed", "archived"], "default": "active"},
            },
            "required": ["title"],
        },
        permission_required=True,
    ),
}

def _call_tool(tool_name: str, arguments: dict) -> str:
    """Safely execute an approved tool via the domain services.

    This is the ONLY place tool actions are taken.  The model only produces
    arguments; we validate and execute here.
    """
    conn = connect()
    try:
        if tool_name == "create_task":
            t = arguments.get("title", "Untitled")
            desc = arguments.get("description", "")
            priority = arguments.get("priority", "medium")
            minutes = int(arguments.get("estimated_minutes", 0) or 0)
            due = arguments.get("due_date")
            task_service.create_task(
                conn,
                task_service.TaskCreate(
                    title=t,
                    description=desc,
                    priority=priority,
                    estimated_minutes=minutes,
                    due_date=due,
                    status="todo",
                ),
            )
            return f"Created task '{t}' (this action was executed by your assistant, not generated by the model)."
        if tool_name == "search_memories":
            query = arguments["query"]
            kind = arguments.get("kind")
            approved_only = arguments.get("approved_only", False)
            results = memory_service.search_memories(
                conn, query, kind=kind, approved_only=approved_only, limit=10
            )
            if not results:
                return "No matching memories found."
            lines = [f"Found {len(results)} memory(s):"]
            for m in results:
                lines.append(f"  [{m.kind}] {'[approved]' if m.approved else '[unapproved]'} {m.content[:120]}…")
            return "\n".join(lines)
        if tool_name == "update_memory":
            mem_id = arguments["memory_id"]
            content = arguments.get("content")
            approved = arguments.get("approved")
            if content is not None:
                memory_service.update_memory(conn, mem_id, MemoryUpdate(content=content))
            elif approved is not None:
                memory_service.approve_memory(conn, mem_id, approved)
            return f"Updated memory {mem_id}."
        if tool_name == "delete_memory":
            mem_id = arguments["memory_id"]
            memory_service.delete_memory(conn, mem_id)
            return f"Deleted memory {mem_id}."
        if tool_name == "create_project":
            title = arguments["title"]
            desc = arguments.get("description", "")
            status = arguments.get("status", "active")
            project_service.create_project(
                conn,
                project_service.ProjectCreate(title=title, description=desc, status=status),
            )
            return f"Created project '{title}'."
        return "Unknown tool."
    finally:
        conn.close()


def _get_tool_choices() -> list[ToolDefinition]:
    """Return tools the user has explicitly approved."""
    approved = set()
    if st.session_state.get("ai_task_tools"):
        approved.add("create_task")
    if st.session_state.get("ai_memory_tools"):
        approved.add("search_memories")
    if st.session_state.get("ai_edit_tools"):
        approved.add("update_memory")
        approved.add("delete_memory")
    if st.session_state.get("ai_project_tools"):
        approved.add("create_project")

def _build_messages(history: list[dict]) -> list[dict]:
    """Convert Streamlit chat history into the provider's expected format."""
    provider = load_provider()
    messages = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    # Optional: add system prompt
    return messages


def _format_tool_calls(tool_calls: list[ToolCall]) -> str:
    """Render tool calls as human-readable lines, never as executable code."""
    lines = []
    for tc in tool_calls:
        lines.append(f"💡 [{tc.name}]")
        for k, v in tc.arguments.items():
            lines.append(f"   • {k}: {v}")
    return "\n".join(lines)


def chat_page() -> None:
    st.subheader("AI Chat")
    st.caption(
        "Chat with Athena. Deterministic v0.1: no AI call is made unless a "
        "provider is configured. All tool calls require your explicit approval."
    )

    # --- Tool permission toggle ------------------------------------------
    st.sidebar.markdown("### Tool permissions")
    st.caption(
        "Select which tool categories Athena may use. Nothing is executed "
        "until you approve a tool here."
    )
    if st.checkbox("Allow task management (create tasks)", key="ai_task_tools"):
        st.session_state["ai_task_tools"] = True
    else:
        st.session_state.pop("ai_task_tools", None)
    if st.checkbox("Allow memory search", key="ai_memory_tools"):
        st.session_state["ai_memory_tools"] = True
    else:
        st.session_state.pop("ai_memory_tools", None)
    if st.checkbox("Allow memory edit/approve/delete", key="ai_edit_tools"):
        st.session_state["ai_edit_tools"] = True
    else:
        st.session_state.pop("ai_edit_tools", None)
    if st.checkbox("Allow project creation", key="ai_project_tools"):
        st.session_state["ai_project_tools"] = True
    else:
        st.session_state.pop("ai_project_tools", None)


    # --- Provider status check ---------------------------------------------
    provider = load_provider()
    if provider is None:
        st.warning(
            "No AI provider is configured yet. "
            "Click 'Settings' → 'AI Provider' to configure one, or check "
            "the README for configuration steps."
        )
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        st.chat_input("Ask Athena anything…")
        return

    # --- Provider status message -------------------------------------------
    provider_name = provider.provider_name
    st.info(f"AI provider: `{provider_name}` (deterministic — no model call on v0.1)")
    # --- Provider status message ----------------------------------------
    provider_name = load_provider().provider_name
    st.info(f"AI provider: `{provider_name}` (deterministic — no model call on v0.1)")

    # --- Chat message history ------------------------------------------
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Render existing messages
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Chat input ----------------------------------------------------
    user_input = st.chat_input("Ask Athena anything…")
    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state["chat_history"].append({"role": "user", "content": user_input})

        # Retrieve context (reviewed memories)
        ctx_items = []
        query = st.session_state.get("last_query", "")
        if query.strip():
            try:
                conn = connect()
                try:
                    results = memory_service.search_memories(
                        conn, query, approved_only=True, limit=5
                    )
                    ctx_items = [m for m in results]
                finally:
                    conn.close()
            except Exception:
                ctx_items = []

        # Build tool call list (only approved tools)
        tool_names = _get_tool_choices()

        with st.spinner("Thinking…"):
            response = provider.chat(
                [{"role": "user", "content": user_input}],
                tools=list(TOOLS.values()),
                tool_permissions=set(tool_names),
                context_limit=50,
            )
        with st.spinner("Thinking…"):
            response = load_provider().chat(
                [{"role": "user", "content": user_input}],
                tools=list(TOOLS.values()),
                tool_permissions=set(tool_names),
                context_limit=50,
            )

            if response.tool_calls:
                st.markdown("### 🔧 Tool calls")
                st.caption("These actions require your approval before they run.")
                for tc in response.tool_calls:
                    with st.expander(f"▶ {tc.name}", expanded=True):
                        st.json(tc.arguments)
                        if st.button("Allow this tool call", key=f"approve_{tc.call_id}"):
                            # Execute the tool
                            _call_tool(tc.name, tc.arguments)
                            st.success(f"✅ {tc.name} executed.")
                            st.session_state["chat_history"].append({
                                "role": "assistant",
                                "content": f"🔧 Ran {tc.name} with arguments: {tc.arguments}",
                            })
                            break
            else:
                st.markdown(response.text)

            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": response.text,
            })
    return [TOOLS[name] for name in sorted(approved)]