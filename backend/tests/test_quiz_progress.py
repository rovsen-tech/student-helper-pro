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
    def test_mcq_with_key_outside_options_is_dropped_not_repaired(self):
        qs, dropped = qe.validate_questions([{"type": "multiple_choice", "question": "Hansı rəng?",
                                              "options": ["1", "2", "3", "5"], "correct_answer": "4"}], 5)
        self.assertEqual(qs, [])
        self.assertEqual(dropped, 1)

    def test_mcq_needs_exactly_four_distinct_options(self):
        base = {"type": "multiple_choice", "question": "Q?", "correct_answer": "a"}
        self.assertEqual(qe.sanitize_questions([{**base, "options": ["a", "b", "c"]}], 5), [])
        self.assertEqual(qe.sanitize_questions([{**base, "options": ["a", "A", "b", "c"]}], 5), [])
        self.assertEqual(len(qe.sanitize_questions([{**base, "options": ["a", "b", "c", "d"]}], 5)), 1)

    def test_wrong_arithmetic_key_is_dropped(self):
        bad = {"type": "short_answer", "question": "12 + 7 neçədir?", "correct_answer": "18"}
        good = {"type": "short_answer", "question": "3 × 4 neçədir?", "correct_answer": "12"}
        qs, dropped = qe.validate_questions([bad, good], 5)
        self.assertEqual([q["question"] for q in qs], ["3 × 4 neçədir?"])
        self.assertEqual(dropped, 1)

    def test_sanitize_drops_invalid_duplicates_and_limits(self):
        raw = [{"question": "", "correct_answer": "x"}, "bad",
               {"type": "short_answer", "question": "A?", "correct_answer": "B"}] * 5
        qs = qe.sanitize_questions(raw, 3)
        self.assertEqual([q["id"] for q in qs], ["q1"])

    def test_numeric_and_az_normalization(self):
        self.assertTrue(qe.answers_equal("0,5", "1/2"))
        self.assertTrue(qe.answers_equal("yarım", "0.5"))
        self.assertTrue(qe.answers_equal("50%", "1/2"))
        self.assertTrue(qe.answers_equal("5 sm", "5"))
        self.assertTrue(qe.answers_equal("İSİM", "isim"))
        self.assertTrue(qe.answers_equal("«Bakı»!", "bakı"))
        self.assertFalse(qe.answers_equal("0,4", "1/2"))
        self.assertIsNone(qe.answers_equal("ağac", "bitki"))
        self.assertIsNone(qe.parse_number("1/0"))

    def test_quick_evaluate(self):
        mc = {"type": "multiple_choice", "correct_answer": "İki"}
        self.assertTrue(qe.quick_evaluate(mc, " iki. "))
        self.assertFalse(qe.quick_evaluate(mc, "üç"))
        self.assertTrue(qe.quick_evaluate({"type": "short_answer", "correct_answer": "4"}, "dörd"))
        self.assertFalse(qe.quick_evaluate({"type": "short_answer", "correct_answer": "4"}, "5"))
        self.assertIsNone(qe.quick_evaluate({"type": "short_answer", "correct_answer": "fotosintez"},
                                            "bitkinin qida hazırlaması"))

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


