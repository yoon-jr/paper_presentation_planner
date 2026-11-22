from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paper_presentation_planner import PaperPresentationWorkflow  # noqa: E402
from paper_presentation_planner.llm import DEFAULT_HF_MODEL, DEFAULT_HF_PROVIDER  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CrewAI-based paper summary and presentation planner")
    parser.add_argument("--input", required=True, help="Path to a paper file (.txt, .md, or .pdf)")
    parser.add_argument("--output", default="outputs", help="Directory where output files will be saved")
    parser.add_argument("--prefix", default="paper_presentation", help="Prefix for output file names")
    parser.add_argument("--model", default=DEFAULT_HF_MODEL, help="Hugging Face chat-completion model id")
    parser.add_argument("--provider", default=DEFAULT_HF_PROVIDER, help="Hugging Face Inference Provider, e.g., auto")
    parser.add_argument("--no-llm", action="store_true", help="Disable Hugging Face LLM enhancement")
    parser.add_argument("--require-llm", action="store_true", help="Fail if Hugging Face LLM enhancement is unavailable")
    parser.add_argument("--print-summary", action="store_true", help="Print a short summary after execution")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workflow = PaperPresentationWorkflow(
        use_llm=not args.no_llm,
        require_llm=args.require_llm,
        model=args.model,
        provider=args.provider,
    )
    state = workflow.run(input_path=args.input, output_dir=args.output, prefix=args.prefix)
    if args.print_summary:
        used_count = sum(1 for item in state.llm_usage if item.get("used_huggingface_llm"))
        print("Paper Presentation Planning completed successfully.")
        print(f"Framework status: {state.framework_status}")
        print(f"Title: {state.title}")
        print(f"Slides: {len(state.slide_plan)}")
        print(f"Q&A items: {len(state.qa_items)}")
        print(f"Hugging Face LLM agents used: {used_count} / {len(state.llm_usage)}")
        print(f"Report: {state.output_files.get('report')}")
        print(f"JSON: {state.output_files.get('json')}")
        print(f"Workflow: {state.output_files.get('workflow')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
