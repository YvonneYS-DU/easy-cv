"""Tests for version memory, rewrite history, strategies, forgotten-experience mining."""

from __future__ import annotations

import tempfile
import unittest

from resume_agents.memory.models import (
    ApplicationStrategy,
    FramingVariant,
    MaterialContent,
    MaterialRecord,
    MaterialStatus,
    MaterialType,
    Resume,
)
from resume_agents.memory.store import MaterialStore
from resume_agents.orchestrator import ResumeOrchestrator


class ExtendedMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = MaterialStore(base_dir=self._tmpdir.name)
        self.orch = ResumeOrchestrator(store=self.store, mock=True)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_resume_version_create_list_restore_fields(self) -> None:
        v1 = self.orch.save_resume_version(
            resume_id="r1",
            raw_markdown="# SUMMARY\n\nhello",
            domain="ai_engineer",
            title="初版",
            source="manual",
            target_role="AI Engineer",
        )
        v2 = self.orch.save_resume_version(
            resume_id="r1",
            raw_markdown="# SUMMARY\n\nhello v2",
            domain="ai_engineer",
            title="JD 改写",
            source="jd_rewrite",
            target_role="AI Engineer",
            parent_version_id=v1.id,
        )
        self.assertEqual(v1.version_no, 1)
        self.assertEqual(v2.version_no, 2)
        listed = self.orch.list_resume_versions(resume_id="r1")
        self.assertEqual(len(listed), 2)
        loaded = self.orch.get_resume_version(v2.id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.parent_version_id, v1.id)
        self.assertIn("hello v2", loaded.raw_markdown)

    def test_block_rewrite_history_and_strategy_variant_on_apply(self) -> None:
        result = self.orch.rewrite_block(
            selected_text="Built RAG system for ops",
            instruction="按后端工程化角度改写",
            chip="Work · RAG",
            domain="ai_engineer",
            resume_id="r-backend",
            block_id="work-1",
            target_role="Backend Engineer",
        )
        rewrite = result["rewrite"]
        self.assertEqual(rewrite.status, "pending")
        self.assertTrue(rewrite.id)

        listed = self.orch.list_block_rewrites(resume_id="r-backend")
        self.assertEqual(len(listed), 1)

        updated = self.orch.update_block_rewrite_status(rewrite.id, "applied")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.status, "applied")

        strategies = self.orch.list_strategies(domain="ai_engineer")
        self.assertTrue(strategies)
        # After applied, a framing variant should be persisted
        has_variant = any(s.variants for s in strategies)
        self.assertTrue(has_variant)

    def test_strategy_same_fact_different_framing(self) -> None:
        s = self.orch.get_or_create_strategy(
            domain="ai_engineer",
            target_role="AI Engineer",
            name="AI 向",
            resume_id="r1",
        )
        s.core_message = "把工程落地能力讲成 AI 产品化能力"
        s.emphasis = ["RAG", "evaluation", "latency"]
        s.why = "同一项目对 AI 岗强调检索与评测，对后端岗强调稳定性"
        self.orch.upsert_strategy(s)

        self.orch.add_strategy_variant(
            strategy_id=s.id,
            direction="AI Engineer",
            angle="RAG quality",
            phrasing="Improved retrieval precision from 0.61 to 0.84 via hybrid search.",
            why="AI 岗看模型效果",
            source_resume_id="r1",
        )
        self.orch.add_strategy_variant(
            strategy_id=s.id,
            direction="Backend Engineer",
            angle="reliability",
            phrasing="Cut p95 latency 35% and shipped canary rollout for retrieval service.",
            why="后端岗看稳定性与上线",
            source_resume_id="r1",
        )
        loaded = self.orch.get_strategy(s.id)
        assert loaded is not None
        self.assertEqual(len(loaded.variants), 2)
        self.assertTrue(
            ("一样话" in loaded.why) or ("取景" in loaded.why) or ("强调" in loaded.why)
        )

    def test_jd_match_mines_forgotten_materials(self) -> None:
        # Material exists in library but not on the resume
        mat = MaterialRecord(
            id="mat-forgotten",
            domain="backend",
            status=MaterialStatus.REFINED,
            content=MaterialContent(
                id="c1",
                type=MaterialType.PROJECT,
                summary="Built Kafka event pipeline for fraud detection",
                tags=["kafka", "fraud", "pipeline"],
                fields={"impact": "reduced false positives 18%"},
            ),
        )
        self.store.save_material(mat)

        resume = Resume(
            domain="ai_engineer",
            raw_markdown="# SUMMARY\n\nAI engineer focused on RAG agents.\n",
        )
        match = self.orch.match_jd(
            resume,
            jd_text="Looking for backend/AI hybrid with Kafka streaming and fraud detection experience.",
            domain="ai_engineer",
            resume_id="r-jd",
            target_role="AI Platform",
            mine_forgotten=True,
        )
        self.assertTrue(match.forgotten_experiences)
        ids = [h.material_id for h in match.forgotten_experiences]
        self.assertIn("mat-forgotten", ids)
        self.assertTrue(match.strategy_notes)
        self.assertTrue(match.probing_questions)

        rewritten = self.orch.rewrite_for_jd(
            resume,
            jd_text="Looking for backend/AI hybrid with Kafka streaming and fraud detection experience.",
            domain="ai_engineer",
            resume_id="r-jd",
            target_role="AI Platform",
            match_result=match,
            save_version=True,
        )
        self.assertIn("Kafka", rewritten.raw_markdown + match.gap_analysis + str(match.forgotten_experiences))
        versions = self.orch.list_resume_versions(resume_id="r-jd")
        self.assertTrue(any(v.source == "jd_rewrite" for v in versions))

    def test_generate_full_saves_version(self) -> None:
        resume = self.orch.generate_full(
            domain="ai_engineer",
            resume_id="r-gen",
            title="生成稿",
            save_version=True,
        )
        self.assertTrue(resume.raw_markdown)
        versions = self.orch.list_resume_versions(resume_id="r-gen")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].source, "generate_full")

    def test_material_preserves_tech_stack_preference(self) -> None:
        material, _ = self.orch.add_material(
            "Built fraud pipeline with Kafka, Redis, FastAPI and Docker",
            domain="backend",
        )
        self.assertTrue(material.preferences.preserve_tech_stack)
        stack = material.content.fields.get("tech_stack") or material.content.fields.get("skills") or []
        stack_l = [str(s).lower() for s in stack]
        self.assertTrue(any("kafka" in s for s in stack_l))
        self.assertTrue(any("fastapi" in s or "docker" in s for s in stack_l))

    def test_block_rewrite_merges_material_hints(self) -> None:
        mat = MaterialRecord(
            id="mat-kafka",
            domain="backend",
            status=MaterialStatus.REFINED,
            content=MaterialContent(
                id="c-k",
                type=MaterialType.PROJECT,
                summary="Kafka fraud detection pipeline",
                tags=["kafka", "fraud"],
                fields={"tech_stack": ["Kafka", "Redis", "FastAPI"]},
            ),
        )
        self.store.save_material(mat)
        result = self.orch.rewrite_block(
            selected_text="Worked on messaging systems",
            instruction="补上素材库里相关但漏写的点",
            chip="Work · Platform",
            domain="ai_engineer",
            resume_id="r-merge",
            block_id="work-1",
            target_role="Backend Engineer",
            resume_markdown="# SUMMARY\nAI engineer\n",
            mine_materials=True,
        )
        self.assertTrue(result["suggested_text"])
        self.assertTrue(result.get("forgotten_experiences"))
        self.assertIn("mat-kafka", [h.material_id for h in result["forgotten_experiences"]])
        self.assertIn("Incorporated related experience", result["suggested_text"])


if __name__ == "__main__":
    unittest.main()
