"""Streamlit chat application for Deep Research.

A ChatGPT-like interface for interacting with the deep research
workflow system. Displays agent intermediate steps and final answers
in a conversational format.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

import streamlit as st

from deep_research_poc.streamlit_app.client import (
    AgentEvent,
    ResearchApiClient,
    ResearchDepth,
    ResearchResult,
)

# Page configuration
st.set_page_config(
    page_title="Deep Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for chat styling
st.markdown(
    """
    <style>
    .stChatMessage {
        padding: 1rem;
    }
    .agent-step {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
    }
    .agent-step-header {
        font-weight: 600;
        color: #1f77b4;
        margin-bottom: 0.25rem;
    }
    .source-chip {
        display: inline-block;
        background-color: #e3e8ee;
        border-radius: 12px;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        font-size: 0.85rem;
    }
    .thinking-indicator {
        color: #666;
        font-style: italic;
    }
    .error-message {
        color: #d32f2f;
        background-color: #ffebee;
        padding: 0.75rem;
        border-radius: 8px;
        border-left: 3px solid #d32f2f;
    }
    .success-badge {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@dataclass
class ChatMessage:
    """A message in the chat history."""

    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: str = "text"  # "text", "research_result", "agent_steps"
    metadata: dict[str, Any] = field(default_factory=lambda: {})


def init_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_client" not in st.session_state:
        st.session_state.api_client = None
    if "api_url" not in st.session_state:
        st.session_state.api_url = "http://localhost:8000"
    if "research_depth" not in st.session_state:
        st.session_state.research_depth = ResearchDepth.STANDARD
    if "max_iterations" not in st.session_state:
        st.session_state.max_iterations = 3
    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = []
    if "current_workflow_id" not in st.session_state:
        st.session_state.current_workflow_id = None


def get_api_client() -> ResearchApiClient:
    """Get or create the API client."""
    if (
        st.session_state.api_client is None
        or st.session_state.api_client.base_url != st.session_state.api_url
    ):
        st.session_state.api_client = ResearchApiClient(
            base_url=st.session_state.api_url
        )
    return st.session_state.api_client


def check_api_health() -> tuple[bool, str]:
    """Check if the API is healthy."""
    try:
        client = get_api_client()
        health = client.check_health()
        if health.get("status") == "healthy":
            temporal_status = (
                "connected" if health.get("temporal_connected") else "disconnected"
            )
            return True, f"API healthy, Temporal {temporal_status}"
        return False, "API returned unhealthy status"
    except Exception as e:
        return False, f"Cannot connect to API: {e}"


def format_agent_event(event: AgentEvent) -> str:
    """Format an agent event for display."""
    agent_icons = {
        "PlanningAgent": "📋",
        "QueryExpansionAgent": "🔍",
        "ResearchAgent": "🔬",
        "ValidationAgent": "✅",
        "CritiqueAgent": "🎯",
        "system": "⚙️",
    }
    icon = agent_icons.get(event.agent_name, "🤖")

    event_type_labels = {
        "system": "System",
        "agent_start": "Started",
        "agent_thinking": "Thinking",
        "agent_result": "Completed",
        "agent_error": "Error",
        "validation": "Validation",
        "critique": "Critique",
    }
    label = event_type_labels.get(event.event_type, event.event_type)

    return f"{icon} **{event.agent_name}** ({label}): {event.message}"


def display_agent_events(events: list[AgentEvent]) -> None:
    """Display agent events in an expandable section."""
    if not events:
        return

    with st.expander("🔄 Research Process Steps", expanded=False):
        for event in events:
            event_text = format_agent_event(event)

            # Color code by event type
            if event.event_type == "agent_error":
                st.markdown(
                    f'<div class="error-message">{event_text}</div>',
                    unsafe_allow_html=True,
                )
            elif event.event_type == "agent_result":
                st.success(event_text)
            elif event.event_type == "agent_thinking":
                st.info(event_text)
            else:
                st.markdown(event_text)

            # Show details if available
            if event.details:
                with st.expander("Details", expanded=False):
                    st.json(event.details)


def display_research_result(result: ResearchResult) -> None:
    """Display the final research result."""
    # Main summary
    st.markdown(result.final_summary)

    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Iterations", result.total_iterations)
    with col2:
        st.metric("Duration", f"{result.duration_seconds:.1f}s")
    with col3:
        st.metric("Sources", len(result.sources))

    # Sources
    if result.sources:
        with st.expander("📚 Sources", expanded=False):
            for source in result.sources:
                if source.url:
                    st.markdown(f"- [{source.title or source.url}]({source.url})")
                    if source.description:
                        st.caption(source.description)

    # Research steps
    if result.steps:
        with st.expander("📝 Research Steps", expanded=False):
            for step in result.steps:
                st.markdown(f"**Step {step.iteration}: {step.question}**")
                st.markdown(step.findings)
                st.progress(step.confidence, text=f"Confidence: {step.confidence:.0%}")
                st.divider()


def display_agent_events_inline(events: list[AgentEvent]) -> None:
    """Display agent events inline in the chat (not in an expander)."""
    if not events:
        return

    for event in events:
        event_text = format_agent_event(event)

        # Color code by event type
        if event.event_type == "agent_error":
            st.error(event_text)
        elif event.event_type == "agent_result":
            st.success(event_text)
        elif event.event_type == "agent_thinking":
            st.info(event_text)
        else:
            st.markdown(event_text)


def render_chat_message(msg: ChatMessage) -> None:
    """Render a single chat message."""
    with st.chat_message(msg.role):
        if msg.message_type == "research_result":
            # Display the research result with formatting
            result = msg.metadata.get("result")
            events = msg.metadata.get("events", [])

            if events:
                display_agent_events_inline(events)

            if result:
                st.divider()
                display_research_result(result)
            else:
                st.markdown(msg.content)

        elif msg.message_type == "agent_steps":
            # Display intermediate steps
            events = msg.metadata.get("events", [])
            display_agent_events_inline(events)
            st.markdown(msg.content)

        else:
            # Regular text message
            st.markdown(msg.content)


def build_context_query(user_input: str) -> str:
    """Build a query with conversation context for follow-up questions."""
    if not st.session_state.conversation_context:
        return user_input

    # Include recent context for follow-up questions
    context_summary = "\n".join(
        [
            f"Previous Q: {ctx['query']}\nKey findings: {ctx['summary'][:200]}..."
            for ctx in st.session_state.conversation_context[-2:]  # Last 2 exchanges
        ]
    )

    return f"""Given this conversation context:
{context_summary}

New question: {user_input}

Please research this question, taking into account the previous context if relevant."""


def poll_workflow_progress(
    client: ResearchApiClient,
    workflow_id: str,
    status_placeholder: Any,
    events_container: Any,
) -> tuple[ResearchResult | None, list[AgentEvent]]:
    """Poll workflow progress and display updates."""
    last_event_count = 0
    all_events: list[AgentEvent] = []

    while True:
        try:
            # Get current status
            status = client.get_status(workflow_id)

            # Update status display
            status_text = f"🔄 **Status**: {status.status}"
            if status.current_phase:
                status_text += f" | **Phase**: {status.current_phase}"
            status_text += f" | Steps: {status.research_steps}"
            status_placeholder.markdown(status_text)

            # Get agent events
            events = client.get_agent_events(workflow_id)
            if len(events) > last_event_count:
                # New events to display in chat
                all_events = events
                # Re-render all events in the container
                with events_container:
                    for event in events:
                        event_text = format_agent_event(event)
                        if event.event_type == "agent_error":
                            st.error(event_text)
                        elif event.event_type == "agent_result":
                            st.success(event_text)
                        elif event.event_type == "agent_thinking":
                            st.info(event_text)
                        else:
                            st.markdown(event_text)
                last_event_count = len(events)

            # Check if complete
            if status.status == "completed":
                break
            elif status.status == "failed":
                # Workflow failed, don't try to get result
                return None, all_events

            time.sleep(1.5)  # Poll interval

        except Exception as e:
            st.error(f"Error polling status: {e}")
            break

    # Get final result (only for completed workflows)
    result = None
    try:
        result = client.get_result(workflow_id)
    except Exception as e:
        st.error(f"Error getting result: {e}")

    return result, all_events


def process_user_input(user_input: str) -> None:
    """Process user input and run research."""
    # Add user message to chat
    user_msg = ChatMessage(role="user", content=user_input)
    st.session_state.messages.append(user_msg)

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build query with context
    query = build_context_query(user_input)

    # Show assistant thinking
    with st.chat_message("assistant"):
        status_placeholder = st.empty()
        events_container = st.container()
        status_placeholder.markdown("🔍 *Starting research...*")

        try:
            client = get_api_client()

            # Start the research workflow
            workflow_id = client.start_research(
                query=query,
                depth=st.session_state.research_depth,
                max_iterations=st.session_state.max_iterations,
            )
            st.session_state.current_workflow_id = workflow_id

            # Poll for progress (events displayed in events_container)
            result, events = poll_workflow_progress(
                client, workflow_id, status_placeholder, events_container
            )

            # Clear status placeholder
            status_placeholder.empty()

            if result:
                st.divider()
                # Display result
                display_research_result(result)

                # Add to conversation context
                st.session_state.conversation_context.append(
                    {
                        "query": user_input,
                        "summary": result.final_summary,
                        "workflow_id": workflow_id,
                    }
                )

                # Add assistant message to history
                assistant_msg = ChatMessage(
                    role="assistant",
                    content=result.final_summary,
                    message_type="research_result",
                    metadata={"result": result, "events": events},
                )
                st.session_state.messages.append(assistant_msg)

            else:
                error_msg = "Research workflow did not complete successfully."
                st.error(error_msg)
                st.session_state.messages.append(
                    ChatMessage(
                        role="assistant",
                        content=error_msg,
                        message_type="text",
                    )
                )

        except Exception as e:
            status_placeholder.empty()
            error_msg = f"An error occurred: {e}"
            st.error(error_msg)
            st.session_state.messages.append(
                ChatMessage(
                    role="assistant",
                    content=error_msg,
                    message_type="text",
                )
            )


def render_sidebar() -> None:
    """Render the sidebar with settings and controls."""
    with st.sidebar:
        st.title("⚙️ Settings")

        # API Configuration
        st.subheader("API Connection")
        api_url = st.text_input(
            "API URL",
            value=st.session_state.api_url,
            help="URL of the FastAPI backend",
        )
        if api_url != st.session_state.api_url:
            st.session_state.api_url = api_url
            st.session_state.api_client = None  # Reset client

        # Health check button
        if st.button("Check Connection", use_container_width=True):
            healthy, message = check_api_health()
            if healthy:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")

        st.divider()

        # Research Settings
        st.subheader("Research Settings")

        depth_options = {
            "Quick (1 iteration)": ResearchDepth.QUICK,
            "Standard (3 iterations)": ResearchDepth.STANDARD,
            "Deep (5+ iterations)": ResearchDepth.DEEP,
        }
        selected_depth = st.selectbox(
            "Research Depth",
            options=list(depth_options.keys()),
            index=1,  # Default to Standard
            help="How thorough the research should be",
        )
        st.session_state.research_depth = depth_options[selected_depth]

        max_iter = cast(
            int,
            st.slider(
                "Max Iterations",
                min_value=1,
                max_value=10,
                value=st.session_state.max_iterations,
                help="Maximum number of research iterations",
            ),
        )
        st.session_state.max_iterations = max_iter

        st.divider()

        # Conversation Controls
        st.subheader("Conversation")

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_context = []
            st.session_state.current_workflow_id = None
            st.rerun()

        # Show conversation stats
        st.caption(f"Messages: {len(st.session_state.messages)}")
        st.caption(f"Context items: {len(st.session_state.conversation_context)}")

        st.divider()

        # Help section
        with st.expander("❓ Help"):
            st.markdown(
                """
            **How to use:**
            1. Type your research question in the chat
            2. The AI will research and provide findings
            3. Ask follow-up questions for more detail

            **Tips:**
            - Use "Quick" depth for simple questions
            - Use "Deep" for complex topics
            - Follow-up questions use conversation context
            """
            )


def main() -> None:
    """Main application entry point."""
    init_session_state()

    # Title
    st.title("🔬 Deep Research Assistant")
    st.caption(
        "Ask me anything! I'll research it using multiple AI agents and provide comprehensive answers."
    )

    # Render sidebar
    render_sidebar()

    # Display chat history
    for msg in st.session_state.messages:
        render_chat_message(msg)

    # Chat input
    if user_input := st.chat_input("Ask a research question..."):
        process_user_input(user_input)


if __name__ == "__main__":
    main()
