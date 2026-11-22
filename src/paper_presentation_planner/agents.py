"""Agent implementations for the paper summary and presentation planner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llm import HuggingFaceLLMClient
from .state import PaperState
from .tools import (
    bulletize,
    ensure_dir,
    extract_abstract,
    extract_authors,
    find_sentences_by_patterns,
    first_nonempty_line,
    keyword_sentences,
    normalize_text,
    read_input_file,
    safe_json_dump,
    split_sections,
    split_sentences,
    top_keywords,
)


def _paper_context(state: PaperState, max_chars: int = 7000) -> str:
    parts = [
        f"Title: {state.title}",
        f"Authors: {', '.join(state.authors) if state.authors else 'Unknown'}",
        f"Abstract: {state.abstract}",
        "Keywords: " + ", ".join(state.keywords[:12]),
        "Sections: " + ", ".join(state.sections.keys()),
        "Text excerpt:\n" + state.raw_text[:max_chars],
    ]
    return "\n\n".join(p for p in parts if p)


def _as_list(value: Any, default: Optional[List[str]] = None, limit: int = 8) -> List[str]:
    if default is None:
        default = []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:limit]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return default[:limit]


class BaseAgent:
    name = "Base Agent"

    def __init__(self, llm_client: Optional[HuggingFaceLLMClient] = None) -> None:
        self.llm_client = llm_client

    def log(self, state: PaperState, message: str) -> None:
        state.workflow_log.append(f"{self.name}: {message}")

    def llm_json(
        self,
        state: PaperState,
        system_prompt: str,
        user_prompt: str,
        fallback_data: Dict[str, Any],
        max_tokens: int = 1800,
    ) -> Dict[str, Any]:
        if not state.llm_enabled or self.llm_client is None:
            return fallback_data
        result = self.llm_client.complete_json(
            agent_name=self.name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback_data=fallback_data,
            max_tokens=max_tokens,
        )
        status = dict(result.data.get("llm_status", {}))
        status.setdefault("agent", self.name)
        state.llm_usage.append(status)
        if result.used_llm:
            self.log(state, "Enhanced output with Hugging Face LLM.")
        else:
            msg = status.get("error") or result.error or "LLM fallback used."
            state.warnings.append(f"{self.name} used fallback instead of LLM: {msg}")
            self.log(state, "Used deterministic fallback because LLM enhancement was unavailable.")
        return result.data


class PaperLoaderAgent(BaseAgent):
    name = "Paper Loader Agent"

    def run(self, state: PaperState) -> PaperState:
        raw = read_input_file(state.input_path)
        state.raw_text = normalize_text(raw)
        if len(state.raw_text) < 500:
            state.warnings.append("The input paper text is short; the generated analysis may be limited.")
        self.log(state, f"Loaded {len(state.raw_text)} characters from {state.input_path}.")
        return state


class PaperStructureAgent(BaseAgent):
    name = "Paper Structure Agent"

    def run(self, state: PaperState) -> PaperState:
        state.title = first_nonempty_line(state.raw_text)
        state.authors = extract_authors(state.raw_text)
        state.sections = split_sections(state.raw_text)
        state.abstract = extract_abstract(state.raw_text, state.sections)
        state.keywords = top_keywords(state.raw_text, 12)
        self.log(state, f"Parsed {len(state.sections)} sections and {len(state.keywords)} keywords.")
        return state


class ProblemMotivationAgent(BaseAgent):
    name = "Problem and Motivation Agent"

    def run(self, state: PaperState) -> PaperState:
        search_space = "\n".join(
            [state.abstract, state.sections.get("introduction", ""), state.sections.get("full text", "")[:2500]]
        )
        candidates = find_sentences_by_patterns(
            search_space,
            [r"problem", r"challenge", r"difficult", r"motivat", r"aim", r"goal", r"address", r"문제", r"어려", r"목표", r"해결"],
            5,
        )
        if not candidates:
            candidates = split_sentences(search_space)[:3]
        fallback = {
            "problem": " ".join(bulletize(candidates, limit=3, max_len=260)),
            "motivation_bullets": bulletize(candidates, limit=5),
        }
        data = self.llm_json(
            state,
            "You are a research seminar mentor. Return only valid JSON.",
            "Analyze the research problem and motivation of this paper. Return JSON with keys: problem, motivation_bullets. "
            "motivation_bullets must be a list of 3-5 concise Korean bullet strings.\n\n" + _paper_context(state, 5500),
            fallback,
        )
        state.problem = str(data.get("problem") or fallback["problem"])
        state.summary["problem_and_motivation"] = _as_list(data.get("motivation_bullets"), fallback["motivation_bullets"], 5)
        self.log(state, "Identified research problem and motivation.")
        return state


class MethodAnalysisAgent(BaseAgent):
    name = "Method Analysis Agent"

    def run(self, state: PaperState) -> PaperState:
        method_text = "\n".join([
            state.sections.get("method", ""),
            state.sections.get("experiments", "")[:1500],
            state.raw_text[:2500] if not state.sections.get("method") else "",
        ])
        candidates = find_sentences_by_patterns(
            method_text,
            [r"propos", r"method", r"model", r"algorithm", r"framework", r"architecture", r"train", r"dataset", r"제안", r"모델", r"방법", r"구조", r"학습"],
            6,
        )
        if not candidates:
            candidates = keyword_sentences(method_text or state.raw_text, state.keywords[:6], 4)
        fallback = {
            "method_summary": " ".join(bulletize(candidates, limit=4, max_len=260)),
            "method_bullets": bulletize(candidates, limit=6),
        }
        data = self.llm_json(
            state,
            "You are a technical paper reviewer. Return only valid JSON.",
            "Summarize the proposed method in presentation-friendly Korean. Return JSON with keys: method_summary, method_bullets. "
            "method_bullets must be a list of 3-6 concise strings.\n\n" + _paper_context(state, 6500),
            fallback,
        )
        state.method = str(data.get("method_summary") or fallback["method_summary"])
        state.summary["method"] = _as_list(data.get("method_bullets"), fallback["method_bullets"], 6)
        self.log(state, "Summarized the proposed method or approach.")
        return state


class ContributionLimitationAgent(BaseAgent):
    name = "Contribution and Limitation Agent"

    def run(self, state: PaperState) -> PaperState:
        full = state.raw_text
        contribution_sentences = find_sentences_by_patterns(
            full,
            [r"contribution", r"we propose", r"we present", r"outperform", r"improve", r"achieve", r"result", r"기여", r"제안", r"향상", r"성능", r"결과"],
            8,
        )
        limitation_sentences = find_sentences_by_patterns(
            full,
            [r"limitation", r"future work", r"however", r"although", r"threat", r"only", r"한계", r"향후", r"하지만", r"제한"],
            6,
        )
        if not contribution_sentences:
            contribution_sentences = keyword_sentences(full, state.keywords[:8], 5)
        if not limitation_sentences:
            limitation_sentences = [
                "The paper may require further validation on broader datasets or settings.",
                "The presentation should mention possible assumptions and generalization limits.",
            ]
        fallback = {
            "contributions": bulletize(contribution_sentences, limit=5),
            "limitations": bulletize(limitation_sentences, limit=4),
        }
        data = self.llm_json(
            state,
            "You are a skeptical academic reviewer. Return only valid JSON.",
            "Extract the paper's main contributions and limitations in Korean. Return JSON with keys: contributions, limitations. "
            "Each value must be a list of concise strings.\n\n" + _paper_context(state, 7000),
            fallback,
        )
        state.contributions = _as_list(data.get("contributions"), fallback["contributions"], 5)
        state.limitations = _as_list(data.get("limitations"), fallback["limitations"], 4)
        state.summary["contributions"] = state.contributions
        state.summary["limitations"] = state.limitations
        self.log(state, "Extracted contributions and limitations.")
        return state


class SlidePlannerAgent(BaseAgent):
    name = "Slide Planner Agent"

    def run(self, state: PaperState) -> PaperState:
        title = state.title
        keywords = ", ".join(state.keywords[:5]) if state.keywords else "key concepts"
        method_bullets = state.summary.get("method", [])[:3]
        contribution_bullets = state.contributions[:3]
        limitation_bullets = state.limitations[:2]
        fallback_slides = [
            {"slide": 1, "title": "Title and Presentation Goal", "bullets": [title, "Explain the paper's problem, method, results, and limitations."], "purpose": "Open the presentation and clarify the goal."},
            {"slide": 2, "title": "Background and Motivation", "bullets": state.summary.get("problem_and_motivation", [])[:3] or [state.problem], "purpose": "Explain why the research problem matters."},
            {"slide": 3, "title": "Research Problem", "bullets": [state.problem or "Summarize the central problem addressed by the paper.", f"Important keywords: {keywords}"], "purpose": "Define the main problem and scope."},
            {"slide": 4, "title": "Proposed Method", "bullets": method_bullets or [state.method or "Describe the proposed method."], "purpose": "Explain the core technical idea."},
            {"slide": 5, "title": "Experiments or Evaluation", "bullets": self._experiment_bullets(state), "purpose": "Show how the paper evaluates its approach."},
            {"slide": 6, "title": "Key Contributions", "bullets": contribution_bullets or ["Summarize the main contributions of the paper."], "purpose": "Highlight what is new or valuable."},
            {"slide": 7, "title": "Limitations and Discussion", "bullets": limitation_bullets or ["Discuss limitations and future work."], "purpose": "Critically evaluate the paper."},
            {"slide": 8, "title": "Conclusion and Takeaways", "bullets": ["Summarize the problem, method, and contributions in one minute.", "End with why the paper is useful and what remains open."], "purpose": "Close the presentation with clear takeaways."},
        ]
        data = self.llm_json(
            state,
            "You are an expert academic presentation designer. Return only valid JSON.",
            "Create a natural 8-slide presentation plan in Korean. Return JSON with key slides. "
            "slides must be a list of 8 objects with slide, title, purpose, bullets. bullets must be 2-4 concise strings.\n\n"
            f"Problem: {state.problem}\nMethod: {state.method}\nContributions: {state.contributions}\nLimitations: {state.limitations}\n\nPaper context:\n{_paper_context(state, 5000)}",
            {"slides": fallback_slides},
            max_tokens=3000,
        )
        slides = data.get("slides")
        if isinstance(slides, list) and len(slides) >= 6:
            cleaned = []
            for idx, slide in enumerate(slides[:10], start=1):
                if not isinstance(slide, dict):
                    continue
                cleaned.append({
                    "slide": int(slide.get("slide") or idx),
                    "title": str(slide.get("title") or f"Slide {idx}"),
                    "bullets": _as_list(slide.get("bullets"), [], 4),
                    "purpose": str(slide.get("purpose") or "Explain this part of the paper."),
                })
            state.slide_plan = cleaned if len(cleaned) >= 6 else fallback_slides
        else:
            state.slide_plan = fallback_slides
        self.log(state, f"Created a {len(state.slide_plan)}-slide presentation plan.")
        return state

    def _experiment_bullets(self, state: PaperState) -> List[str]:
        text = state.sections.get("experiments", "") or state.sections.get("discussion", "") or state.raw_text
        candidates = find_sentences_by_patterns(
            text,
            [r"experiment", r"evaluation", r"dataset", r"baseline", r"accuracy", r"result", r"performance", r"실험", r"평가", r"데이터", r"성능"],
            4,
        )
        return bulletize(candidates, limit=3) or ["Describe datasets, baselines, metrics, and main results."]


class SpeakerNotesAgent(BaseAgent):
    name = "Speaker Notes Agent"

    def run(self, state: PaperState) -> PaperState:
        fallback_notes = []
        for slide in state.slide_plan:
            bullets = slide.get("bullets", [])
            note = f"이 슬라이드에서는 {slide.get('title', '')}를 설명합니다. 목적은 {slide.get('purpose', '')}입니다. "
            if bullets:
                note += "특히 " + " / ".join(str(b) for b in bullets[:2]) + " 부분을 강조하면 좋습니다."
            fallback_notes.append({"slide": str(slide["slide"]), "title": slide["title"], "notes": note})
        data = self.llm_json(
            state,
            "You are a Korean-speaking presentation coach. Return only valid JSON.",
            "Write natural Korean speaker notes for each slide. Return JSON with key speaker_notes. "
            "speaker_notes must be a list of objects with slide, title, notes. Notes should be 2-4 sentences.\n\n"
            + json.dumps({"slides": state.slide_plan}, ensure_ascii=False),
            {"speaker_notes": fallback_notes},
            max_tokens=2800,
        )
        notes = data.get("speaker_notes")
        if isinstance(notes, list) and notes:
            state.speaker_notes = [
                {"slide": str(n.get("slide", i + 1)), "title": str(n.get("title", "")), "notes": str(n.get("notes", ""))}
                for i, n in enumerate(notes) if isinstance(n, dict)
            ] or fallback_notes
        else:
            state.speaker_notes = fallback_notes
        self.log(state, "Generated speaker notes for the slide plan.")
        return state


class QAPreparationAgent(BaseAgent):
    name = "Q&A Preparation Agent"

    def run(self, state: PaperState) -> PaperState:
        method_topic = state.keywords[0] if state.keywords else "the proposed method"
        limitation = state.limitations[0] if state.limitations else "The paper may require further validation."
        fallback_items = [
            {"question": "이 논문이 해결하려는 핵심 문제는 무엇인가?", "answer": state.problem or "논문은 서론에서 설명한 핵심 연구 문제를 다룹니다."},
            {"question": "제안 방법의 핵심 아이디어는 무엇인가?", "answer": state.method or f"핵심 아이디어는 {method_topic}와 관련이 있습니다."},
            {"question": "이 논문의 주요 기여점은 무엇인가?", "answer": "; ".join(state.contributions[:3]) if state.contributions else "새로운 방법, 분석 또는 실험 결과를 제시합니다."},
            {"question": "이 논문의 한계점은 무엇인가?", "answer": limitation},
            {"question": "향후 연구에서는 무엇을 확장할 수 있는가?", "answer": "더 다양한 설정에서 평가하거나 추가 baseline과 비교하고 실제 적용 가능성을 개선할 수 있습니다."},
        ]
        data = self.llm_json(
            state,
            "You are a seminar Q&A coach. Return only valid JSON.",
            "Generate 5-7 expected audience questions and strong Korean answers for a paper presentation. "
            "Return JSON with key qa_items, a list of objects with question and answer.\n\n"
            f"Summary: {state.summary}\nSlides: {state.slide_plan}\nLimitations: {state.limitations}",
            {"qa_items": fallback_items},
            max_tokens=2500,
        )
        qa = data.get("qa_items")
        if isinstance(qa, list) and qa:
            state.qa_items = [
                {"question": str(item.get("question", "")), "answer": str(item.get("answer", ""))}
                for item in qa if isinstance(item, dict) and item.get("question")
            ] or fallback_items
        else:
            state.qa_items = fallback_items
        self.log(state, "Prepared expected Q&A items.")
        return state


class QualityReviewAgent(BaseAgent):
    name = "Quality Review Agent"

    def run(self, state: PaperState) -> PaperState:
        issues: List[str] = []
        if len(state.raw_text) < 1000:
            issues.append("Input text is relatively short; analysis depth may be limited.")
        if not state.abstract:
            issues.append("Abstract could not be clearly identified.")
        if len(state.slide_plan) < 6:
            issues.append("Slide plan is shorter than recommended for a paper presentation.")
        if not state.contributions:
            issues.append("Contributions are weakly detected and should be checked manually.")
        score = 100 - len(issues) * 12
        fallback = {
            "completeness_score": max(40, score),
            "issues": issues,
            "recommendation": "Review the generated slide plan and adjust technical details before presentation.",
        }
        data = self.llm_json(
            state,
            "You are a strict final reviewer for an undergraduate assignment. Return only valid JSON.",
            "Review whether this paper presentation plan is complete, coherent, and useful. Return JSON with keys: completeness_score, issues, recommendation. "
            "issues must be a list of concise Korean strings.\n\n"
            + json.dumps({"slides": state.slide_plan, "speaker_notes": state.speaker_notes, "qa_items": state.qa_items}, ensure_ascii=False)[:7000],
            fallback,
            max_tokens=1400,
        )
        try:
            completeness = int(float(data.get("completeness_score", fallback["completeness_score"])))
        except Exception:
            completeness = fallback["completeness_score"]
        state.quality_review = {
            "completeness_score": max(0, min(100, completeness)),
            "issues": _as_list(data.get("issues"), fallback["issues"], 8),
            "recommendation": str(data.get("recommendation") or fallback["recommendation"]),
        }
        for issue in state.quality_review.get("issues", []):
            if issue not in state.warnings:
                state.warnings.append(issue)
        self.log(state, "Reviewed final output quality.")
        return state


class ReportWriterAgent(BaseAgent):
    name = "Report Writer Agent"

    def run(self, state: PaperState, output_dir: str, prefix: str = "paper_presentation") -> PaperState:
        ensure_dir(output_dir)
        md_path = str(Path(output_dir) / f"{prefix}_report.md")
        json_path = str(Path(output_dir) / f"{prefix}_report.json")
        workflow_path = str(Path(output_dir) / f"{prefix}_workflow.txt")
        Path(md_path).write_text(self._markdown_report(state), encoding="utf-8")
        safe_json_dump(state.to_dict(), json_path)
        Path(workflow_path).write_text("\n".join(state.workflow_log), encoding="utf-8")
        state.output_files = {"report": md_path, "json": json_path, "workflow": workflow_path}
        self.log(state, "Wrote Markdown, JSON, and workflow output files.")
        return state

    def _markdown_report(self, state: PaperState) -> str:
        authors = ", ".join(state.authors) if state.authors else "Unknown"
        used_count = sum(1 for item in state.llm_usage if item.get("used_huggingface_llm"))
        lines = [
            "# Paper Summary and Presentation Plan",
            "",
            f"## Title\n{state.title}",
            "",
            f"## Authors\n{authors}",
            "",
            f"## Framework Status\n{state.framework_status}",
            "",
            "## LLM Status",
            f"- LLM enabled: {state.llm_enabled}",
            f"- Hugging Face model: {state.llm_model}",
            f"- LLM agents used successfully: {used_count} / {len(state.llm_usage)}",
            "",
            "## Abstract / Overview",
            state.abstract or "No abstract detected.",
            "",
            "## Key Keywords",
            ", ".join(state.keywords) if state.keywords else "No keywords detected.",
            "",
            "## Research Problem and Motivation",
            state.problem or "Not clearly detected.",
            "",
            "## Method Summary",
            state.method or "Not clearly detected.",
            "",
            "## Contributions",
        ]
        lines.extend([f"- {c}" for c in state.contributions] or ["- Not clearly detected."])
        lines.extend(["", "## Limitations / Discussion Points"])
        lines.extend([f"- {l}" for l in state.limitations] or ["- Not clearly detected."])
        lines.extend(["", "## Slide-by-Slide Presentation Plan"])
        for slide in state.slide_plan:
            lines.append(f"### Slide {slide['slide']}. {slide['title']}")
            lines.append(f"Purpose: {slide.get('purpose', '')}")
            for bullet in slide.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")
        lines.extend(["## Speaker Notes"])
        for note in state.speaker_notes:
            lines.append(f"### Slide {note['slide']}. {note['title']}")
            lines.append(note["notes"])
            lines.append("")
        lines.extend(["## Expected Q&A"])
        for idx, item in enumerate(state.qa_items, start=1):
            lines.append(f"**Q{idx}. {item['question']}**")
            lines.append(f"A. {item['answer']}")
            lines.append("")
        lines.extend(["## Quality Review", f"Completeness score: {state.quality_review.get('completeness_score', 'N/A')} / 100"])
        for issue in state.quality_review.get("issues", []):
            lines.append(f"- {issue}")
        lines.append(state.quality_review.get("recommendation", ""))
        if state.warnings:
            lines.extend(["", "## Warnings"])
            lines.extend([f"- {w}" for w in state.warnings])
        lines.extend(["", "## Workflow Log"])
        lines.extend([f"- {entry}" for entry in state.workflow_log])
        return "\n".join(lines).strip() + "\n"
