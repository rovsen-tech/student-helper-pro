"""/api/progress/skill-gaps və /api/progress/error-analysis testləri.

TEST_REAL_MONGO_URL verilərsə REAL MongoDB-də (hər test üçün ayrıca, sonda silinən baza), əks halda mongomock-da işləyir.
"""
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_quiz_progress import _install_stubs, _FakeChat  # noqa: E402


class SkillGapEndpoints(unittest.TestCase):
    REAL_MONGO = os.environ.get("TEST_REAL_MONGO_URL")

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "test_db")
        _install_stubs()
        import server
        cls.server = server
        cls.TestClient = TestClient

    def setUp(self):
        self.server.make_chat = lambda *a, **k: _FakeChat()
        self.server.init_storage = lambda *a, **k: "k"
        if self.REAL_MONGO:
            from motor.motor_asyncio import AsyncIOMotorClient
            name = f"t_sg_{uuid.uuid4().hex[:10]}"
            mc = AsyncIOMotorClient(self.REAL_MONGO, serverSelectionTimeoutMS=3000)
            self.server.db = mc[name]
        else:
            from mongomock_motor import AsyncMongoMockClient
            self.server.db = AsyncMongoMockClient()["sg"]
        self.client = self.TestClient(self.server.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        if self.REAL_MONGO:
            self.addCleanup(lambda: self.client.portal.call(mc.drop_database, name))

    def _run(self, coro):
        async def _await():
            return await coro
        return self.client.portal.call(_await)

    def _student(self, name):
        r = self.client.post("/api/students", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["id"]

    def _answer(self, sid, question, correct, topic="Adi kəsrlər", subject="Riyaziyyat", quiz="q1"):
        pm = self.server.progress_manager
        self._run(self.server.db.quiz_answers.insert_one({
            "student_id": sid, "quiz_id": quiz, "question_id": uuid.uuid4().hex,
            "question_key": pm.question_key(question), "question": question, "subject": subject,
            "topic": topic, "correct": correct, "day": "2026-10-18",
            "created_at": f"2026-10-18T10:00:{uuid.uuid4().int % 60:02d}"}))

    def _get(self, path, sid):
        return self.client.get(path, headers={"X-Student-Id": sid})

    def test_unknown_student_404(self):
        for p in ("/api/progress/skill-gaps", "/api/progress/error-analysis"):
            self.assertEqual(self._get(p, "yoxdur-123").status_code, 404, p)

    def test_empty_student(self):
        sid = self._student("Boş")
        self.assertEqual(self._get("/api/progress/skill-gaps", sid).json(), {"skill_gaps": []})
        self.assertEqual(self._get("/api/progress/error-analysis", sid).json(), {"top_errors": []})

    def test_gaps_and_errors(self):
        sid = self._student("Aysel")
        other = self._student("Başqa")
        self._answer(sid, "3/4 kəsrində surət hansıdır?", False)
        self._answer(sid, "3/4 kəsrində surət hansıdır?", False, quiz="q2")
        self._answer(sid, "1/2 ilə hansı kəsr bərabərdir?", True)
        self._answer(sid, "25% nədir?", False, topic="Faiz")
        self._answer(other, "Başqa şagirdin sualı", False)
        before = self._run(self.server.db.quiz_answers.count_documents({}))

        gaps = self._get("/api/progress/skill-gaps", sid).json()["skill_gaps"]
        self.assertEqual([(g["subject"], g["topic"]) for g in gaps],
                         [("Riyaziyyat", "Faiz"), ("Riyaziyyat", "Adi kəsrlər")])  # weakest first
        faiz, kesr = gaps
        self.assertEqual((faiz["wrong_count"], faiz["correct_count"], faiz["accuracy_pct"]), (1, 0, 0))
        # compute_mastery counts only the first answer per question → 1 wrong, 1 correct
        self.assertEqual((kesr["wrong_count"], kesr["correct_count"], kesr["accuracy_pct"]), (1, 1, 50))
        self.assertTrue(kesr["common_mistakes"] and kesr["key_concepts"] and kesr["mastery_level"])

        errs = self._get("/api/progress/error-analysis", sid).json()["top_errors"]
        self.assertEqual(errs[0]["question"], "3/4 kəsrində surət hansıdır?")
        self.assertEqual(errs[0]["wrong_count"], 2)
        self.assertEqual(len(errs), 2)
        self.assertNotIn("Başqa şagirdin sualı", [e["question"] for e in errs])  # student isolation
        self.assertTrue(all(e["hint"] for e in errs))
        # read-only: no DB writes
        self.assertEqual(self._run(self.server.db.quiz_answers.count_documents({})), before)

    def test_error_analysis_top10(self):
        sid = self._student("Çox")
        for i in range(12):
            self._answer(sid, f"Sual {i}", False)
        errs = self._get("/api/progress/error-analysis", sid).json()["top_errors"]
        self.assertEqual(len(errs), 10)
