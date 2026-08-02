"""
FastAPI routes — multi-agent resume API.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from resume_agents.api.schemas import (
    AddMaterialRequest,
    AddMaterialResponse,
    AddStrategyVariantRequest,
    BlockRewriteResponse,
    CreateSessionRequest,
    DomainsResponse,
    DomainInfo,
    GenerateFullRequest,
    GenerateFullResponse,
    GenerateSectionRequest,
    GenerateSectionResponse,
    JDMatchRequest,
    JDMatchResponse,
    ListBlockRewritesResponse,
    ListResumeVersionsResponse,
    ListSessionsResponse,
    ListStrategiesResponse,
    RefineMaterialRequest,
    RefineMaterialResponse,
    ResumeVersionResponse,
    RewriteBlockRequest,
    RewriteBlockResponse,
    SaveResumeVersionRequest,
    SessionResponse,
    StrategyResponse,
    UpdateBlockRewriteRequest,
    UpdateSuggestionRequest,
    UpsertStrategyRequest,
)
from resume_agents.memory.models import ApplicationStrategy, MaterialStatus, Resume
from resume_agents.orchestrator import ResumeOrchestrator

router = APIRouter(prefix="/api/v1", tags=["resume"])


def get_orchestrator() -> ResumeOrchestrator:
    """Return the global orchestrator instance."""
    from main import orchestrator as global_orch
    return global_orch


# ── Materials ────────────────────────────────────────

@router.post("/materials", response_model=AddMaterialResponse)
def add_material(req: AddMaterialRequest):
    """Add raw material (AI extract + follow-up questions)."""
    orch = get_orchestrator()
    material, questions = orch.add_material(req.raw_text, domain=req.domain)
    return AddMaterialResponse(material=material, ai_questions=questions)


@router.put("/materials/refine", response_model=RefineMaterialResponse)
def refine_material(req: RefineMaterialRequest):
    """Refine material via human–AI dialogue."""
    orch = get_orchestrator()
    try:
        material, questions, is_complete = orch.refine_material(
            req.material_id, req.user_response
        )
        return RefineMaterialResponse(
            material=material,
            ai_questions=questions,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/materials")
def list_materials(
    domain: str = "",
    status: Optional[str] = None,
    all_domains: bool = False,
):
    """List materials."""
    orch = get_orchestrator()
    mat_status = MaterialStatus(status) if status else None
    materials = orch.list_materials(
        domain=domain,
        status=mat_status,
        include_all_domains=all_domains,
    )
    return [m.model_dump(mode="json") for m in materials]


@router.get("/materials/{material_id}")
def get_material(material_id: str, domain: str = ""):
    """Get one material."""
    orch = get_orchestrator()
    m = orch.get_material(material_id, domain=domain)
    if not m:
        raise HTTPException(status_code=404, detail=f"素材不存在: {material_id}")
    return m.model_dump(mode="json")


@router.delete("/materials/{material_id}")
def delete_material(material_id: str, domain: str = ""):
    """Delete a material."""
    orch = get_orchestrator()
    ok = orch.delete_material(material_id, domain=domain)
    if not ok:
        raise HTTPException(status_code=404, detail=f"素材不存在: {material_id}")
    return {"ok": True, "id": material_id}


# ── Resume generation ────────────────────────────────

@router.post("/resume/section", response_model=GenerateSectionResponse)
def generate_section(req: GenerateSectionRequest):
    """Generate one resume section."""
    orch = get_orchestrator()
    content = orch.generate_section(
        domain=req.domain,
        section=req.section,
        material_ids=req.material_ids or None,
        jd_text=req.jd_text,
    )
    return GenerateSectionResponse(section_name=req.section, content=content)


@router.post("/resume/full", response_model=GenerateFullResponse)
def generate_full(req: GenerateFullRequest):
    """Generate a full resume in batch."""
    orch = get_orchestrator()
    resume = orch.generate_full(
        domain=req.domain,
        material_ids=req.material_ids or None,
        jd_text=req.jd_text,
        resume_id=req.resume_id,
        title=req.title,
        save_version=req.save_version,
        strategy_id=req.strategy_id,
        target_role=req.target_role,
    )
    version = None
    if req.resume_id and req.save_version:
        versions = orch.list_resume_versions(resume_id=req.resume_id, limit=1)
        version = versions[0] if versions else None
    return GenerateFullResponse(resume=resume, version=version)


@router.post("/resume/block-rewrite", response_model=RewriteBlockResponse)
def rewrite_block(req: RewriteBlockRequest):
    """AI-rewrite a selected block; persist session and rewrite history."""
    if not req.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text 不能为空")
    if not req.instruction.strip():
        raise HTTPException(status_code=400, detail="instruction 不能为空")
    orch = get_orchestrator()
    result = orch.rewrite_block(
        selected_text=req.selected_text,
        instruction=req.instruction,
        chip=req.chip,
        domain=req.domain,
        session_id=req.session_id,
        resume_id=req.resume_id,
        block_id=req.block_id,
        use_history=req.use_history,
        strategy_id=req.strategy_id,
        target_role=req.target_role,
        resume_markdown=req.resume_markdown,
        mine_materials=req.mine_materials,
        material_ids=req.material_ids or None,
    )
    session = result["session"]
    user_msg = result["user_message"]
    ai_msg = result["ai_message"]
    rewrite = result.get("rewrite")
    return RewriteBlockResponse(
        original_text=req.selected_text,
        suggested_text=result["suggested_text"],
        block_id=req.block_id,
        chip=req.chip,
        session_id=session.id,
        user_message_id=user_msg.id,
        ai_message_id=ai_msg.id,
        rewrite_id=rewrite.id if rewrite else "",
        ai_note=result.get("ai_note") or ai_msg.content,
        session=session,
        rewrite=rewrite,
        strategy=result.get("strategy"),
        forgotten_experiences=result.get("forgotten_experiences") or [],
    )


# ── Session memory ───────────────────────────────────

@router.post("/sessions", response_model=SessionResponse)
def create_or_get_session(req: CreateSessionRequest):
    """Create or get a session (reuse by resume_id)."""
    orch = get_orchestrator()
    session = orch.get_or_create_session(
        session_id=req.session_id,
        resume_id=req.resume_id,
        domain=req.domain,
        title=req.title,
    )
    return SessionResponse(session=session)


@router.get("/sessions", response_model=ListSessionsResponse)
def list_sessions(resume_id: str = ""):
    """List sessions."""
    orch = get_orchestrator()
    sessions = orch.list_sessions(resume_id=resume_id)
    return ListSessionsResponse(sessions=sessions)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    """Get one session."""
    orch = get_orchestrator()
    session = orch.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return SessionResponse(session=session)


@router.patch("/sessions/{session_id}/messages/{message_id}", response_model=SessionResponse)
def update_session_suggestion(session_id: str, message_id: str, req: UpdateSuggestionRequest):
    """Update suggestion status (applied / ignored / pending)."""
    status = req.status.strip().lower()
    if status not in {"applied", "ignored", "pending"}:
        raise HTTPException(status_code=400, detail="status 必须是 applied|ignored|pending")
    orch = get_orchestrator()
    session = orch.update_session_suggestion(session_id, message_id, status)
    if not session:
        raise HTTPException(status_code=404, detail="会话或消息不存在")
    return SessionResponse(session=session)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session."""
    orch = get_orchestrator()
    ok = orch.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
    return {"ok": True, "id": session_id}


