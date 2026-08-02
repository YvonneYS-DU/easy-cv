"""
Material / session / version / strategy store — filesystem persistence.

Directory layout:
.materials/
├── raw/              # Raw input, unchanged
├── extracted/         # AI-extracted structured materials (by domain)
├── refined/           # Final materials after human–AI refinement (by domain)
├── sessions/          # AI session memory
├── versions/          # Full resume version snapshots
├── rewrites/          # Block rewrite history
└── strategies/        # Application strategy memory (same facts, different framing)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from resume_agents.memory.models import (
    ApplicationStrategy,
    BlockRewriteRecord,
    ChatSession,
    FramingVariant,
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    ResumeVersion,
    SessionMessage,
)


class MaterialStore:
    """Persistent store for materials and extended memory."""

    def __init__(self, base_dir: str = ".materials"):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.extracted_dir = self.base_dir / "extracted"
        self.refined_dir = self.base_dir / "refined"
        self.sessions_dir = self.base_dir / "sessions"
        self.versions_dir = self.base_dir / "versions"
        self.rewrites_dir = self.base_dir / "rewrites"
        self.strategies_dir = self.base_dir / "strategies"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [
            self.raw_dir,
            self.extracted_dir,
            self.refined_dir,
            self.sessions_dir,
            self.versions_dir,
            self.rewrites_dir,
            self.strategies_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now().isoformat()

    # ── Raw materials ──────────────────────────────────

    def save_raw(self, raw_text: str, material_id: str) -> str:
        """Save raw input text; return file path."""
        filepath = self.raw_dir / f"{material_id}.json"
        data = {"id": material_id, "raw_text": raw_text}
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(filepath)

    def read_raw(self, material_id: str) -> Optional[str]:
        """Read raw input text."""
        filepath = self.raw_dir / f"{material_id}.json"
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")

    # ── Structured materials ───────────────────────────

    def _domain_dir(self, base: Path, domain: str) -> Path:
        d = base / domain if domain else base / "common"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_material(self, material: MaterialRecord) -> str:
        """Save structured material to the appropriate directory."""
        target_dir = self.refined_dir if material.status == MaterialStatus.REFINED else self.extracted_dir
        d = self._domain_dir(target_dir, material.domain)
        filepath = d / f"{material.id}.json"
        filepath.write_text(
            material.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return str(filepath)

    def load_material(self, material_id: str, domain: str = "") -> Optional[MaterialRecord]:
        """Load one material record."""
        search_dirs = [
            self._domain_dir(self.refined_dir, domain),
            self._domain_dir(self.extracted_dir, domain),
        ]
        if domain:
            search_dirs.append(self._domain_dir(self.refined_dir, ""))
            search_dirs.append(self._domain_dir(self.extracted_dir, ""))

        for d in search_dirs:
            filepath = d / f"{material_id}.json"
            if filepath.exists():
                return MaterialRecord.model_validate_json(
                    filepath.read_text(encoding="utf-8")
                )

        for base in [self.refined_dir, self.extracted_dir]:
            for filepath in base.rglob(f"{material_id}.json"):
                return MaterialRecord.model_validate_json(
                    filepath.read_text(encoding="utf-8")
                )

        return None

    def list_materials(
        self,
        domain: str = "",
        status: Optional[MaterialStatus] = None,
        material_type: Optional[MaterialType] = None,
        include_all_domains: bool = False,
    ) -> list[MaterialRecord]:
        """List material records."""
        results: list[MaterialRecord] = []
        seen: set[str] = set()

        def _collect_from(base: Path) -> None:
            if not base.exists():
                return
            paths = base.rglob("*.json") if include_all_domains or not domain else (
                self._domain_dir(base, domain).glob("*.json")
            )
            for f in paths:
                try:
                    record = MaterialRecord.model_validate_json(
                        f.read_text(encoding="utf-8")
                    )
                except Exception:
                    continue
                if record.id in seen:
                    continue
                if material_type and record.content.type != material_type:
                    continue
                if status and record.status != status:
                    continue
                if domain and not include_all_domains and record.domain and record.domain != domain:
                    continue
                seen.add(record.id)
                results.append(record)

        if status == MaterialStatus.REFINED or status is None:
            _collect_from(self.refined_dir)
        if status == MaterialStatus.EXTRACTED or status is None:
            _collect_from(self.extracted_dir)

        if not domain and not include_all_domains:
            # Backward compatible: always scan common
            pass

        return results

    def delete_material(self, material_id: str) -> bool:
        """Delete material (search and remove from all dirs)."""
        deleted = False
        for base in [self.raw_dir, self.extracted_dir, self.refined_dir]:
            for f in base.rglob(f"{material_id}.json"):
                f.unlink()
                deleted = True
        return deleted

    # ── Session memory ─────────────────────────────────

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def save_session(self, session: ChatSession) -> str:
        session.updated_at = self._now()
        filepath = self._session_path(session.id)
        filepath.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        return str(filepath)

    def load_session(self, session_id: str) -> Optional[ChatSession]:
        filepath = self._session_path(session_id)
        if not filepath.exists():
            return None
        return ChatSession.model_validate_json(filepath.read_text(encoding="utf-8"))

    def list_sessions(self, resume_id: str = "") -> list[ChatSession]:
        results: list[ChatSession] = []
        if not self.sessions_dir.exists():
            return results
        for f in sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                session = ChatSession.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if resume_id and session.resume_id != resume_id:
                continue
            results.append(session)
        return results

    def get_or_create_session(
        self,
        session_id: str = "",
        resume_id: str = "",
        domain: str = "",
        title: str = "",
    ) -> ChatSession:
        if session_id:
            existing = self.load_session(session_id)
            if existing:
                dirty = False
                if resume_id and not existing.resume_id:
                    existing.resume_id = resume_id
                    dirty = True
                if domain and existing.domain != domain:
                    existing.domain = domain
                    dirty = True
                if title and not existing.title:
                    existing.title = title
                    dirty = True
                if dirty:
                    self.save_session(existing)
                return existing

        if resume_id:
            matched = self.list_sessions(resume_id=resume_id)
            if matched:
                session = matched[0]
                if domain and session.domain != domain:
                    session.domain = domain
                    self.save_session(session)
                return session

        session = ChatSession(
            resume_id=resume_id,
            domain=domain,
            title=title or "AI 会话",
        )
        self.save_session(session)
        return session

    def append_session_messages(
        self,
        session_id: str,
        messages: list[SessionMessage],
    ) -> Optional[ChatSession]:
        session = self.load_session(session_id)
        if not session:
            return None
        session.messages.extend(messages)
        self.save_session(session)
        return session

    def update_session_message(
        self,
        session_id: str,
        message_id: str,
        **fields: object,
    ) -> Optional[ChatSession]:
        session = self.load_session(session_id)
        if not session:
            return None
        found = False
        for msg in session.messages:
            if msg.id != message_id:
                continue
            for key, value in fields.items():
                if hasattr(msg, key) and value is not None:
                    setattr(msg, key, value)
            found = True
            break
        if not found:
            return None
        self.save_session(session)
        return session

    def delete_session(self, session_id: str) -> bool:
        filepath = self._session_path(session_id)
        if not filepath.exists():
            return False
        filepath.unlink()
        return True

    # ── Resume versions ────────────────────────────────

    def _version_path(self, version_id: str) -> Path:
        return self.versions_dir / f"{version_id}.json"

    def save_resume_version(self, version: ResumeVersion) -> str:
        if not version.created_at:
            version.created_at = self._now()
        filepath = self._version_path(version.id)
        filepath.write_text(version.model_dump_json(indent=2), encoding="utf-8")
        return str(filepath)

    def load_resume_version(self, version_id: str) -> Optional[ResumeVersion]:
        filepath = self._version_path(version_id)
        if not filepath.exists():
            return None
        return ResumeVersion.model_validate_json(filepath.read_text(encoding="utf-8"))

    def list_resume_versions(
        self,
        resume_id: str = "",
        domain: str = "",
        limit: int = 50,
    ) -> list[ResumeVersion]:
        results: list[ResumeVersion] = []
        if not self.versions_dir.exists():
            return results
        for f in sorted(self.versions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                version = ResumeVersion.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if resume_id and version.resume_id != resume_id:
                continue
            if domain and version.domain and version.domain != domain:
                continue
            results.append(version)
            if len(results) >= limit:
                break
        return results

    def next_version_no(self, resume_id: str) -> int:
        versions = self.list_resume_versions(resume_id=resume_id, limit=200)
        if not versions:
            return 1
        return max(v.version_no for v in versions) + 1

    def create_resume_version(
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
        version = ResumeVersion(
            resume_id=resume_id,
            domain=domain,
            title=title,
            source=source,
            note=note,
            target_role=target_role,
            strategy_id=strategy_id,
            parent_version_id=parent_version_id,
            version_no=self.next_version_no(resume_id) if resume_id else 1,
            raw_markdown=raw_markdown,
            document_json=document_json or {},
            tags=tags or [],
        )
        self.save_resume_version(version)
        return version

    def delete_resume_version(self, version_id: str) -> bool:
        filepath = self._version_path(version_id)
        if not filepath.exists():
            return False
        filepath.unlink()
        return True

    # ── Block rewrite history ──────────────────────────

    def _rewrite_path(self, rewrite_id: str) -> Path:
        return self.rewrites_dir / f"{rewrite_id}.json"

    def save_block_rewrite(self, record: BlockRewriteRecord) -> str:
        record.updated_at = self._now()
        filepath = self._rewrite_path(record.id)
        filepath.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return str(filepath)

    def load_block_rewrite(self, rewrite_id: str) -> Optional[BlockRewriteRecord]:
        filepath = self._rewrite_path(rewrite_id)
        if not filepath.exists():
            return None
        return BlockRewriteRecord.model_validate_json(filepath.read_text(encoding="utf-8"))

    def list_block_rewrites(
        self,
        resume_id: str = "",
        block_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[BlockRewriteRecord]:
        results: list[BlockRewriteRecord] = []
        if not self.rewrites_dir.exists():
            return results
        for f in sorted(self.rewrites_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                record = BlockRewriteRecord.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if resume_id and record.resume_id != resume_id:
                continue
            if block_id and record.block_id != block_id:
                continue
            if status and record.status != status:
                continue
            results.append(record)
            if len(results) >= limit:
                break
        return results

    def update_block_rewrite(
        self,
        rewrite_id: str,
        **fields: object,
    ) -> Optional[BlockRewriteRecord]:
        record = self.load_block_rewrite(rewrite_id)
        if not record:
            return None
        for key, value in fields.items():
            if hasattr(record, key) and value is not None:
                setattr(record, key, value)
        self.save_block_rewrite(record)
        return record

    def delete_block_rewrite(self, rewrite_id: str) -> bool:
        filepath = self._rewrite_path(rewrite_id)
        if not filepath.exists():
            return False
        filepath.unlink()
        return True

    # ── Application strategy memory ────────────────────

    def _strategy_path(self, strategy_id: str) -> Path:
        return self.strategies_dir / f"{strategy_id}.json"

    def save_strategy(self, strategy: ApplicationStrategy) -> str:
        strategy.updated_at = self._now()
        filepath = self._strategy_path(strategy.id)
        filepath.write_text(strategy.model_dump_json(indent=2), encoding="utf-8")
        return str(filepath)

    def load_strategy(self, strategy_id: str) -> Optional[ApplicationStrategy]:
        filepath = self._strategy_path(strategy_id)
        if not filepath.exists():
            return None
        return ApplicationStrategy.model_validate_json(filepath.read_text(encoding="utf-8"))

    def list_strategies(self, domain: str = "", resume_id: str = "") -> list[ApplicationStrategy]:
        results: list[ApplicationStrategy] = []
        if not self.strategies_dir.exists():
            return results
        for f in sorted(self.strategies_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                strategy = ApplicationStrategy.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if domain and strategy.domain and strategy.domain != domain:
                continue
            if resume_id and resume_id not in strategy.related_resume_ids:
                continue
            results.append(strategy)
        return results

    def get_or_create_strategy(
        self,
        strategy_id: str = "",
        domain: str = "",
        target_role: str = "",
        name: str = "",
        resume_id: str = "",
    ) -> ApplicationStrategy:
        if strategy_id:
            existing = self.load_strategy(strategy_id)
            if existing:
                return existing

        # Reuse when domain + target_role match
        for s in self.list_strategies(domain=domain):
            if target_role and s.target_role == target_role:
                if resume_id and resume_id not in s.related_resume_ids:
                    s.related_resume_ids.append(resume_id)
                    self.save_strategy(s)
                return s
            if not target_role and domain and s.domain == domain and not s.target_role:
                if resume_id and resume_id not in s.related_resume_ids:
                    s.related_resume_ids.append(resume_id)
                    self.save_strategy(s)
                return s

        strategy = ApplicationStrategy(
            name=name or (f"{domain or '通用'} · {target_role}" if target_role else (domain or "写法分支")),
            domain=domain,
            target_role=target_role,
            related_resume_ids=[resume_id] if resume_id else [],
            why=(
                "源项目写法分支：同一真实经历按投递方向改具体写法；"
                "事实不变，强调点与措辞可变。"
            ),
            framing_rules=[
                "挂靠源经历/源项目，记录该方向下如何改、改成什么样",
                "事实不变，角度可变；禁止编造未发生的经历",
                "技术栈倾向保留完整，少删 stack",
                "接受区块建议后沉淀为新的写法分支，供下次复用",
            ],
        )
        self.save_strategy(strategy)
        return strategy

    def upsert_strategy(self, strategy: ApplicationStrategy) -> ApplicationStrategy:
        if not strategy.created_at:
            strategy.created_at = self._now()
        self.save_strategy(strategy)
        return strategy

    def add_strategy_variant(
        self,
        strategy_id: str,
        variant: FramingVariant,
    ) -> Optional[ApplicationStrategy]:
        strategy = self.load_strategy(strategy_id)
        if not strategy:
            return None
        strategy.variants.append(variant)
        self.save_strategy(strategy)
        return strategy

    def delete_strategy(self, strategy_id: str) -> bool:
        filepath = self._strategy_path(strategy_id)
        if not filepath.exists():
            return False
        filepath.unlink()
        return True
