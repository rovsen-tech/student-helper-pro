"""5-ci sinif kurikulumunun genişləndirilməsi: yeni fənlər/mövzular, məcburi sahələr və /api/curriculum endpoint-i.

Həmçinin məşq cavabının deterministik hökmünün SSE `done` hadisəsində qaytarılması (mini-quiz təklifi üçün).
Gemini mock-dur. TEST_REAL_MONGO_URL verilərsə REAL MongoDB-də, əks halda mongomock-da işləyir.
"""
import json
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_quiz_progress import _install_stubs  # noqa: E402
from tests.test_fraction_flow import _CaptureChat  # noqa: E402

NEW_SUBJECTS = {
    "İnformatika": ["İnformasiya nədir", "Kompüterin hissələri", "İnternet", "Təhlükəsizlik qaydaları"],
    "İngilis dili": ["Greetings", "Numbers and colours", "Family members"],
    "Tarix": ["Qədim insanlar", "Azərbaycanın qədim tarixi", "Tarixi abidələr"],
    "Musiqi": ["Notlar", "Musiqi alətləri", "Muğam"],
    "Təsviri incəsənət": ["Rənglər aləmi", "Milli naxışlar", "Xalça sənəti"],
    "Texnologiya": ["Materiallar", "Qida və sağlamlıq", "Təhlükəsizlik qaydaları"],
    "Fiziki tərbiyə": ["Sağlam həyat tərzi", "Gimnastika", "İdman oyunları"],
    "Coğrafiya": ["Materiklər və okeanlar", "Azərbaycanın coğrafiyası"],
}
EXISTING = {"Riyaziyyat", "Azərbaycan dili", "Təbiət"}
REQUIRED = ("learning_outcomes", "key_concepts", "common_mistakes", "hints", "sample_problems")


class CurriculumData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import curriculum
        cls.cur = curriculum

    def test_all_subjects_present(self):
        names = set(self.cur.CURRICULUM)
        self.assertTrue(EXISTING <= names, names)
        self.assertTrue(set(NEW_SUBJECTS) <= names, set(NEW_SUBJECTS) - names)

    def test_new_topics_have_required_fields(self):
        for subj, topics in NEW_SUBJECTS.items():
            for topic in topics:
                with self.subTest(subject=subj, topic=topic):
                    info = self.cur.get_topic_info(subj, topic)
                    self.assertIsNotNone(info)
                    for field in REQUIRED:
                        self.assertIsInstance(info.get(field), list, field)
                        self.assertTrue(info[field], f"{field} boşdur")
                    self.assertIsInstance(info.get("difficulty_order"), int)
                    self.assertGreaterEqual(info["difficulty_order"], 1)
                    for p in info["sample_problems"]:
                        self.assertTrue(p.get("question") and p.get("answer"), p)

    def test_existing_topics_keep_fields(self):
        for subj in EXISTING:
            for topic, info in self.cur.CURRICULUM[subj].items():
                with self.subTest(subject=subj, topic=topic):
                    for field in REQUIRED:
                        self.assertIn(field, info)
                    self.assertTrue(info["sample_problems"])

    def test_subject_topics_in_server_have_curriculum(self):
        _install_stubs()
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "test_db")
        import server
        for s in server.SUBJECTS:  # /api/subjects-dəki HƏR mövzunun kurikulum məlumatı olmalıdır
            for topic in s["topics"]:
                with self.subTest(subject=s["name"], topic=topic):
                    self.assertIsNotNone(self.cur.get_topic_info(s["name"], topic))


class CurriculumApi(unittest.TestCase):
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
        s = self.server
        _CaptureChat.calls, _CaptureChat.replies = [], []
        s.make_chat = lambda sid, sysmsg: _CaptureChat(sid, sysmsg)
        s.init_storage = lambda *a, **k: "k"
        if self.REAL_MONGO:
            from motor.motor_asyncio import AsyncIOMotorClient
            name = f"t_cur_{uuid.uuid4().hex[:10]}"
            mc = AsyncIOMotorClient(self.REAL_MONGO, serverSelectionTimeoutMS=3000)
            s.db = mc[name]
        else:
            from mongomock_motor import AsyncMongoMockClient
            s.db = AsyncMongoMockClient()["curexp"]
        self.c = self.TestClient(s.app)
        self.c.__enter__()
        self.addCleanup(self.c.__exit__, None, None, None)
        if self.REAL_MONGO:
            self.addCleanup(lambda: self.c.portal.call(mc.drop_database, name))

    def test_endpoint_returns_200_for_new_topics(self):
        for subj, topics in NEW_SUBJECTS.items():
            for topic in topics:
                with self.subTest(subject=subj, topic=topic):
                    r = self.c.get(f"/api/curriculum/{subj}/{topic}")
                    self.assertEqual(r.status_code, 200, r.text)
                    body = r.json()
                    for field in REQUIRED:
                        self.assertIn(field, body)

    def test_endpoint_404_for_unknown_topic(self):
        self.assertEqual(self.c.get("/api/curriculum/Tarix/Yoxdur").status_code, 404)

    def _done_event(self, text):
        events = [json.loads(p[len("data: "):]) for p in text.split("\n\n") if p.startswith("data: ")]
        done = [e for e in events if e.get("done")]
        self.assertEqual(len(done), 1, text)
        return done[0]

    def test_practice_verdict_in_done_event(self):
        h = {"X-Student-Id": self.c.post("/api/students", json={"name": "Aysel"}).json()["id"]}
        base = {"subject": "Riyaziyyat", "topic": "Adi kəsrlər", "lang": "az"}
        _CaptureChat.replies = ["Salam! 1/4 + 2/4 neçədir?", "Əla, izah edirəm.", "2 + 3 neçədir?", "Düzdür!",
                                "4 + 4 neçədir?", "Yenə cəhd et."]
        self.assertIsNone(self._done_event(self.c.post("/api/chat", json={**base, "explain": True}, headers=h).text)
                          .get("verdict"))
        self.c.post("/api/chat", json={**base, "message": "3/4"}, headers=h)
        self.c.post("/api/chat", json={**base, "stage": "quiz_next"}, headers=h)
        ok = self.c.post("/api/chat", json={**base, "stage": "quiz_answer", "message": "5"}, headers=h)
        self.assertIs(self._done_event(ok.text)["verdict"], True)
        self.c.post("/api/chat", json={**base, "stage": "quiz_next"}, headers=h)
        bad = self.c.post("/api/chat", json={**base, "stage": "quiz_answer", "message": "9"}, headers=h)
        self.assertIs(self._done_event(bad.text)["verdict"], False)


if __name__ == "__main__":
    unittest.main()
