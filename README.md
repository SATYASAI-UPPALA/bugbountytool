# LangGraph Kali Execution Agent

This project is a minimal LangGraph loop for a bug bounty assistant:

1. The model plans the next command.
2. A controlled shell tool runs the command.
3. The model analyzes output and decides whether to continue.
4. The loop stops when the model returns a final answer.

The model is called through the Hugging Face OpenAI-compatible endpoint shown in your example.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` before real command execution:

```env
KALI_DRY_RUN=false
KALI_WORKDIR=/path/to/allowed/workdir
```

## Run

```powershell
python -m src.agent "Enumerate example.com for public web security testing"
```

By default, `KALI_DRY_RUN=true`, so commands are printed but not executed.

## Important

Only run commands against systems where you have explicit authorization. Keep `KALI_DRY_RUN=true` until you have reviewed the generated command plan.
