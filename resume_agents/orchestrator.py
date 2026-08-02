"""
Orchestrator — wires agents and manages global flow and memory.

Flow:
1. Materials: extract → refine dialogue loop
2. Resume generation: section-by-section or full
3. JD match: strategy-aware + forgotten-experience mining → rewrite
4. Block rewrite: block-level AI edit + rewrite history
5. Persist version / strategy memory
"""

from __future__ import annotations

import re
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from resume_agents.agents.material_extractor import MaterialExtractorAgent
from resume_agents.agents.material_refiner import MaterialRefinerAgent
from resume_agents.agents.resume_generator import ResumeGeneratorAgent
from resume_agents.agents.jd_matcher import JDMatcherAgent
from resume_agents.agents.block_editor import BlockEditorAgent
from resume_agents.memory.models import (
    ApplicationStrategy,
    BlockRewriteRecord,
    ChatSession,
    ForgottenExperienceHint,
    FramingVariant,
    MaterialRecord,
    MaterialStatus,
    Resume,
    JDMatchResult,
    ResumeVersion,
    SessionMessage,
)
from resume_agents.memory.store import MaterialStore
from resume_agents.domain.profiles import get_domain, list_domains


class ResumeOrchestrator:
    """Multi-agent resume orchestrator."""

    def __init__(
        self,
        model: Any = None,
        store: Optional[MaterialStore] = None,
        agents: Any = None,
        mock: bool = False,
    ):
        if model is None and not mock:
            model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

        self.model = model
        self.mock = mock
        self.store = store or MaterialStore()

        self.extractor = MaterialExtractorAgent(model, agents=agents) if not mock else None
        self.refiner = MaterialRefinerAgent(model, agents=agents) if not mock else None
        self.generator = ResumeGeneratorAgent(model, agents=agents) if not mock else None
        self.matcher = JDMatcherAgent(model, agents=agents) if not mock else None
        self.block_editor = BlockEditorAgent(model, agents=agents) if not mock else None

    # ── Materials ─────────────────────────────────────

    def add_material(self, raw_text: str, domain: str = "") -> tuple[MaterialRecord, list[str]]:
        if self.mock:
            from resume_agents.mock_service import mock_add_material

            return mock_add_material(self.store, raw_text, domain)

        material = self.extractor.extract(raw_text, domain=domain)
        material.raw_ref = self.store.save_raw(raw_text, material.id)
        self.store.save_material(material)

        questions = self.refiner.generate_initial_questions(material)
        self.store.save_material(material)

        return material, questions

    def refine_material(self, material_id: str, user_response: str) -> tuple[MaterialRecord, list[str], bool]:
        material = self.store.load_material(material_id)
        if not material:
            raise ValueError(f"素材不存在: {material_id}")

        if self.mock:
            from resume_agents.mock_service import mock_refine_material

            material, questions, is_complete = mock_refine_material(material, user_response)
            self.store.save_material(material)
            return material, questions, is_complete

        material, questions, is_complete = self.refiner.refine(material, user_response)
        self.store.save_material(material)
        return material, questions, is_complete

    def list_materials(
        self,
        domain: str = "",
        status: Optional[MaterialStatus] = None,
        include_all_domains: bool = False,
    ) -> list[MaterialRecord]:
        return self.store.list_materials(
            domain=domain,
            status=status,
            include_all_domains=include_all_domains,
        )

    def get_material(self, material_id: str, domain: str = "") -> Optional[MaterialRecord]:
        return self.store.load_material(material_id, domain=domain)

    def delete_material(self, material_id: str, domain: str = "") -> bool:
        _ = domain
        return self.store.delete_material(material_id)

    # ── Sessions ──────────────────────────────────────

    def get_or_create_session(
        self,
        session_id: str = "",
        resume_id: str = "",
        domain: str = "",
        title: str = "",
    ) -> ChatSession:
        return self.store.get_or_create_session(
            session_id=session_id,
            resume_id=resume_id,
            domain=domain,
            title=title,
        )

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self.store.load_session(session_id)

    def list_sessions(self, resume_id: str = "") -> list[ChatSession]:
        return self.store.list_sessions(resume_id=resume_id)

    def delete_session(self, session_id: str) -> bool:
        return self.store.delete_session(session_id)

    def update_session_suggestion(
        self,
        session_id: str,
        message_id: str,
        status: str,
    ) -> Optional[ChatSession]:
        session = self.store.update_session_message(
            session_id,
            message_id,
            suggestion_status=status,
        )
        # Sync block-rewrite history status
        for rec in self.store.list_block_rewrites(limit=200):
            if rec.message_id == message_id or (
                rec.session_id == session_id and rec.id == message_id
            ):
                self.store.update_block_rewrite(rec.id, status=status)
        return session

    # ── Version memory ────────────────────────────────

    def save_resume_version(
        self,
        resume_id: str,
        raw_markdown: str = "",
        document_json: Optional[dict] = None,
        domain: str = "",
        title: str = "",
        source: str = "snapshot",
        note: str = "",
        target_role: str = "",
        strategy_id: str = "",
        parent_version_id: str = "",
        tags: Optional[list[str]] = None,
    ) -> ResumeVersion:
        return self.store.create_resume_version(
            resume_id=resume_id,
            raw_markdown=raw_markdown,
            document_json=document_json,
            domain=domain,
            title=title,
            source=source,
            note=note,
            target_role=target_role,
            strategy_id=strategy_id,
            parent_version_id=parent_version_id,
            tags=tags,
        )

    def list_resume_versions(
        self,
        resume_id: str = "",
        domain: str = "",
        limit: int = 50,
    ) -> list[ResumeVersion]:
        return self.store.list_resume_versions(
            resume_id=resume_id,
            domain=domain,
            limit=limit,
        )

    def get_resume_version(self, version_id: str) -> Optional[ResumeVersion]:
        return self.store.load_resume_version(version_id)

    def delete_resume_version(self, version_id: str) -> bool:
        return self.store.delete_resume_version(version_id)

    # ── Block rewrite history ─────────────────────────

    def list_block_rewrites(
        self,
        resume_id: str = "",
        block_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[BlockRewriteRecord]:
        return self.store.list_block_rewrites(
            resume_id=resume_id,
            block_id=block_id,
            status=status,
            limit=limit,
        )

    def get_block_rewrite(self, rewrite_id: str) -> Optional[BlockRewriteRecord]:
        return self.store.load_block_rewrite(rewrite_id)

    def update_block_rewrite_status(
        self,
        rewrite_id: str,
        status: str,
        session_id: str = "",
    ) -> Optional[BlockRewriteRecord]:
        record = self.store.update_block_rewrite(rewrite_id, status=status)
        if record and (session_id or record.session_id) and record.message_id:
            self.store.update_session_message(
                session_id or record.session_id,
                record.message_id,
                suggestion_status=status,
            )
        # On apply, promote rewrite into a strategy framing variant
        if record and status == "applied":
            self._capture_framing_from_rewrite(record)
        return record

    # ── Application strategies ────────────────────────

    def get_or_create_strategy(
        self,
        strategy_id: str = "",
        domain: str = "",
        target_role: str = "",
        name: str = "",
        resume_id: str = "",
    ) -> ApplicationStrategy:
        return self.store.get_or_create_strategy(
            strategy_id=strategy_id,
            domain=domain,
            target_role=target_role,
            name=name,
            resume_id=resume_id,
        )

    def list_strategies(self, domain: str = "", resume_id: str = "") -> list[ApplicationStrategy]:
        return self.store.list_strategies(domain=domain, resume_id=resume_id)

    def get_strategy(self, strategy_id: str) -> Optional[ApplicationStrategy]:
        return self.store.load_strategy(strategy_id)

    def upsert_strategy(self, strategy: ApplicationStrategy) -> ApplicationStrategy:
        return self.store.upsert_strategy(strategy)

    def delete_strategy(self, strategy_id: str) -> bool:
        return self.store.delete_strategy(strategy_id)

    def add_strategy_variant(
        self,
        strategy_id: str,
        direction: str,
        angle: str,
        phrasing: str,
        why: str = "",
        source_block_id: str = "",
        source_resume_id: str = "",
    ) -> Optional[ApplicationStrategy]:
        variant = FramingVariant(
            direction=direction,
            angle=angle,
            phrasing=phrasing,
            why=why,
            source_block_id=source_block_id,
            source_resume_id=source_resume_id,
        )
        return self.store.add_strategy_variant(strategy_id, variant)

    # ── Block rewrite ─────────────────────────────────

    def rewrite_block(
        self,
        selected_text: str,
        instruction: str,
        chip: str = "",
        domain: str = "",
        session_id: str = "",
        resume_id: str = "",
        block_id: str = "",
        use_history: bool = True,
        strategy_id: str = "",
        target_role: str = "",
        resume_markdown: str = "",
        mine_materials: bool = True,
        material_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Selected block → AI suggestion (framing branches + fillable material points)
        → user accepts/ignores. Experience mining is folded into this suggestion path.
        """
        session = self.store.get_or_create_session(
            session_id=session_id,
            resume_id=resume_id,
            domain=domain,
            title=chip or "区块改写",
        )

        strategy = self.store.get_or_create_strategy(
            strategy_id=strategy_id,
            domain=domain,
            target_role=target_role,
            resume_id=resume_id,
        )

        history_text = ""
        if use_history and session.messages:
            recent = session.messages[-12:]
            history_text = "\n".join(
                f"[{m.role}] {m.content}"
                + (f"\n  原文: {m.original_text}" if m.original_text else "")
                + (f"\n  建议: {m.suggested_text}" if m.suggested_text else "")
                for m in recent
            )

        writing_branches = self._format_writing_branches(strategy, target_role or domain)
        material_hints = ""
        forgotten: list[ForgottenExperienceHint] = []
        if mine_materials:
            materials = (
                self._load_materials(material_ids, domain)
                if material_ids
                else self.store.list_materials(include_all_domains=True)
            )
            context_md = resume_markdown or selected_text
            forgotten = self._heuristic_forgotten(
                resume_markdown=context_md,
                jd_text=f"{instruction}\n{target_role}\n{domain}\n{selected_text}",
                materials=materials,
                existing=[],
            )
            # Rank items more relevant to the current block first
            forgotten = self._rank_hints_for_block(forgotten, selected_text, chip)
            material_hints = self._format_material_hints(forgotten)

        if self.mock:
            from resume_agents.mock_service import mock_rewrite_block

            suggested = mock_rewrite_block(
                selected_text,
                instruction,
                chip=chip,
                material_hints=material_hints,
                target_role=target_role,
            )
        else:
            suggested = self.block_editor.rewrite(
                selected_text=selected_text,
                instruction=instruction,
                chip=chip,
                domain=domain,
                history=history_text,
                writing_branches=writing_branches,
                material_hints=material_hints,
                target_role=target_role,
            )

        ai_note = "已生成修改建议"
        if forgotten:
            ai_note = f"已生成修改建议（并入 {len(forgotten)} 条可补素材点）"

        user_msg = SessionMessage(
            role="user",
            content=instruction,
            block_id=block_id,
            chip=chip,
            instruction=instruction,
            original_text=selected_text,
            meta={
                "strategy_id": strategy.id,
                "target_role": target_role,
                "kind": "block_rewrite",
            },
        )
        ai_msg = SessionMessage(
            role="ai",
            content=ai_note,
            block_id=block_id,
            chip=chip,
            instruction=instruction,
            original_text=selected_text,
            suggested_text=suggested,
            suggestion_status="pending",
            meta={
                "strategy_id": strategy.id,
                "target_role": target_role,
                "kind": "block_rewrite",
                "forgotten_material_ids": [h.material_id for h in forgotten if h.material_id],
            },
        )
        self.store.append_session_messages(session.id, [user_msg, ai_msg])
        session = self.store.load_session(session.id) or session

        rewrite = BlockRewriteRecord(
            resume_id=resume_id,
            session_id=session.id,
            message_id=ai_msg.id,
            block_id=block_id,
            chip=chip,
            domain=domain,
            instruction=instruction,
            original_text=selected_text,
            suggested_text=suggested,
            status="pending",
            strategy_id=strategy.id,
            target_role=target_role,
        )
        self.store.save_block_rewrite(rewrite)

        return {
            "suggested_text": suggested,
            "session": session,
            "user_message": user_msg,
            "ai_message": ai_msg,
            "rewrite": rewrite,
            "strategy": strategy,
            "forgotten_experiences": forgotten,
            "ai_note": ai_note,
        }

    # ── Generation ────────────────────────────────────

    def generate_section(
        self,
        domain: str,
        section: str,
        material_ids: Optional[list[str]] = None,
        jd_text: str = "",
    ) -> str:
        materials = self._load_materials(material_ids, domain)
        if self.mock:
            from resume_agents.mock_service import mock_generate_section

            return mock_generate_section(domain, section, materials, jd_text)
        return self.generator.generate_section(
            domain=domain,
            section=section,
            materials=materials,
            jd_text=jd_text,
        )

    def generate_full(
        self,
        domain: str,
        material_ids: Optional[list[str]] = None,
        jd_text: str = "",
        resume_id: str = "",
        title: str = "",
        save_version: bool = True,
        strategy_id: str = "",
        target_role: str = "",
    ) -> Resume:
        materials = self._load_materials(material_ids, domain)
        if self.mock:
            from resume_agents.mock_service import mock_generate_full

            resume = mock_generate_full(domain, materials, jd_text)
        else:
            resume = self.generator.generate_full(
                domain=domain,
                materials=materials,
                jd_text=jd_text,
            )

        if save_version and resume_id:
            self.save_resume_version(
                resume_id=resume_id,
                raw_markdown=resume.raw_markdown,
                domain=domain,
                title=title or "生成完整简历",
                source="generate_full",
                note="由素材生成",
                strategy_id=strategy_id,
                target_role=target_role,
            )
        return resume

    # ── JD matching (strategy + mining) ────────────────

    def match_jd(
        self,
        resume: Resume,
        jd_text: str,
        domain: str = "",
        resume_id: str = "",
        strategy_id: str = "",
        target_role: str = "",
        material_ids: Optional[list[str]] = None,
        mine_forgotten: bool = True,
    ) -> JDMatchResult:
        strategy = self.store.get_or_create_strategy(
            strategy_id=strategy_id,
            domain=domain,
            target_role=target_role,
            resume_id=resume_id,
        )

        materials: list[MaterialRecord] = []
        if mine_forgotten:
            if material_ids:
                materials = self._load_materials(material_ids, domain)
            else:
                # Pull materials across domains so other projects are not forgotten
                materials = self.store.list_materials(include_all_domains=True)
                if domain:
                    # Prefer current domain
                    materials = sorted(
                        materials,
                        key=lambda m: 0 if m.domain == domain else 1,
                    )

        rewrite_variants_context = self._build_rewrite_variants_context(
            resume_id=resume_id,
            strategy=strategy,
        )

        if self.mock:
            from resume_agents.mock_service import mock_match_jd

            result = mock_match_jd(
                resume.raw_markdown,
                jd_text,
                domain,
                materials=materials,
                strategy=strategy,
            )
        else:
            result = self.matcher.match_and_analyze(
                resume_markdown=resume.raw_markdown,
                jd_text=jd_text,
                domain=domain,
                strategy=strategy,
                materials=materials,
                rewrite_variants_context=rewrite_variants_context,
            )

        # Extra deterministic mining so materials always surface when present
        if mine_forgotten and materials:
            heuristic = self._heuristic_forgotten(
                resume_markdown=resume.raw_markdown,
                jd_text=jd_text,
                materials=materials,
                existing=result.forgotten_experiences,
            )
            if heuristic:
                # Merge and dedupe
                seen = {h.material_id for h in result.forgotten_experiences if h.material_id}
                for h in heuristic:
                    if h.material_id and h.material_id in seen:
                        continue
                    result.forgotten_experiences.append(h)
                    if h.material_id:
                        seen.add(h.material_id)

        if not result.strategy_notes and strategy:
            result.strategy_notes = (
                f"沿用策略「{strategy.name}」：事实不变，按本 JD 调整强调点。"
                f" 当前强调: {', '.join(strategy.emphasis) or '待从 JD 提炼'}。"
            )

        # Write missing keywords back into strategy.emphasis (light learning)
        if result.missing_keywords:
            merged = list(dict.fromkeys(strategy.emphasis + result.missing_keywords[:8]))
            strategy.emphasis = merged[:16]
            if resume_id and resume_id not in strategy.related_resume_ids:
                strategy.related_resume_ids.append(resume_id)
            if not strategy.target_role and target_role:
                strategy.target_role = target_role
            self.store.save_strategy(strategy)

        return result

    def rewrite_for_jd(
        self,
        resume: Resume,
        jd_text: str,
        domain: str = "",
        resume_id: str = "",
        strategy_id: str = "",
        target_role: str = "",
        match_result: Optional[JDMatchResult] = None,
        save_version: bool = True,
        title: str = "",
    ) -> Resume:
        strategy = self.store.get_or_create_strategy(
            strategy_id=strategy_id,
            domain=domain,
            target_role=target_role,
            resume_id=resume_id,
        )
        if match_result is None:
            match_result = self.match_jd(
                resume,
                jd_text,
                domain=domain,
                resume_id=resume_id,
                strategy_id=strategy.id,
                target_role=target_role,
            )

        if self.mock:
            from resume_agents.mock_service import mock_rewrite_for_jd

            rewritten = mock_rewrite_for_jd(resume, match_result)
        else:
            rewritten = self.matcher.rewrite_for_jd(resume, match_result, strategy=strategy)

        if save_version and resume_id:
            self.save_resume_version(
                resume_id=resume_id,
                raw_markdown=rewritten.raw_markdown,
                domain=domain,
                title=title or "JD 改写稿",
                source="jd_rewrite",
                note=(match_result.strategy_notes or match_result.gap_analysis)[:240],
                strategy_id=strategy.id,
                target_role=target_role,
                tags=match_result.matched_keywords[:8],
            )
        return rewritten

    def full_pipeline(
        self,
        domain: str,
        material_ids: Optional[list[str]] = None,
        jd_text: str = "",
        resume_id: str = "",
    ) -> dict:
        resume = self.generate_full(
            domain,
            material_ids,
            jd_text,
            resume_id=resume_id,
        )
        result = {"resume": resume, "match": None, "rewritten": None}

        if jd_text:
            match = self.match_jd(resume, jd_text, domain, resume_id=resume_id)
            result["match"] = match
            result["rewritten"] = self.rewrite_for_jd(
                resume,
                jd_text,
                domain,
                resume_id=resume_id,
                match_result=match,
            )

        return result

    def get_domain_info(self, domain: str) -> dict:
        return get_domain(domain)

    def list_domains(self) -> list[dict]:
        return list_domains()

    # ── helpers ───────────────────────────────────────

    def _load_materials(
        self,
        material_ids: Optional[list[str]],
        domain: str,
    ) -> list[MaterialRecord]:
        if material_ids:
            materials = []
            for mid in material_ids:
                m = self.store.load_material(mid, domain)
                if m:
                    materials.append(m)
            return materials

        refined = self.store.list_materials(
            domain=domain, status=MaterialStatus.REFINED
        )
        if refined:
            return refined
        return self.store.list_materials(domain=domain)

    def _build_rewrite_variants_context(
        self,
        resume_id: str = "",
        strategy: Optional[ApplicationStrategy] = None,
    ) -> str:
        parts: list[str] = []
        if strategy and strategy.variants:
            parts.append("策略 variants:")
            for v in strategy.variants[-8:]:
                parts.append(f"- [{v.direction}] {v.angle}: {v.phrasing} ({v.why})")

        rewrites = self.store.list_block_rewrites(resume_id=resume_id, status="applied", limit=12)
        if rewrites:
            parts.append("已应用区块改写:")
            for r in rewrites:
                parts.append(
                    f"- [{r.chip or r.block_id}] {r.instruction[:40]} → {r.suggested_text[:80]}"
                )
        return "\n".join(parts) if parts else ""

    def _capture_framing_from_rewrite(self, record: BlockRewriteRecord) -> None:
        """After accepting a suggestion, persist it as a directional phrasing branch."""
        if not record.suggested_text.strip():
            return
        strategy = self.store.get_or_create_strategy(
            strategy_id=record.strategy_id,
            domain=record.domain,
            target_role=record.target_role,
            resume_id=record.resume_id,
        )
        why = (
            f"用户在「{record.chip or record.block_id}」接受了改写："
            f"{record.instruction[:80] or '按方向调整表述'}"
        )
        variant = FramingVariant(
            direction=record.target_role or record.domain or "general",
            angle=record.instruction[:60] or (record.chip or "reframe"),
            phrasing=record.suggested_text[:400],
            why=why,
            source_block_id=record.block_id,
            source_resume_id=record.resume_id,
        )
        self.store.add_strategy_variant(strategy.id, variant)

    def _format_writing_branches(
        self,
        strategy: Optional[ApplicationStrategy],
        direction: str = "",
    ) -> str:
        if not strategy:
            return ""
        lines = [
            f"分支集: {strategy.name}",
            f"方向: {strategy.target_role or strategy.domain or direction}",
            f"强调: {', '.join(strategy.emphasis) or '（未设）'}",
            f"规则: {'; '.join(strategy.framing_rules[:4])}",
            f"why: {strategy.why}",
        ]
        variants = strategy.variants[-10:]
        if direction:
            preferred = [v for v in variants if direction.lower() in (v.direction or "").lower()]
            others = [v for v in variants if v not in preferred]
            variants = (preferred + others)[-10:]
        if variants:
            lines.append("已有写法分支:")
            for v in variants:
                lines.append(
                    f"- [{v.direction}] {v.angle}: {v.phrasing[:200]}"
                    + (f" （{v.why}）" if v.why else "")
                )
        return "\n".join(lines)

    def _format_material_hints(self, hints: list[ForgottenExperienceHint]) -> str:
        if not hints:
            return ""
        lines = []
        for h in hints[:5]:
            lines.append(
                f"- material_id={h.material_id} | {h.summary}\n"
                f"  为何相关: {h.why_relevant}\n"
                f"  建议角度: {h.suggested_angle}\n"
                f"  证据: {', '.join(h.evidence[:6])}"
            )
        return "\n".join(lines)

    def _rank_hints_for_block(
        self,
        hints: list[ForgottenExperienceHint],
        selected_text: str,
        chip: str = "",
    ) -> list[ForgottenExperienceHint]:
        ctx = f"{chip}\n{selected_text}".lower()

        def score(h: ForgottenExperienceHint) -> float:
            s = h.confidence
            blob = f"{h.summary} {' '.join(h.evidence)}".lower()
            overlap = sum(1 for w in re.findall(r"[a-z\u4e00-\u9fff]{3,}", blob) if w in ctx)
            # Slightly down-rank unrelated items but keep them for gap-filling
            return s + 0.05 * overlap

        return sorted(hints, key=score, reverse=True)

    def _heuristic_forgotten(
        self,
        resume_markdown: str,
        jd_text: str,
        materials: list[MaterialRecord],
        existing: list[ForgottenExperienceHint],
    ) -> list[ForgottenExperienceHint]:
        resume_l = (resume_markdown or "").lower()
        jd_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", (jd_text or "").lower()))
        stop = {
            "and", "the", "with", "for", "you", "our", "will", "have", "from",
            "this", "that", "经验", "负责", "参与", "项目", "工作",
        }
        jd_kw = {t for t in jd_tokens if t not in stop and len(t) > 1}
        existing_ids = {h.material_id for h in existing if h.material_id}
        hints: list[ForgottenExperienceHint] = []

        for m in materials:
            if m.id in existing_ids:
                continue
            blob = " ".join(
                [
                    m.content.summary or "",
                    " ".join(m.content.tags or []),
                    " ".join(str(v) for v in (m.content.fields or {}).values()),
                ]
            ).strip()
            if not blob:
                continue
            blob_l = blob.lower()
            # Skip if resume already clearly contains this summary
            summary_key = (m.content.summary or "")[:24].lower()
            if summary_key and summary_key in resume_l:
                continue

            hit = [k for k in jd_kw if k in blob_l]
            # Treat as potentially forgotten if material keywords are absent from the resume
            material_tokens = set(re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", blob_l))
            novel = [t for t in material_tokens if t not in resume_l and t not in stop]
            if not hit and len(novel) < 2:
                continue

            conf = min(0.95, 0.35 + 0.08 * len(hit) + 0.03 * min(len(novel), 8))
            angle = (
                f"用该经历覆盖 JD 关键词: {', '.join(hit[:5])}"
                if hit
                else f"补充简历未体现的细节: {', '.join(novel[:5])}"
            )
            hints.append(
                ForgottenExperienceHint(
                    material_id=m.id,
                    summary=m.content.summary or blob[:80],
                    why_relevant=(
                        f"素材库有此经历，但当前简历未充分体现。"
                        + (f" 与 JD 重合: {', '.join(hit[:6])}。" if hit else "")
                    ),
                    suggested_angle=angle,
                    evidence=hit[:6] or novel[:6],
                    confidence=round(conf, 2),
                )
            )

        hints.sort(key=lambda h: h.confidence, reverse=True)
        return hints[:8]
