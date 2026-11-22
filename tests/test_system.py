from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paper_presentation_planner import PaperPresentationWorkflow


def test_workflow_runs_with_sample(tmp_path):
    sample = ROOT / "sample_papers" / "sample_ai_paper.txt"
    workflow = PaperPresentationWorkflow()
    state = workflow.run(str(sample), output_dir=str(tmp_path), prefix="test")
    assert state.title
    assert len(state.slide_plan) >= 8
    assert len(state.qa_items) >= 5
    assert Path(state.output_files["report"]).exists()


def test_sections_and_keywords_detected(tmp_path):
    sample = ROOT / "sample_papers" / "sample_ai_paper.txt"
    workflow = PaperPresentationWorkflow()
    state = workflow.run(str(sample), output_dir=str(tmp_path), prefix="test2")
    assert state.keywords
    assert state.abstract
    assert state.contributions
