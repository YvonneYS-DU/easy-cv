"""Session memory persistence and orchestrator integration tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resume_agents.memory.models import SessionMessage
from resume_agents.memory.store import MaterialStore
from resume_agents.orchestrator import ResumeOrchestrator


class SessionMemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = MaterialStore(base_dir=self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_create_save_and_reload_session(self) -> None:
        session = self.store.get_or_create_session(
            resume_id="resume-1",
            domain="ai_engineer",
            title="测试会话",
        )
        self.assertTrue(session.id)
        self.assertEqual(session.resume_id, "resume-1")

        path = Path(self.store.sessions_dir) / f"{session.id}.json"
        self.assertTrue(path.exists())

        loaded = self.store.load_session(session.id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.id, session.id)
        self.assertEqual(loaded.title, "测试会话")

    def test_reuse_session_by_resume_id(self) -> None:
        first = self.store.get_or_create_session(resume_id="resume-x", domain="ai")
        second = self.store.get_or_create_session(resume_id="resume-x", domain="ai")
        self.assertEqual(first.id, second.id)

    def test_append_and_update_messages(self) -> None:
        session = self.store.get_or_create_session(resume_id="r2")
        user = SessionMessage(role="user", content="精简这段", block_id="b1")
        ai = SessionMessage(
            role="ai",
            content="已生成修改建议",
            block_id="b1",
            suggested_text="精简后的内容",
            suggestion_status="pending",
        )
        updated = self.store.append_session_messages(session.id, [user, ai])
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(len(updated.messages), 2)

        after = self.store.update_session_message(
            session.id,
            ai.id,
            suggestion_status="applied",
        )
        self.assertIsNotNone(after)
        assert after is not None
        self.assertEqual(after.messages[1].suggestion_status, "applied")

        reloaded = self.store.load_session(session.id)
        assert reloaded is not None
        self.assertEqual(reloaded.messages[1].suggestion_status, "applied")

    def test_list_and_delete_session(self) -> None:
        a = self.store.get_or_create_session(resume_id="ra")
        b = self.store.get_or_create_session(resume_id="rb")
        all_sessions = self.store.list_sessions()
        self.assertGreaterEqual(len(all_sessions), 2)

        only_a = self.store.list_sessions(resume_id="ra")
        self.assertEqual(len(only_a), 1)
        self.assertEqual(only_a[0].id, a.id)

        self.assertTrue(self.store.delete_session(b.id))
        self.assertIsNone(self.store.load_session(b.id))


class SessionMemoryOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = MaterialStore(base_dir=self._tmpdir.name)
        self.orch = ResumeOrchestrator(store=self.store, mock=True)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_rewrite_block_persists_session_memory(self) -> None:
        result = self.orch.rewrite_block(
            selected_text="Built AI agent with LangChain",
            instruction="量化成果",
            chip="Work · Demo",
            domain="ai_engineer",
            resume_id="resume-demo",
            block_id="work-1",
            use_history=True,
        )
        self.assertIn("suggested_text", result)
        session = result["session"]
        self.assertTrue(session.id)
        self.assertEqual(session.resume_id, "resume-demo")
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[0].content, "量化成果")
        self.assertEqual(session.messages[1].role, "ai")
        self.assertEqual(session.messages[1].suggestion_status, "pending")
        self.assertTrue(session.messages[1].suggested_text)

        disk = self.store.load_session(session.id)
        self.assertIsNotNone(disk)
        assert disk is not None
        self.assertEqual(len(disk.messages), 2)

        second = self.orch.rewrite_block(
            selected_text=result["suggested_text"],
            instruction="再精简一点",
            chip="Work · Demo",
            domain="ai_engineer",
            session_id=session.id,
            resume_id="resume-demo",
            block_id="work-1",
        )
        self.assertEqual(second["session"].id, session.id)
        self.assertEqual(len(second["session"].messages), 4)

        updated = self.orch.update_session_suggestion(
            session.id,
            second["ai_message"].id,
            "applied",
        )
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.messages[-1].suggestion_status, "applied")


if __name__ == "__main__":
    unittest.main()
