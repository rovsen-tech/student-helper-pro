import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import curriculum  # noqa: E402
from tests.test_quiz_progress import _install_stubs, _FakeChat  # noqa: E402


class CurriculumData(unittest.TestCase):
    def test_math_topics_and_no_cyrillic(self):
        topics = ["Natural ədədlər", "Adi kəsrlər", "Onluq kəsrlər", "Faiz", "Həndəsi fiqurlar",
                  "Ölçü vahidləri", "Sadə tənliklər"]
        for t in topics:
            self.assertIsNotNone(curriculum.get_topic_info("Riyaziyyat", t), t)
        self.assertIsNone(re.search("[\u0400-\u04FF]", json.dumps(curriculum.CURRICULUM, ensure_ascii=False)))
        self.assertIsNone(curriculum.get_topic_info("Riyaziyyat", "Yoxdur"))


class Endpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mongomock_motor import AsyncMongoMockClient
        from fastapi.testclient import TestClient
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "test_db")
        _install_stubs()
        import server
        cls.server = server
        server.make_chat = lambda *a, **k: _FakeChat()
        server.init_storage = lambda *a, **k: "k"
        server.db = AsyncMongoMockClient()["cp"]
        cls.c = TestClient(server.app)

    def test_curriculum_endpoint(self):
        self.assertEqual(self.c.get("/api/curriculum/Riyaziyyat/Faiz").status_code, 200)
        self.assertEqual(self.c.get("/api/curriculum/Riyaziyyat/Yox").status_code, 404)

    def test_review_questions_empty(self):
        r = self.c.get("/api/progress/review-questions")
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())

    def test_pin_flow(self):
        self.server.db = self.server.db.client["pin"]
        c = self.c
        self.assertFalse(c.get("/api/parent/pin-status").json()["has_pin"])
        self.assertEqual(c.post("/api/parent/pin", json={"pin": "12a"}).status_code, 422)
        self.assertTrue(c.post("/api/parent/pin", json={"pin": "1234"}).json()["ok"])
        st = c.get("/api/parent/pin-status").json()
        self.assertEqual(set(st), {"has_pin"})
        self.assertTrue(c.post("/api/parent/verify", json={"pin": "1234"}).json()["ok"])
        self.assertFalse(c.post("/api/parent/verify", json={"pin": "0000"}).json()["ok"])
        self.assertEqual(c.post("/api/parent/pin", json={"pin": "5678"}).status_code, 403)
        self.assertEqual(c.post("/api/parent/pin", json={"pin": "5678", "old_pin": "1111"}).status_code, 403)
        r = c.post("/api/parent/pin", json={"pin": "5678", "old_pin": "1234"})
        self.assertNotIn("hash", r.text)
        self.assertTrue(c.post("/api/parent/verify", json={"pin": "5678"}).json()["ok"])

    def test_system_message(self):
        m = self.server.tutor_system_message("az", None, "Riyaziyyat", "Faiz", {"level_index": 1})
        self.assertIn("Təlim nəticələri", m)
        self.assertIn("sadə dil", m)
        self.assertIn("çətin", self.server.tutor_system_message("az", None, "Riyaziyyat", "Faiz", {"level_index": 4}))
