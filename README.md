# GuardFlow Security Playground

Try all four non-PII guards from the published [GuardFlow package](https://pypi.org/project/guardflow/) on synthetic prompts. The Streamlit app displays the actual pipeline decision, individual guard actions, and execution times.

Run GuardFlow before the application calls a model or gives an agent access to tools. If `result.allowed` is true, use the processed `result.text` as model input. If it is false, stop the request. Expand **Use GuardFlow in your Python app** in the playground for a copyable example.

- **TokenLimitGuard** estimates tokens, warns at 160, and blocks above 200. The app also caps input at 4,000 characters.
- **InputSanitizer** normalizes invisible characters and control sequences before the secrets scan.
- **SecretsGuard** uses detect-secrets to identify and redact likely credentials by matching patterns locally.
- **PromptInjectionGuard** uses the [ProtectAI DeBERTa classifier](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) and displays GuardFlow's injection score. GuardFlow blocks at its default threshold of 0.85.

All four guards appear as checked boxes under **Guard pipeline**, in the order listed above. A block stops the pipeline and marks subsequent selected guards as skipped. The prompt-injection model loads only when that guard runs and is then reused. Its first download requires Hugging Face access and about 700 MB of disk space. Deselect PromptInjectionGuard to run the other checks without loading the model. The app excludes PII detection and its dependencies.

## Review the developer scenarios

| Scenario | What to inspect |
| --- | --- |
| Pull request review | Baseline allow for a checkout retry change |
| Config review with a dummy password | SecretsGuard redaction decision |
| Broken config key after copy and paste | InputSanitizer decision for an invisible character in YAML |
| Issue triage with an untrusted comment | Prompt-injection score and block decision |
| On-call triage with a short or expanded log excerpt | Compare the token warning with an early block that skips later guards |

The scenarios use fictional repositories, configuration values, and staging logs. The editor is prefilled so reviewers can change the input and compare actual guard results.

## Run locally

Use Python 3.12 and create a fresh environment.

```bash
python3.12 -m venv .venv-playground
source .venv-playground/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

On Windows PowerShell, create the environment with `py -3.12 -m venv .venv-playground` and activate it with `./.venv-playground/Scripts/Activate.ps1`.

## Deploy to Streamlit Community Cloud

1. Push the Streamlit files to your GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), choose **Create app** and select your GitHub repository and branch.
3. Set the main file path to `streamlit_app.py`. Community Cloud installs dependencies from the root `requirements.txt`.
4. Select **Python 3.12** in **Advanced settings** and deploy. Leave the secrets field empty.

See the [Community Cloud deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) for details.

The Linux requirements use CPU-only PyTorch. Allow time for the initial download and verify the host has enough memory to load the model. Choose **Issue triage with an untrusted comment** and inspect it to verify the classifier after deployment.

## Privacy

Use synthetic text only. Your prompt is sent to the Streamlit server for inspection and the editor resets to the selected example on submission. The app does not write prompts to logs, cache, or persistent storage, send prompts to an LLM or a verification service, or display submitted or transformed text in results.

## Tests

Run `python -m unittest -v` in the same environment. Tests exercise the published guards and the Streamlit interface. The injection test runs the real classifier and requires the model in the local cache or access to download it.
