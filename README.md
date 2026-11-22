# LLM-Based Paper Summary and Presentation Planner

This project implements a CrewAI-based agentic system that summarizes an academic paper and generates a presentation plan. It uses Hugging Face LLM enhancement by default when `HF_TOKEN` is available, and falls back to a deterministic local pipeline when the token or network is unavailable.

## Main Features

- Reads `.txt`, `.md`, or `.pdf` paper files.
- Extracts title, authors, abstract, sections, and keywords.
- Uses multiple LLM-enhanced agents to summarize the research problem, method, contributions, and limitations.
- Generates an 8-slide presentation outline.
- Generates natural speaker notes and expected Q&A.
- Writes Markdown, JSON, and workflow log outputs.
- Supports strict LLM mode with `--require-llm`.

## Installation

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install packages:

```bash
python -m pip install -r requirements.txt
```

## Hugging Face Token

For LLM-based output, set a Hugging Face token.

Windows PowerShell:

```powershell
$env:HF_TOKEN="hf_your_token_here"
```

macOS/Linux:

```bash
export HF_TOKEN="hf_your_token_here"
```

Do not hard-code the token in the source code.

## Run

```bash
python run.py --input sample_papers/sample_ai_paper.txt --output outputs --print-summary
```

PDF input is also supported:

```bash
python run.py --input path/to/paper.pdf --output outputs --print-summary
```

Choose a model:

```bash
python run.py --input sample_papers/sample_ai_paper.txt --model Qwen/Qwen2.5-1.5B-Instruct --output outputs --print-summary
```

Require successful LLM calls:

```bash
python run.py --input sample_papers/sample_ai_paper.txt --require-llm --output outputs --print-summary
```

Disable LLM enhancement:

```bash
python run.py --input sample_papers/sample_ai_paper.txt --no-llm --output outputs --print-summary
```

## Output

The system creates:

- `outputs/paper_presentation_report.md`
- `outputs/paper_presentation_report.json`
- `outputs/paper_presentation_workflow.txt`

## Tests

```bash
python -m pytest tests
```