# ── Resume versions ──────────────────────────────────

@router.post("/resume/versions", response_model=ResumeVersionResponse)
def save_resume_version(req: SaveResumeVersionRequest):
    """Save a full resume version snapshot."""
    if not req.resume_id.strip():
        raise HTTPException(status_code=400, detail="resume_id 不能为空")
    orch = get_orchestrator()
    version = orch.save_resume_version(
        resume_id=req.resume_id,
        raw_markdown=req.raw_markdown,
        document_json=req.document_json,
        domain=req.domain,
        title=req.title,
        source=req.source,
        note=req.note,
        target_role=req.target_role,
        strategy_id=req.strategy_id,
        parent_version_id=req.parent_version_id,
        tags=req.tags,
    )
    return ResumeVersionResponse(version=version)


@router.get("/resume/versions", response_model=ListResumeVersionsResponse)
def list_resume_versions(resume_id: str = "", domain: str = "", limit: int = 50):
    """List resume versions."""
    orch = get_orchestrator()
    versions = orch.list_resume_versions(
        resume_id=resume_id,
        domain=domain,
        limit=max(1, min(limit, 200)),
    )
    return ListResumeVersionsResponse(versions=versions)


@router.get("/resume/versions/{version_id}", response_model=ResumeVersionResponse)
def get_resume_version(version_id: str):
    """Get one resume version."""
    orch = get_orchestrator()
    version = orch.get_resume_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"版本不存在: {version_id}")
    return ResumeVersionResponse(version=version)


