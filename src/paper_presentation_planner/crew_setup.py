"""CrewAI metadata construction.

This module builds CrewAI Agent/Task/Crew objects when the crewai package is
installed, documenting the role-based multi-agent architecture used by the
system. The execution pipeline also supports Hugging Face LLM enhancement with
a deterministic fallback for robust homework evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class CrewMetadata:
    available: bool
    status: str
    agents: List[Dict[str, str]]
    tasks: List[Dict[str, str]]
    crew_object: Any = None


AGENT_SPECS = [
    {
        "name": "Paper Loader Agent",
        "role": "Paper Loader",
        "goal": "Read a paper from txt, md, or pdf and prepare clean text.",
        "backstory": "A careful research assistant who prepares reliable input for later agents.",
    },
    {
        "name": "Paper Structure Agent",
        "role": "Paper Structure Analyst",
        "goal": "Detect title, authors, abstract, sections, and important keywords.",
        "backstory": "An academic editor who understands common research paper structure.",
    },
    {
        "name": "Problem and Motivation Agent",
        "role": "Research Problem Analyst",
        "goal": "Identify the research problem, motivation, and background.",
        "backstory": "A seminar mentor who explains why a paper matters.",
    },
    {
        "name": "Method Analysis Agent",
        "role": "Methodology Analyst",
        "goal": "Summarize the proposed method, model, algorithm, or system design.",
        "backstory": "A technical reviewer who focuses on the method section.",
    },
    {
        "name": "Contribution and Limitation Agent",
        "role": "Contribution and Limitation Reviewer",
        "goal": "Extract major contributions, experimental findings, and limitations.",
        "backstory": "A skeptical reviewer who checks both strengths and weaknesses.",
    },
    {
        "name": "Slide Planner Agent",
        "role": "Presentation Planner",
        "goal": "Design a clear slide-by-slide presentation outline.",
        "backstory": "A presentation coach who converts research content into teachable slides.",
    },
    {
        "name": "Speaker Notes Agent",
        "role": "Speaker Notes Writer",
        "goal": "Generate concise speaking notes for each planned slide.",
        "backstory": "A teaching assistant who helps students present papers clearly.",
    },
    {
        "name": "Q&A Preparation Agent",
        "role": "Q&A Coach",
        "goal": "Generate expected audience questions and suggested answers.",
        "backstory": "A seminar examiner who anticipates difficult questions.",
    },
    {
        "name": "Quality Review Agent",
        "role": "Final Quality Reviewer",
        "goal": "Check whether the final summary and presentation plan are complete and coherent.",
        "backstory": "A strict but helpful reviewer who checks assignment deliverables.",
    },
]

TASK_SPECS = [
    {"name": "load_paper", "description": "Load and clean the input paper text."},
    {"name": "parse_structure", "description": "Extract title, authors, abstract, sections, and keywords."},
    {"name": "analyze_problem", "description": "Explain the research problem and motivation."},
    {"name": "analyze_method", "description": "Explain the proposed method or approach."},
    {"name": "review_contributions", "description": "Find contributions, findings, and limitations."},
    {"name": "plan_slides", "description": "Create slide-by-slide presentation structure."},
    {"name": "write_notes", "description": "Write speaker notes for the slide plan."},
    {"name": "prepare_qa", "description": "Generate expected questions and answers."},
    {"name": "quality_review", "description": "Review final output quality."},
]


def build_crewai_metadata() -> CrewMetadata:
    try:
        from crewai import Agent, Crew, Process, Task

        agents = []
        for spec in AGENT_SPECS:
            agents.append(
                Agent(
                    role=spec["role"],
                    goal=spec["goal"],
                    backstory=spec["backstory"],
                    verbose=False,
                    allow_delegation=False,
                )
            )
        tasks = []
        for idx, spec in enumerate(TASK_SPECS):
            agent = agents[min(idx, len(agents) - 1)]
            tasks.append(
                Task(
                    description=spec["description"],
                    expected_output=f"Structured output for {spec['name']}.",
                    agent=agent,
                )
            )
        crew = Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=False)
        return CrewMetadata(
            available=True,
            status="CrewAI objects created successfully; local workflow supports Hugging Face LLM enhancement with fallback.",
            agents=AGENT_SPECS,
            tasks=TASK_SPECS,
            crew_object=crew,
        )
    except Exception as exc:
        return CrewMetadata(
            available=False,
            status=f"CrewAI package could not be initialized, local workflow used instead: {exc}",
            agents=AGENT_SPECS,
            tasks=TASK_SPECS,
            crew_object=None,
        )
