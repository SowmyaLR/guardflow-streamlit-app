import streamlit as st

from demo_core import (
    EXAMPLES,
    GUARDS,
    INJECTION_THRESHOLD,
    MAX_CHARS,
    MAX_TOKENS,
    WARNING_TOKENS,
    InvalidInput,
    PromptInjectionFailed,
    inspect_text,
)

GUARD_HELP = {
    "token_limit": (
        f"Checks size first. Warns from {WARNING_TOKENS} estimated tokens and blocks "
        f"above {MAX_TOKENS} before the other guards run."
    ),
    "input_sanitizer": "Normalizes invisible Unicode and control characters before later checks.",
    "secrets": "Redacts likely credentials before the processed text moves downstream.",
    "prompt_injection": f"Uses a local classifier and blocks at a score of {INJECTION_THRESHOLD:.2f}.",
}

INTEGRATION_EXAMPLE = f"""from guardflow import (
    GuardFlow, InputSanitizer, PromptInjectionGuard,
    SecretsGuard, TokenLimitGuard,
)

guard = GuardFlow(guards=[
    TokenLimitGuard(max_tokens={MAX_TOKENS}, warning_tokens={WARNING_TOKENS}),
    InputSanitizer(),
    SecretsGuard(),
    PromptInjectionGuard(threshold={INJECTION_THRESHOLD}),
])

def guarded_invoke(prompt, invoke_model):
    result = guard.inspect(prompt)
    if not result.allowed:
        raise ValueError("Prompt blocked by GuardFlow")
    return invoke_model(result.text)
"""


def main():
    st.set_page_config(
        page_title="GuardFlow Security Playground",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    with st.sidebar:
        st.header("About GuardFlow")
        st.write(
            "GuardFlow is a local-first Python SDK that lets you compose checks for "
            "untrusted input. Each guard reports its action and why it took it. "
            "A guard can also pass modified text to the next check."
        )
        st.markdown(
            "- [GuardFlow on GitHub](https://github.com/SowmyaLR/GuardFlow)\n"
            "- [GuardFlow on PyPI](https://pypi.org/project/guardflow/)\n"
            "- [Hugging Face demo](https://huggingface.co/spaces/lrsowmya/guardflow-demo-app)"
        )

    st.title("GuardFlow Security Playground")
    st.markdown("**Check untrusted input before an LLM or agent can act.**")
    st.write(
        "Put GuardFlow between incoming text and your model call. It can stop oversized "
        "requests early, clean copied text, redact likely credentials, and flag attempts "
        "to override instructions. Try a developer scenario to see what your application "
        "would receive from the SDK."
    )
    st.markdown("**Incoming prompt → GuardFlow → Application decision**")
    st.caption(
        "If allowed, pass GuardFlow’s processed text downstream. If blocked, stop the "
        "request before calling the model or tools. This playground only runs the checks."
    )
    st.warning(
        "Use synthetic text only. Keep real credentials, personal data, and confidential "
        "content out of this demo. Your submission is processed on the app server."
    )

    with st.expander("Use GuardFlow in your Python app"):
        st.write(
            "Install the extras for secrets detection and prompt injection. "
            "Pass your model client’s callable as `invoke_model`."
        )
        st.code("python -m pip install 'guardflow[secrets,injection]==0.1.0'", language="bash")
        st.code(INTEGRATION_EXAMPLE, language="python")
        st.caption(
            "Use the pipeline decision, `result.allowed`, even when individual guards "
            "report warnings, sanitization, or redaction. Keep authorization checks "
            "in place for tools and data access."
        )

    pipeline, editor = st.columns([1, 2], gap="large")
    with pipeline:
        st.subheader("Guard pipeline")
        st.caption("Checked guards run in order. Each sees the text left by the previous guard.")
        selected = []
        for name, label in GUARDS.items():
            if st.checkbox(label, value=True, key=name):
                selected.append(name)
            st.caption(GUARD_HELP[name])
        if "prompt_injection" in selected:
            st.caption("The first prompt-injection check may take longer while the model loads.")

    with editor:
        st.subheader("Test a prompt")
        sample = st.selectbox("Developer scenario", options=list(EXAMPLES))
        example = EXAMPLES[sample]
        st.caption(example.context)
        with st.form("inspection", clear_on_submit=True):
            prompt = st.text_area(
                "Prompt to inspect",
                value=example.prompt,
                height=220,
                max_chars=MAX_CHARS,
                help=f"Up to {MAX_CHARS:,} characters. The editor resets to the selected example on submit.",
            )
            submitted = st.form_submit_button("Inspect with GuardFlow", type="primary")

    if submitted:
        show_inspection(prompt, selected)


def show_inspection(prompt, selected):
    try:
        with st.spinner("Running selected guards…"):
            allowed, latency, rows, _token_count = inspect_text(prompt, selected)
    except InvalidInput as error:
        st.warning(str(error))
        return
    except PromptInjectionFailed:
        st.error(
            "The prompt-injection check could not finish. Check the app server's "
            "model download access and available memory, then retry."
        )
        return
    except Exception:
        st.error("GuardFlow could not complete the inspection. Try again with a synthetic example.")
        return

    st.subheader("Inspection results")
    decision, timing = st.columns(2)
    decision.metric("Application decision", "ALLOW" if allowed else "BLOCK")
    timing.metric("Total guard latency", f"{latency:.2f} ms")
    if not allowed:
        blocked_by = next(row["Guard"] for row in rows if row["Decision"] == "BLOCK")
        st.error(f"{blocked_by} blocked this prompt. An application should stop here.")
    elif any(row["Decision"] in {"SANITIZE", "REDACT"} for row in rows):
        st.success("The application can continue with the processed text in `result.text`.")
    else:
        st.success("The application can continue with `result.text`. Review any warnings below.")

    st.dataframe(
        rows,
        hide_index=True,
        column_config={
            "Latency (ms)": st.column_config.NumberColumn(format="%.3f"),
            "Injection score": st.column_config.NumberColumn(
                format="%.4f",
                help=f"Classifier score between 0 and 1. The block threshold is {INJECTION_THRESHOLD:.2f}.",
            ),
        },
    )
    st.caption("Results show findings and timings without replaying submitted or processed text.")


if __name__ == "__main__":
    main()