@router.delete("/resume/versions/{version_id}")
def delete_resume_version(version_id: str):
    """Delete a resume version."""
    orch = get_orchestrator()
    ok = orch.delete_resume_version(version_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"版本不存在: {version_id}")
    return {"ok": True, "id": version_id}


# ── Block rewrite history ────────────────────────────

@router.get("/rewrites", response_model=ListBlockRewritesResponse)
def list_block_rewrites(
    resume_id: str = "",
    block_id: str = "",
    status: str = "",
    limit: int = 100,
):
    """List block rewrites."""
    orch = get_orchestrator()
    rewrites = orch.list_block_rewrites(
        resume_id=resume_id,
        block_id=block_id,
        status=status,
        limit=max(1, min(limit, 300)),
    )
    return ListBlockRewritesResponse(rewrites=rewrites)


@router.get("/rewrites/{rewrite_id}", response_model=BlockRewriteResponse)
def get_block_rewrite(rewrite_id: str):
    """Get one rewrite record."""
    orch = get_orchestrator()
    rewrite = orch.get_block_rewrite(rewrite_id)
    if not rewrite:
        raise HTTPException(status_code=404, detail=f"改写记录不存在: {rewrite_id}")
    return BlockRewriteResponse(rewrite=rewrite)


@router.patch("/rewrites/{rewrite_id}", response_model=BlockRewriteResponse)
def update_block_rewrite(rewrite_id: str, req: UpdateBlockRewriteRequest):
    """Update rewrite status; on applied, promote into strategy variants."""
    status = req.status.strip().lower()
    if status not in {"applied", "ignored", "pending"}:
        raise HTTPException(status_code=400, detail="status 必须是 applied|ignored|pending")
    orch = get_orchestrator()
    rewrite = orch.update_block_rewrite_status(
        rewrite_id,
        status=status,
        session_id=req.session_id,
    )
    if not rewrite:
        raise HTTPException(status_code=404, detail=f"改写记录不存在: {rewrite_id}")
    return BlockRewriteResponse(rewrite=rewrite)


# ── Application strategies ───────────────────────────

@router.post("/strategies", response_model=StrategyResponse)
def upsert_strategy(req: UpsertStrategyRequest):
    """Create or update an application strategy (same facts, different framing)."""
    orch = get_orchestrator()
    if req.id:
        existing = orch.get_strategy(req.id)
        if existing:
            data = existing.model_dump()
            patch = req.model_dump(exclude_unset=False)
            for key in (
                "name", "domain", "target_role", "company_type", "core_message",
                "emphasis", "de_emphasis", "framing_rules", "why", "notes",
                "related_resume_ids", "related_material_ids",
            ):
                val = patch.get(key)
                if val not in (None, "", []):
                    data[key] = val
            if req.resume_id and req.resume_id not in data.get("related_resume_ids", []):
                data.setdefault("related_resume_ids", []).append(req.resume_id)
            strategy = ApplicationStrategy.model_validate(data)
            strategy = orch.upsert_strategy(strategy)
            return StrategyResponse(strategy=strategy)

    strategy = orch.get_or_create_strategy(
        strategy_id=req.id,
        domain=req.domain,
        target_role=req.target_role,
        name=req.name,
        resume_id=req.resume_id,
    )
    # Merge user-provided fields
    if req.name:
        strategy.name = req.name
    if req.core_message:
        strategy.core_message = req.core_message
    if req.company_type:
        strategy.company_type = req.company_type
    if req.emphasis:
        strategy.emphasis = req.emphasis
    if req.de_emphasis:
        strategy.de_emphasis = req.de_emphasis
    if req.framing_rules:
        strategy.framing_rules = req.framing_rules
    if req.why:
        strategy.why = req.why
    if req.notes:
        strategy.notes = req.notes
    if req.related_material_ids:
        strategy.related_material_ids = list(dict.fromkeys(
            strategy.related_material_ids + req.related_material_ids
        ))
    strategy = orch.upsert_strategy(strategy)
    return StrategyResponse(strategy=strategy)


