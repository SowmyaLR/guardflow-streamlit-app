# GuardFlow Agent Prompt Firewall

A local Streamlit demo showing how GuardFlow can inspect user prompts before an AI agent continues. The app displays the overall decision, individual guard actions, and measured latency.

The demo includes synthetic examples for healthcare text, customer support, developer secrets, direct prompt injection, and a safe request. It does not connect to an LLM, use real customer records, or execute external tools.

## Requirements

- Python 3.10 or newer
- Internet access during installation, so Python packages and local model resources can be downloaded

## Run locally in a virtual environment

Open a terminal and change to the project directory:

```bash
cd /path/to/guardflow-streamlit-app

Create and activate a virtual environment.

macOS or Linux:
python3 -m venv .venv
source .venv/bin/activate
Windows PowerShell:
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
Install the dependencies:
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Start Streamlit:
python -m streamlit run streamlit_app.py