import asyncio
import json
import os
import sys
import unittest
from datetime import date

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import progress_manager as pm  # noqa: E402
import quiz_engine as qe  # noqa: E402


class QuizEngineTests(unittest.TestCase):
    def test_sanitize_adds_correct_answer_to_options(self):
        qs = qe.sanitize_questions([{"type": "multiple_choice", "question": "2+2?",
                                     "options": ["1", "2", "3", "5"], "correct_answer": "4"}], 5)
        self.assertIn("4", qs[0]["options"])
        self.assertEqual(len(qs[0]["options"]), 4)

    def test_sanitize_drops_invalid_and_limits(self):
        raw = [{"question": "", "correct_answer": "x"}, "bad", {"question": "A?", "correct_answer": "B"}] * 5
        qs = qe.sanitize_questions(raw, 3)
        self.assertEqual([q["id"] for q in qs], ["q1"])
        self.assertEqual(qs[0]["type"], "short_answer")

    def test_quick_evaluate(self):
        mc = {"type": "multiple_choice", "correct_answer": "İki"}
        self.assertTrue(qe.quick_evaluate(mc, " iki. "))
        self.assertFalse(qe.quick_evaluate(mc, "üç"))
        self.assertIsNone(qe.quick_evaluate({"type": "short_answer", "correct_answer": "4"}, "dörd"))

    def test_parse_json_robust(self):
        self.assertEqual(qe._parse_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertIsNone(qe._parse_json("json yoxdur"))


class ProgressPureTests(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(pm.level_info(0)["level"], "Yeni başlayan")
        self.assertEqual(pm.level_info(200)["level"], "Öyrənən")
        self.assertEqual(pm.level_info(999)["level"], "Çalışqan")
        self.assertEqual(pm.level_info(1500)["level"], "Ustalaşan")
        self.assertEqual(pm.level_info(5000)["level"], "Deha")
        self.assertEqual(pm.level_info(100)["level_progress_pct"], 50)

    def test_streak(self):
        today = date(2026, 10, 18)
        days = ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18", "2026-10-10"]
        self.assertEqual(pm.compute_streak(days, today), 5)
        self.assertEqual(pm.compute_streak(["2026-10-17"], today), 1)
        self.assertEqual(pm.compute_streak(["2026-10-15"], today), 0)
        self.assertEqual(pm.compute_streak([], today), 0)


class _FakeChat:
    """emergentintegrations əvəzinə: əvvəlcədən hazır JSON qaytarır."""
    replies = []

    def __init__(self, *a, **k):
        pass

    async def stream_message(self, msg):
        from emergentintegrations.llm.chat import TextDelta, StreamDone
        yield TextDelta(_FakeChat.replies.pop(0))
        yield StreamDone()


def _install_stubs():
    import types
    if "emergentintegrations.llm.chat" in sys.modules and hasattr(sys.modules["emergentintegrations.llm.chat"], "_is_stub"):
        return
    try:
        import emergentintegrations.llm.chat  # noqa: F401
        return
    except Exception:
        pass
    for n in ["emergentintegrations", "emergentintegrations.llm",
              "emergentintegrations.llm.chat", "emergentintegrations.llm.openai"]:
        sys.modules[n] = types.ModuleType(n)
    chat = sys.modules["emergentintegrations.llm.chat"]
    chat._is_stub = True

    class TextDelta:
        def __init__(self, content):
            self.content = content

    class StreamDone:
        pass

    class UserMessage:
        def __init__(self, text="", file_contents=None):
            self.text = text

    chat.TextDelta, chat.StreamDone, chat.UserMessage = TextDelta, StreamDone, UserMessage
    chat.LlmChat = chat.FileContentWithMimeType = object
    sys.modules["emergentintegrations.llm.openai"].OpenAITextToSpeech = object


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from mongomock_motor import AsyncMongoMockClient
            from fastapi.testclient import TestClient
        except ImportError as exc:
            raise unittest.SkipTest(f"mongomock_motor/fastapi yoxdur: {exc}")
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "test_db")
        _install_stubs()
        try:
            import server
        except Exception as exc:
            raise unittest.SkipTest(f"server import edilmədi: {exc}")
        cls.server = server
        cls.TestClient = TestClient
        cls.Mock = AsyncMongoMockClient

    def setUp(self):
        self.server.db = self.Mock()["t"]
        self.server.make_chat = lambda *a, **k: _FakeChat()
        self.server.init_storage = lambda *a, **k: "k"
        self.client = self.TestClient(self.server.app)

    def _make_quiz(self):
        _FakeChat.replies = [json.dumps({"questions": [
            {"type": "multiple_choice", "question": "1/2 nədir?", "options": ["yarım", "tam", "üçdə bir", "sıfır"],
             "correct_answer": "yarım", "hint": "Almanı ikiyə böl."},
            {"type": "multiple_choice", "question": "2+2?", "options": ["3", "4", "5", "6"],
             "correct_answer": "4", "hint": "Barmaqlarla say."}]})]
        r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Adi kəsrlər"})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _submit(self, quiz_id, qid, ans, reply=None):
        _FakeChat.replies = [reply or '{"correct": true, "score": 10, "feedback": "Düzdür", "encouragement": "Əla!"}']
        return self.client.post("/api/quiz/submit", json={"quiz_id": quiz_id, "question_id": qid,
                                                          "student_answer": ans}).json()

    def test_generate_hides_answers(self):
        data = self._make_quiz()
        self.assertEqual(len(data["questions"]), 2)
        self.assertNotIn("correct_answer", data["questions"][0])

    def test_perfect_quiz_awards_bonus_and_badge_once(self):
        quiz = self._make_quiz()
        r1 = self._submit(quiz["quiz_id"], "q1", "yarım")
        self.assertTrue(r1["correct"])
        self.assertEqual(r1["xp_earned"], 20)
        dup = self._submit(quiz["quiz_id"], "q1", "yarım")
        self.assertEqual(dup["xp_earned"], 0)
        r2 = self._submit(quiz["quiz_id"], "q2", "4")
        self.assertTrue(r2["perfect"])
        self.assertEqual(r2["xp_earned"], 120)
        self.assertEqual(r2["badge_earned"], "Quiz qalibi")
        stats = self.client.get("/api/progress/stats").json()
        self.assertEqual(stats["total_xp"], 140)
        self.assertEqual(stats["quiz_correct_pct"], 100)
        self.assertIn("Quiz qalibi", stats["badges"])
        hist = self.client.get("/api/quiz/history", params={"subject": "Riyaziyyat"}).json()
        self.assertEqual(hist[0]["correct_count"], 2)

    def test_wrong_mc_answer_cannot_be_overridden_by_llm(self):
        quiz = self._make_quiz()
        r = self._submit(quiz["quiz_id"], "q2", "5")
        self.assertFalse(r["correct"])
        self.assertEqual(r["xp_earned"], 0)
        self.assertEqual(r["correct_answer"], "4")

    def test_lesson_complete_flow(self):
        r = self.client.post("/api/progress/lesson-complete",
                             json={"subject": "Riyaziyyat", "topic": "Faiz"}).json()
        self.assertEqual(r["xp_earned"], 50)
        self.assertEqual(r["badge_earned"], "İlk dərs")
        self.assertTrue(r["confetti"])
        again = self.client.post("/api/progress/lesson-complete",
                                 json={"subject": "Riyaziyyat", "topic": "Faiz"}).json()
        self.assertEqual(again["xp_earned"], 10)
        self.assertIsNone(again["badge_earned"])
        stats = self.client.get("/api/progress/stats").json()
        self.assertEqual(stats["lessons_complete"], 1)
        self.assertEqual(stats["streak_days"], 1)
        self.assertEqual(stats["level"], "Yeni başlayan")

    def test_subject_master_badge(self):
        topics = next(s["topics"] for s in self.server.SUBJECTS if s["name"] == "Tarix")
        last = None
        for t in topics:
            last = self.client.post("/api/progress/lesson-complete", json={"subject": "Tarix", "topic": t}).json()
        self.assertIn("Fənn ustası", last["badges_earned"])

    def test_empty_stats_and_404s(self):
        stats = self.client.get("/api/progress/stats").json()
        self.assertEqual(stats["total_xp"], 0)
        self.assertEqual(stats["badges"], [])
        r = self.client.post("/api/quiz/submit", json={"quiz_id": "x", "question_id": "q1", "student_answer": "a"})
        self.assertEqual(r.status_code, 404)

    def test_generate_failure_returns_502(self):
        _FakeChat.replies = ["bağışla, JSON yoxdur"]
        r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Faiz"})
        self.assertEqual(r.status_code, 502)


if __name__ == "__main__":
    unittest.main()