@router.get("/strategies", response_model=ListStrategiesResponse)
def list_strategies(domain: str = "", resume_id: str = ""):
    """List strategies."""
    orch = get_orchestrator()
    strategies = orch.list_strategies(domain=domain, resume_id=resume_id)
    return ListStrategiesResponse(strategies=strategies)


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: str):
    """Get one strategy."""
    orch = get_orchestrator()
    strategy = orch.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")
    return StrategyResponse(strategy=strategy)


@router.post("/strategies/{strategy_id}/variants", response_model=StrategyResponse)
def add_strategy_variant(strategy_id: str, req: AddStrategyVariantRequest):
    """Append a framing/phrasing variant to a strategy."""
    if not req.phrasing.strip():
        raise HTTPException(status_code=400, detail="phrasing 不能为空")
    orch = get_orchestrator()
    strategy = orch.add_strategy_variant(
        strategy_id=strategy_id,
        direction=req.direction,
        angle=req.angle,
        phrasing=req.phrasing,
        why=req.why,
        source_block_id=req.source_block_id,
        source_resume_id=req.source_resume_id,
    )
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")
    return StrategyResponse(strategy=strategy)


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: str):
    """Delete a strategy."""
    orch = get_orchestrator()
    ok = orch.delete_strategy(strategy_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")
    return {"ok": True, "id": strategy_id}


# ── JD matching ──────────────────────────────────────

@router.post("/resume/match", response_model=JDMatchResponse)
def match_jd(req: JDMatchRequest):
    """JD match analysis + strategy-aware rewrite + forgotten-experience mining."""
    orch = get_orchestrator()
    resume = Resume(
        domain=req.domain,
        raw_markdown=req.resume_markdown,
    )
    match_result = orch.match_jd(
        resume,
        req.jd_text,
        domain=req.domain,
        resume_id=req.resume_id,
        strategy_id=req.strategy_id,
        target_role=req.target_role,
        material_ids=req.material_ids or None,
        mine_forgotten=req.mine_forgotten,
    )
    suggested = orch.rewrite_for_jd(
        resume,
        req.jd_text,
        domain=req.domain,
        resume_id=req.resume_id,
        strategy_id=req.strategy_id,
        target_role=req.target_role,
        match_result=match_result,
        save_version=req.save_version and bool(req.resume_id),
        title=req.title,
    )
    strategy = None
    if req.strategy_id:
        strategy = orch.get_strategy(req.strategy_id)
    if strategy is None:
        strategies = orch.list_strategies(domain=req.domain, resume_id=req.resume_id)
        strategy = strategies[0] if strategies else None

    version = None
    if req.resume_id and req.save_version:
        versions = orch.list_resume_versions(resume_id=req.resume_id, limit=1)
        version = versions[0] if versions else None

    return JDMatchResponse(
        match_result=match_result,
        suggested_resume=suggested,
        strategy=strategy,
        version=version,
    )


# ── Domains ──────────────────────────────────────────

@router.get("/domains", response_model=DomainsResponse)
def list_domains():
    """List all supported domains."""
    orch = get_orchestrator()
    domains_data = orch.list_domains()
    from resume_agents.domain.profiles import get_domain

    domain_infos = []
    for d in domains_data:
        profile = get_domain(d["key"])
        domain_infos.append(DomainInfo(
            key=d["key"],
            label=d["label"],
            core_keywords=profile.get("core_keywords", []),
        ))

    return DomainsResponse(domains=domain_infos)