class MasteryTests(unittest.TestCase):
    def _a(self, i, correct, quiz="z1", day="2026-10-18"):
        return {"question_key": f"k{i}", "question": f"S{i}", "correct": correct, "quiz_id": quiz, "day": day}

    def test_empty(self):
        self.assertEqual(pm.compute_mastery([])["level"], "başlanmayıb")

    def test_only_first_attempt_counts(self):
        ans = [self._a(1, False)] + [self._a(1, True)] * 20
        m = pm.compute_mastery(ans)
        self.assertEqual(m["answered"], 1)
        self.assertEqual(m["distinct_correct"], 0)
        self.assertEqual(m["review_questions"], ["S1"])

    def test_mastered_requires_multiple_quizzes_and_days(self):
        one_day = [self._a(i, True) for i in range(10)]
        self.assertEqual(pm.compute_mastery(one_day)["level"], "mənimsəyir")
        spread = [self._a(i, True, quiz=f"z{i % 2}", day=f"2026-10-1{i % 2}") for i in range(10)]
        self.assertEqual(pm.compute_mastery(spread)["level"], "mənimsəyib")

    def test_low_accuracy(self):
        ans = [self._a(i, i == 0) for i in range(10)]
        self.assertEqual(pm.compute_mastery(ans)["level"], "başlanğıc")


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
        asyncio.get_event_loop().run_until_complete(self.server.progress_manager.ensure_indexes(self.server.db))
        self.client = self.TestClient(self.server.app)

    def _make_quiz(self, headers=None):
        _FakeChat.replies = [json.dumps({"questions": [
            {"type": "multiple_choice", "question": "1/2 nədir?", "options": ["yarım", "tam", "üçdə bir", "sıfır"],
             "correct_answer": "yarım", "hint": "Almanı ikiyə böl."},
            {"type": "multiple_choice", "question": "2+2?", "options": ["3", "4", "5", "6"],
             "correct_answer": "4", "hint": "Barmaqlarla say."},
            {"type": "short_answer", "question": "Yarım neçə faizdir?", "correct_answer": "50%",
             "hint": "Yüzün yarısı."}]})]
        r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Adi kəsrlər"},
                             headers=headers or {})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def _submit(self, quiz_id, qid, ans, reply=None, headers=None, raw=False):
        _FakeChat.replies = [reply or '{"correct": true, "score": 10, "feedback": "Düzdür", "encouragement": "Əla!"}']
        r = self.client.post("/api/quiz/submit", json={"quiz_id": quiz_id, "question_id": qid,
                                                       "student_answer": ans}, headers=headers or {})
        return r if raw else r.json()

    def _student(self, name):
        r = self.client.post("/api/students", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        return {"X-Student-Id": r.json()["id"]}

    def test_generate_hides_answers(self):
        data = self._make_quiz()
        self.assertEqual(len(data["questions"]), 3)
        self.assertNotIn("correct_answer", data["questions"][0])

    def test_perfect_quiz_awards_bonus_and_badge_once(self):
        quiz = self._make_quiz()
        r1 = self._submit(quiz["quiz_id"], "q1", "yarım")
        self.assertTrue(r1["correct"])
        self.assertEqual(r1["xp_earned"], 20)
        dup = self._submit(quiz["quiz_id"], "q1", "yarım")
        self.assertEqual(dup["xp_earned"], 0)
        self._submit(quiz["quiz_id"], "q2", "4")
        r3 = self._submit(quiz["quiz_id"], "q3", "0,5")  # deterministik: 50% == 0,5
        self.assertTrue(r3["perfect"])
        self.assertEqual(r3["xp_earned"], 120)
        self.assertEqual(r3["badge_earned"], "Quiz qalibi")
        self.assertEqual(r3["mastery"]["distinct_correct"], 3)
        stats = self.client.get("/api/progress/stats").json()
        self.assertEqual(stats["total_xp"], 160)
        self.assertEqual(stats["quiz_correct_pct"], 100)
        self.assertIn("Quiz qalibi", stats["badges"])
        hist = self.client.get("/api/quiz/history", params={"subject": "Riyaziyyat"}).json()
        self.assertEqual(hist[0]["correct_count"], 3)

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
        self.assertEqual(again["xp_earned"], 0)
        self.assertFalse(again["first_time"])
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

    def test_student_isolation(self):
        a, b = self._student("Aysel"), self._student("Murad")
        quiz = self._make_quiz(headers=a)
        r = self._submit(quiz["quiz_id"], "q1", "yarım", headers=b, raw=True)
        self.assertEqual(r.status_code, 404)  # B, A-nın quizinə cavab verə bilməz
        self._submit(quiz["quiz_id"], "q1", "yarım", headers=a)
        self.client.post("/api/progress/lesson-complete", json={"subject": "Riyaziyyat", "topic": "Faiz"}, headers=a)
        sa = self.client.get("/api/progress/stats", headers=a).json()
        sb = self.client.get("/api/progress/stats", headers=b).json()
        sd = self.client.get("/api/progress/stats").json()
        self.assertEqual(sa["total_xp"], 70)
        self.assertEqual(sb["total_xp"], 0)
        self.assertEqual(sd["total_xp"], 0)
        self.assertEqual(self.client.get("/api/quiz/history", headers=b).json(), [])
        self.assertEqual(self.client.get("/api/progress", headers=b).json()["lessons_started"], 0)
        self.assertEqual(self.client.get("/api/messages", params={"subject": "R", "topic": "T"},
                                         headers=b).json(), [])

    def test_unknown_or_malformed_student_rejected(self):
        for sid in ["abcdef0123456789", "../../etc", "x" * 100]:
            r = self.client.get("/api/progress/stats", headers={"X-Student-Id": sid})
            self.assertEqual(r.status_code, 404, sid)

    def test_students_list_and_limit(self):
        self.server.MAX_STUDENTS = 2
        try:
            self._student("A")
            self._student("B")
            r = self.client.post("/api/students", json={"name": "C"})
            self.assertEqual(r.status_code, 400)
            names = [s["name"] for s in self.client.get("/api/students").json()]
            self.assertEqual(names, ["Əsas profil", "A", "B"])
        finally:
            self.server.MAX_STUDENTS = 10

    def test_concurrent_submits_award_xp_once(self):
        quiz = self._make_quiz()
        q = (asyncio.get_event_loop().run_until_complete(
            self.server.db.quizzes.find_one({"quiz_id": quiz["quiz_id"]})))["questions"][0]

        async def race():
            return await asyncio.gather(*[self.server.progress_manager.record_quiz_answer(
                self.server.db, "default", quiz["quiz_id"], q, "Riyaziyyat", "Adi kəsrlər", True)
                for _ in range(5)])
        xps = asyncio.get_event_loop().run_until_complete(race())
        self.assertEqual(sorted(xps), [0, 0, 0, 0, 20])
        self.assertEqual(self.client.get("/api/progress/stats").json()["total_xp"], 20)

    def test_daily_quiz_limit(self):
        self.server.QUIZ_DAILY_LIMIT = 1
        try:
            self._make_quiz()
            r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Faiz"})
            self.assertEqual(r.status_code, 429)
        finally:
            self.server.QUIZ_DAILY_LIMIT = 10

    def test_too_few_valid_questions_returns_502(self):
        _FakeChat.replies = [json.dumps({"questions": [
            {"type": "multiple_choice", "question": "Q?", "options": ["a", "b"], "correct_answer": "a"},
            {"type": "short_answer", "question": "2 + 2 neçədir?", "correct_answer": "5"}]})]
        r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Faiz"})
        self.assertEqual(r.status_code, 502)

    def test_legacy_docs_backfilled_to_default(self):
        db = self.server.db
        loop = asyncio.get_event_loop()
        loop.run_until_complete(db.progress.insert_one({"subject": "Tarix", "topic": "Qədim insanlar",
                                                        "question_count": 3}))
        loop.run_until_complete(self.server.progress_manager.ensure_indexes(db))
        data = self.client.get("/api/progress").json()
        self.assertEqual(data["total_questions"], 3)
        self.assertEqual(self.client.get("/api/progress", headers=self._student("Y")).json()["total_questions"], 0)

    def test_generate_failure_returns_502(self):
        _FakeChat.replies = ["bağışla, JSON yoxdur"]
        r = self.client.post("/api/quiz/generate", json={"subject": "Riyaziyyat", "topic": "Faiz"})
        self.assertEqual(r.status_code, 502)


if __name__ == "__main__":
    unittest.main()
