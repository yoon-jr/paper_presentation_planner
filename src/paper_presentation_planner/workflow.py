"""Workflow orchestration for the paper presentation planner."""
from __future__ import annotations

from .agents import (
    ContributionLimitationAgent,
    MethodAnalysisAgent,
    PaperLoaderAgent,
    PaperStructureAgent,
    ProblemMotivationAgent,
    QAPreparationAgent,
    QualityReviewAgent,
    ReportWriterAgent,
    SlidePlannerAgent,
    SpeakerNotesAgent,
)
from .crew_setup import build_crewai_metadata
from .llm import DEFAULT_HF_MODEL, DEFAULT_HF_PROVIDER, HuggingFaceLLMClient
from .state import PaperState


class PaperPresentationWorkflow:
    """CrewAI-based multi-agent workflow with optional Hugging Face LLM enhancement."""

    def __init__(
        self,
        use_llm: bool = True,
        require_llm: bool = False,
        model: str = DEFAULT_HF_MODEL,
        provider: str = DEFAULT_HF_PROVIDER,
    ) -> None:
        self.crew_metadata = build_crewai_metadata()
        self.use_llm = use_llm
        self.require_llm = require_llm
        self.model = model
        self.provider = provider
        self.llm_client = HuggingFaceLLMClient(
            model=model,
            provider=provider,
            allow_fallback=not require_llm,
        ) if use_llm else None
        llm_enabled_agents = [
            ProblemMotivationAgent(self.llm_client),
            MethodAnalysisAgent(self.llm_client),
            ContributionLimitationAgent(self.llm_client),
            SlidePlannerAgent(self.llm_client),
            SpeakerNotesAgent(self.llm_client),
            QAPreparationAgent(self.llm_client),
            QualityReviewAgent(self.llm_client),
        ]
        self.agents = [
            PaperLoaderAgent(),
            PaperStructureAgent(),
            *llm_enabled_agents,
        ]
        self.report_writer = ReportWriterAgent()

    def run(self, input_path: str, output_dir: str = "outputs", prefix: str = "paper_presentation") -> PaperState:
        state = PaperState(
            input_path=input_path,
            llm_enabled=self.use_llm,
            llm_required=self.require_llm,
            llm_model=self.model,
            llm_provider=self.provider,
        )
        llm_status = "disabled"
        if self.use_llm and self.llm_client is not None:
            llm_status = "enabled; HF_TOKEN detected" if self.llm_client.configured else "enabled; HF_TOKEN not detected, fallback available"
        if self.require_llm:
            llm_status += "; strict mode"
        state.framework_status = f"{self.crew_metadata.status} LLM enhancement: {llm_status}."
        state.workflow_log.append("Workflow: CrewAI role/task metadata initialized.")
        state.workflow_log.append(f"Workflow: Hugging Face LLM enhancement is {llm_status}.")
        for agent in self.agents:
            state = agent.run(state)
        state = self.report_writer.run(state, output_dir=output_dir, prefix=prefix)
        return state
