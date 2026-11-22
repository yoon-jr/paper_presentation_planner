"""Shared state models for the paper presentation planner."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PaperState:
    input_path: str = ""
    raw_text: str = ""
    title: str = "Untitled Paper"
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    problem: str = ""
    method: str = ""
    contributions: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    slide_plan: List[Dict[str, Any]] = field(default_factory=list)
    speaker_notes: List[Dict[str, str]] = field(default_factory=list)
    qa_items: List[Dict[str, str]] = field(default_factory=list)
    quality_review: Dict[str, Any] = field(default_factory=dict)
    workflow_log: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    framework_status: str = "CrewAI metadata mode"
    llm_enabled: bool = True
    llm_required: bool = False
    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    llm_provider: str = "auto"
    llm_usage: List[Dict[str, Any]] = field(default_factory=list)
    output_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
