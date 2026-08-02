"""
Resume material data models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class MaterialType(str, Enum):
    """Material type."""
    WORK_EXPERIENCE = "work_experience"
    PROJECT = "project"
    EDUCATION = "education"
    SKILL = "skill"
    CERTIFICATE = "certificate"
    OTHER = "other"


class MaterialStatus(str, Enum):
    """Material status."""
    EXTRACTED = "extracted"   # Initial AI extraction
    REFINED = "refined"       # Final version after human–AI refinement


class MaterialPreferences(BaseModel):
    """
    Material-level preferences (apply directly; no accept/ignore).
    preserve_tech_stack=True: prefer keeping the full stack on extract/refine.
    """
    preserve_tech_stack: bool = True
    notes: str = "技术栈倾向保留完整，少删工具/框架/语言"


class MaterialContent(BaseModel):
    """
    Structured material content — minimal core + flexible extensions.

    - Fixed fields are only id / type / summary / tags for cross-domain indexing.
    - fields is a free-form dict decided by the LLM from material type/domain;
      different projects, domains, and phrasings use different content ids.
    - Prefer writing tech stack into fields.tech_stack / fields.skills (lists); keep stack.
    """
    id: str = Field(default_factory=_new_id)
    type: MaterialType = MaterialType.OTHER
    summary: str = ""                     # One-line summary for indexing/search
    tags: list[str] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Human–AI chat message."""
    role: str                           # "ai" | "user"
    msg: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class MaterialRecord(BaseModel):
    """One material record (fact store: edit in place, no suggestion approval)."""
    id: str = Field(default_factory=_new_id)
    raw_ref: str = ""                    # Points back to the original file under raw/
    domain: str = ""                     # Domain
    version: int = 1
    status: MaterialStatus = MaterialStatus.EXTRACTED
    content: MaterialContent = Field(default_factory=MaterialContent)
    preferences: MaterialPreferences = Field(default_factory=MaterialPreferences)
    chat_log: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResumeSection(BaseModel):
    """One resume section."""
    name: str                            # summary / work_experience / projects / skills / education
    content: str                         # Markdown content


class Resume(BaseModel):
    """Full resume."""
    domain: str = ""
    sections: list[ResumeSection] = Field(default_factory=list)
    raw_markdown: str = ""               # Full markdown
    version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class JDRequirements(BaseModel):
    """Structured requirements parsed from a JD."""
    keywords: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    years_of_experience: str = ""
    education_level: str = ""


class ForgottenExperienceHint(BaseModel):
    """Experience mined from materials that the current resume may omit."""
    material_id: str = ""
    summary: str = ""
    why_relevant: str = ""
    suggested_angle: str = ""
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class JDMatchResult(BaseModel):
    """JD match result."""
    jd_text: str = ""
    jd_requirements: JDRequirements = Field(default_factory=JDRequirements)
    match_score: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    section_suggestions: dict[str, str] = Field(default_factory=dict)
    gap_analysis: str = ""
    strategy_notes: str = ""
    forgotten_experiences: list[ForgottenExperienceHint] = Field(default_factory=list)
    probing_questions: list[str] = Field(default_factory=list)


class SessionMessage(BaseModel):
    """One session message (survives requests/restarts)."""
    id: str = Field(default_factory=_new_id)
    role: str = "user"  # user | ai | system
    content: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    block_id: str = ""
    chip: str = ""
    instruction: str = ""
    original_text: str = ""
    suggested_text: str = ""
    suggestion_status: str = ""  # pending | applied | ignored | ""
    meta: dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """AI session memory bound to a resume; persists chat and rewrite suggestions."""
    id: str = Field(default_factory=_new_id)
    resume_id: str = ""
    domain: str = ""
    title: str = ""
    messages: list[SessionMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResumeVersion(BaseModel):
    """Full resume version snapshot."""
    id: str = Field(default_factory=_new_id)
    resume_id: str = ""
    domain: str = ""
    title: str = ""
    source: str = ""  # manual | generate_full | jd_rewrite | block_apply | import | snapshot
    note: str = ""
    target_role: str = ""
    strategy_id: str = ""
    parent_version_id: str = ""
    version_no: int = 1
    raw_markdown: str = ""
    document_json: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BlockRewriteRecord(BaseModel):
    """Block rewrite history (separate from sessions for cross-resume search)."""
    id: str = Field(default_factory=_new_id)
    resume_id: str = ""
    session_id: str = ""
    message_id: str = ""
    block_id: str = ""
    chip: str = ""
    domain: str = ""
    instruction: str = ""
    original_text: str = ""
    suggested_text: str = ""
    status: str = "pending"  # pending | applied | ignored
    strategy_id: str = ""
    target_role: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FramingVariant(BaseModel):
    """
    Phrasing branch for one source experience under one target direction.
    Same facts → multiple direction-specific phrasings (not full resume copies).
    """
    id: str = Field(default_factory=_new_id)
    direction: str = ""  # e.g. ai_engineer / backend / pm
    angle: str = ""      # Emphasis, e.g. RAG / engineering / business impact
    phrasing: str = ""   # Concrete phrasing for this direction
    why: str = ""        # Why rewrite this way
    source_material_id: str = ""  # Linked source material/project
    source_block_id: str = ""
    source_resume_id: str = ""


class ApplicationStrategy(BaseModel):
    """
    Set of phrasing branches: how source experience is rewritten per direction.
    Reused by block AI rewrite; does not replace resume version snapshots.
    """
    id: str = Field(default_factory=_new_id)
    name: str = ""
    domain: str = ""
    target_role: str = ""
    company_type: str = ""
    core_message: str = ""
    emphasis: list[str] = Field(default_factory=list)
    de_emphasis: list[str] = Field(default_factory=list)
    framing_rules: list[str] = Field(default_factory=list)
    why: str = ""
    variants: list[FramingVariant] = Field(default_factory=list)
    related_resume_ids: list[str] = Field(default_factory=list)
    related_material_ids: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
