import streamlit as st

from demo_core import EXAMPLES, MAX_CHARS, get_guard, inspect_text, result_rows

st.set_page_config(
    page_title="GuardFlow · Agent Prompt Firewall",
    page_icon="🛡️",
    layout="wide",
)

with st.spinner("Loading GuardFlow and local detection models…"):
    try:
        get_guard()
        st.session_state["guardflow_startup_error"] = None
    except Exception as exc:
        st.session_state["guardflow_startup_error"] = (
            f"{type(exc).__name__}: {exc}"
        )

st.title("GuardFlow · Agent Prompt Firewall")
st.caption(
    "A user prompt enters an AI agent. GuardFlow checks it before the agent "
    "can access mock records or call a tool."
)

st.warning(
    "Use synthetic examples only. Never paste real patient, financial, or "
    "confidential data. This demo makes no external LLM calls, stores no chat "
    "history, and does not intentionally log raw submissions. Hosting providers "
    "may collect operational telemetry."
)

startup_error = st.session_state.get("guardflow_startup_error")
if startup_error:
    st.error(f"GuardFlow failed to initialize: {startup_error}")
    st.info(
        "The PII and prompt-injection guards download local models on first "
        "startup. Check internet access to Hugging Face, available memory and "
        "disk space, then restart the app."
    )

with st.sidebar:
    st.subheader("Synthetic agent data")
    st.write(
        "The mock agent has access to a fictional customer profile and a fake "
        "development configuration. Tool actions are simulated and only proceed "
        "when GuardFlow allows the prompt."
    )
    st.caption("No real records, credentials, external APIs, or LLM are connected.")

sample = st.selectbox("Prompt scenario", list(EXAMPLES))
prompt = st.text_area(
    "User prompt",
    value=EXAMPLES[sample],
    max_chars=MAX_CHARS,
    height=150,
    placeholder="Ask the demo agent something…",
)

if st.button(
    "Send to guarded agent",
    type="primary",
    disabled=bool(startup_error),
):
    try:
        with st.spinner("Inspecting prompt with the loaded GuardFlow pipeline…"):
            result, elapsed_ms = inspect_text(prompt)

        st.metric("Pipeline latency", f"{elapsed_ms:.2f} ms")
        allowed = result.allowed
        st.metric(
            "GuardFlow decision",
            "ALLOW · agent may continue"
            if allowed
            else "BLOCK · agent and tools stopped",
        )

        st.subheader("Agent action")
        if allowed:
            st.success(
                "GuardFlow allowed this prompt. In a real integration, the agent "
                "could continue with only its authorized data and tools."
            )
            st.info(
                "This playground does not call an LLM or execute tools. "
                "The security decision shown below comes from GuardFlow."
            )
        else:
            st.error("The agent did not receive the prompt and no tool action ran.")

        st.subheader("Guard-by-guard inspection")
        st.dataframe(
            result_rows(result),
            use_container_width=True,
            hide_index=True,
        )

        if result.text and result.text != prompt:
            st.subheader("GuardFlow processed text")
            st.code(result.text, language="text")

    except Exception as exc:
        st.error(f"GuardFlow inspection failed: {type(exc).__name__}: {exc}")
        st.info(
            "Check the terminal running Streamlit for the full traceback. "
            "If model initialization failed, check Hugging Face connectivity, "
            "available memory, and disk space, then restart the app."
        )