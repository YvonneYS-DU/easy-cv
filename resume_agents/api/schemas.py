"""
API request/response schemas.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from resume_agents.memory.models import (
    ApplicationStrategy,
    BlockRewriteRecord,
    ChatSession,
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    Resume,
    JDMatchResult,
    ResumeVersion,
)


# ── Materials ─────────────────────────────────────────

class AddMaterialRequest(BaseModel):
    """Add raw material (chat capture / batch import)."""
    raw_text: str
    domain: str = ""


class AddMaterialResponse(BaseModel):
    material: MaterialRecord
    ai_questions: list[str] = Field(default_factory=list)  # AI follow-up questions


class RefineMaterialRequest(BaseModel):
    """User answers AI questions to refine material."""
    material_id: str
    user_response: str


class RefineMaterialResponse(BaseModel):
    material: MaterialRecord
    ai_questions: list[str] = Field(default_factory=list)  # May ask further questions


class ListMaterialsRequest(BaseModel):
    domain: str = ""
    status: Optional[MaterialStatus] = None
    material_type: Optional[MaterialType] = None


# ── Resume generation ────────────────────────────────

class GenerateSectionRequest(BaseModel):
    """Generate one section at a time."""
    domain: str
    section: str                     # summary / work_experience / projects / skills / education
    material_ids: list[str] = Field(default_factory=list)
    jd_text: str = ""


class GenerateSectionResponse(BaseModel):
    section_name: str
    content: str


class GenerateFullRequest(BaseModel):
    """Generate a full resume in batch."""
    domain: str
    material_ids: list[str] = Field(default_factory=list)
    jd_text: str = ""


class GenerateFullResponse(BaseModel):
    resume: Resume


# ── JD matching ──────────────────────────────────────

class JDMatchRequest(BaseModel):
    resume_markdown: str
    jd_text: str
    domain: str = ""
    resume_id: str = ""
    strategy_id: str = ""
    target_role: str = ""
    material_ids: list[str] = Field(default_factory=list)
    mine_forgotten: bool = True
    save_version: bool = True
    title: str = ""


class JDMatchResponse(BaseModel):
    match_result: JDMatchResult
    suggested_resume: Optional[Resume] = None
    strategy: Optional[ApplicationStrategy] = None
    version: Optional[ResumeVersion] = None


# ── Domains ──────────────────────────────────────────

class DomainInfo(BaseModel):
    key: str
    label: str
    core_keywords: list[str] = Field(default_factory=list)


class DomainsResponse(BaseModel):
    domains: list[DomainInfo]


# ── Block AI rewrite ──────────────────────────────────

class RewriteBlockRequest(BaseModel):
    selected_text: str
    instruction: str
    chip: str = ""
    domain: str = ""
    block_id: str = ""
    session_id: str = ""
    resume_id: str = ""
    use_history: bool = True
    strategy_id: str = ""
    target_role: str = ""
    resume_markdown: str = ""
    mine_materials: bool = True
    material_ids: list[str] = Field(default_factory=list)


class RewriteBlockResponse(BaseModel):
    original_text: str
    suggested_text: str
    block_id: str = ""
    chip: str = ""
    session_id: str = ""
    user_message_id: str = ""
    ai_message_id: str = ""
    rewrite_id: str = ""
    ai_note: str = ""
    session: Optional[ChatSession] = None
    rewrite: Optional[BlockRewriteRecord] = None
    strategy: Optional[ApplicationStrategy] = None
    forgotten_experiences: list = Field(default_factory=list)


# ── Session memory ───────────────────────────────────

class CreateSessionRequest(BaseModel):
    resume_id: str = ""
    domain: str = ""
    title: str = ""
    session_id: str = ""


class SessionResponse(BaseModel):
    session: ChatSession


class ListSessionsResponse(BaseModel):
    sessions: list[ChatSession] = Field(default_factory=list)


class UpdateSuggestionRequest(BaseModel):
    status: str  # applied | ignored | pending


# ── Resume versions ──────────────────────────────────

class SaveResumeVersionRequest(BaseModel):
    resume_id: str
    raw_markdown: str = ""
    document_json: dict[str, Any] = Field(default_factory=dict)
    domain: str = ""
    title: str = ""
    source: str = "snapshot"
    note: str = ""
    target_role: str = ""
    strategy_id: str = ""
    parent_version_id: str = ""
    tags: list[str] = Field(default_factory=list)


class ResumeVersionResponse(BaseModel):
    version: ResumeVersion


class ListResumeVersionsResponse(BaseModel):
    versions: list[ResumeVersion] = Field(default_factory=list)


# ── Block rewrite history ────────────────────────────

class ListBlockRewritesResponse(BaseModel):
    rewrites: list[BlockRewriteRecord] = Field(default_factory=list)


class BlockRewriteResponse(BaseModel):
    rewrite: BlockRewriteRecord


class UpdateBlockRewriteRequest(BaseModel):
    status: str  # applied | ignored | pending
    session_id: str = ""


# ── Application strategies ───────────────────────────

class UpsertStrategyRequest(BaseModel):
    id: str = ""
    name: str = ""
    domain: str = ""
    target_role: str = ""
    company_type: str = ""
    core_message: str = ""
    emphasis: list[str] = Field(default_factory=list)
    de_emphasis: list[str] = Field(default_factory=list)
    framing_rules: list[str] = Field(default_factory=list)
    why: str = ""
    notes: str = ""
    related_resume_ids: list[str] = Field(default_factory=list)
    related_material_ids: list[str] = Field(default_factory=list)
    resume_id: str = ""


class StrategyResponse(BaseModel):
    strategy: ApplicationStrategy


class ListStrategiesResponse(BaseModel):
    strategies: list[ApplicationStrategy] = Field(default_factory=list)


class AddStrategyVariantRequest(BaseModel):
    direction: str = ""
    angle: str = ""
    phrasing: str = ""
    why: str = ""
    source_block_id: str = ""
    source_resume_id: str = ""
