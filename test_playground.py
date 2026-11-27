import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from demo_core import EXAMPLES, GUARDS, MAX_CHARS, InvalidInput, inspect_text


class PlaygroundTests(unittest.TestCase):
    def test_examples_use_real_guard_decisions(self):
        expectations = {
            "Pull request review": (True, ["ALLOW", "ALLOW", "ALLOW", "ALLOW"]),
            "Config review with a dummy password": (True, ["ALLOW", "ALLOW", "REDACT", "ALLOW"]),
            "Broken config key after copy and paste": (True, ["ALLOW", "SANITIZE", "ALLOW", "ALLOW"]),
            "Issue triage with an untrusted comment": (False, ["ALLOW", "ALLOW", "ALLOW", "BLOCK"]),
            "On-call triage with a short log excerpt": (True, ["WARN", "ALLOW", "ALLOW", "ALLOW"]),
            "On-call triage with an expanded log excerpt": (
                False, ["BLOCK", "SKIPPED", "SKIPPED", "SKIPPED"]
            ),
        }
        for example, (expected_allowed, decisions) in expectations.items():
            with self.subTest(example=example):
                allowed, latency, rows, token_count = inspect_text(
                    EXAMPLES[example].prompt, GUARDS
                )
                self.assertEqual(allowed, expected_allowed)
                self.assertEqual([row["Decision"] for row in rows], decisions)
                self.assertGreaterEqual(latency, 0)
                self.assertGreater(token_count, 0)
                for row in rows:
                    if row["Decision"] == "SKIPPED":
                        self.assertIsNone(row["Latency (ms)"])
                    else:
                        self.assertGreaterEqual(row["Latency (ms)"], 0)

    def test_token_block_skips_prompt_injection(self):
        with patch("demo_core._prompt_injection_guard") as load_guard:
            prompt = EXAMPLES["On-call triage with an expanded log excerpt"].prompt
            allowed, _, rows, _ = inspect_text(prompt, GUARDS)
        self.assertFalse(allowed)
        self.assertEqual(rows[-1]["Decision"], "SKIPPED")
        load_guard.assert_not_called()

    def test_streamlit_runs_real_prompt_injection_guard(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("streamlit_app.py")), default_timeout=180
        ).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "ALLOW")

        app.selectbox[0].select("Issue triage with an untrusted comment").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "BLOCK")
        self.assertIn("PromptInjectionGuard blocked", app.error[0].value)
        results = app.dataframe[0].value
        self.assertEqual(list(results["Guard"]), list(GUARDS.values()))
        self.assertEqual(list(results["Decision"]), ["ALLOW", "ALLOW", "ALLOW", "BLOCK"])
        self.assertGreaterEqual(results["Injection score"].iloc[-1], 0.85)

    def test_playground_shows_all_four_guards_and_sdk_guidance(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("streamlit_app.py")), default_timeout=20
        ).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.header[0].value, "About GuardFlow")
        links = app.sidebar.markdown[-1].value
        self.assertIn("https://github.com/SowmyaLR/GuardFlow", links)
        self.assertIn("https://huggingface.co/spaces/lrsowmya/guardflow-demo-app", links)
        self.assertIn("**Incoming prompt → GuardFlow → Application decision**", [
            markdown.value for markdown in app.markdown
        ])
        self.assertIn("return invoke_model(result.text)", app.code[-1].value)
        self.assertEqual(
            [guard.label for guard in app.checkbox],
            ["TokenLimitGuard", "InputSanitizer", "SecretsGuard", "PromptInjectionGuard"],
        )
        self.assertTrue(all(guard.value for guard in app.checkbox))
        sample = "Config review with a dummy password"
        app.selectbox[0].select(sample).run()
        self.assertEqual(app.text_area[0].value, EXAMPLES[sample].prompt)
        self.assertIn(EXAMPLES[sample].context, [caption.value for caption in app.caption])

    def test_input_limits_and_selection(self):
        for prompt, selected in [(" ", GUARDS), ("a" * (MAX_CHARS + 1), GUARDS), ("Hello", [])]:
            with self.subTest(prompt_length=len(prompt), selected=selected):
                with self.assertRaises(InvalidInput):
                    inspect_text(prompt, selected)
        allowed, _, rows, token_count = inspect_text("a" * MAX_CHARS, ["input_sanitizer"])
        self.assertTrue(allowed)
        self.assertEqual([row["Guard"] for row in rows], ["InputSanitizer"])
        self.assertIsNone(token_count)

    def test_streamlit_run_shows_selected_guard_without_echo(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("streamlit_app.py")), default_timeout=20
        ).run()
        sample = "Config review with a dummy password"
        app.selectbox[0].select(sample).run()
        self.assertEqual(app.text_area[0].value, EXAMPLES[sample].prompt)
        for guard in app.checkbox:
            if guard.key != "secrets":
                guard.uncheck()
        app.run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "ALLOW")
        results = app.dataframe[0].value
        self.assertEqual(list(results["Decision"]), ["REDACT"])
        self.assertIn("1 credential", results["Finding"].iloc[0])
        self.assertIn("result.text", app.success[0].value)
        self.assertNotIn("demo-only-fake-value-4829", str(results))

    def test_streamlit_error_does_not_echo_library_exception(self):
        app = AppTest.from_file(
            str(Path(__file__).with_name("streamlit_app.py")), default_timeout=20
        ).run()
        with patch("demo_core.GuardFlow.inspect", side_effect=ValueError("raw-secret-marker")):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("could not complete", app.error[0].value)
        self.assertNotIn("raw-secret-marker", app.error[0].value)
