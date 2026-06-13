from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models import Signal, InterestProfile, GridPlan, RenderDocument
from ..retrieval.feeds import Candidate
from ..editorial.summarize import SummarizedStory


@dataclass
class IssueContext:
    user_id: str
    issue_id: str
    theme_id: str
    output_lang: str
    work_dir: Path

    signals: list[Signal] = field(default_factory=list)
    profile: InterestProfile | None = None
    candidates: list[Candidate] = field(default_factory=list)
    ranked: list[Candidate] = field(default_factory=list)
    stories: list[SummarizedStory] = field(default_factory=list)
    grid_plan: GridPlan | None = None
    render_document: RenderDocument | None = None
    pdf_path: Path | None = None
