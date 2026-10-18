"""«Adi kəsrlər» dərs axını: diaqnostika → uyğunlaşma → deterministik kəsr yoxlaması → XP/mastery → F5 → izolyasiya.

Gemini mock-dur (real API çağırılmır). TEST_REAL_MONGO_URL verilərsə REAL MongoDB-də
(hər test üçün ayrıca, sonda silinən baza), əks halda mongomock-da işləyir.
"""
import json
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_quiz_progress import _install_stubs  # noqa: E402

SUBJ, TOPIC = "Riyaziyyat", "Adi kəsrlər"


class _CaptureChat:
    """Gemini əvəzi: göndərilən prompt və system message-i yadda saxlayır, hazır cavab qaytarır."""
    calls = []
    replies = []

    def __init__(self, session_id=None, system_message=None):
        self.system_message = system_message

    async def stream_message(self, msg):
        from emergentintegrations.llm.chat import TextDelta, StreamDone
        _CaptureChat.calls.append({"text": msg.text, "system": self.system_message})
        yield TextDelta(_CaptureChat.replies.pop(0) if _CaptureChat.replies else "Yaxşı.")
        yield StreamDone(content=None, tool_calls=None, finish_reason="stop", usage=None, raw=None)


class FractionValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import quiz_engine
        cls.qe = quiz_engine

    def test_equivalent_fractions(self):
        v = self.qe.validate_fraction_answer
        self.assertTrue(v("1/2", "2/4"))
        self.assertTrue(v("3/4", "6/8"))
        self.assertTrue(v("0,5", "1/2"))
        self.assertTrue(v("yarım", "2/4"))
        self.assertFalse(v("1/3", "1/2"))
        self.assertFalse(v("2/8", "1/2"))  # 1/4 + 1/4 = 2/8 tipik səhvi

    def test_mixed_numbers(self):
        v = self.qe.validate_fraction_answer
        self.assertTrue(v("1 1/2", "3/2"))       # əvvəl "11/2" kimi oxunurdu
        self.assertTrue(v("2 tam 1/4", "9/4"))
        self.assertFalse(v("1 1/2", "11/2"))
        self.assertTrue(v("4 700", "4700"))      # min ayırıcı boşluq pozulmayıb

    def test_simplify_question_requires_lowest_terms(self):
        q = {"type": "short_answer", "question": "6/8 kəsrini ixtisar et.", "correct_answer": "3/4"}
        self.assertTrue(self.qe.quick_evaluate(q, "3/4"))
        self.assertFalse(self.qe.quick_evaluate(q, "6/8"))
        self.assertTrue(self.qe.quick_evaluate({**q, "question": "1/2 nəyə bərabərdir?", "correct_answer": "2/4"},
                                               "1/2"))

    def test_fraction_arithmetic_check(self):
        self.assertTrue(self.qe.check_arithmetic("1/4 + 2/4 neçədir?", "3/4"))
        self.assertFalse(self.qe.check_arithmetic("1/4 + 1/4 neçədir?", "2/8"))
        self.assertTrue(self.qe.check_arithmetic("1/4 + 1/4 neçədir?", "1/2"))


class FractionLessonFlow(unittest.TestCase):
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
            name = f"t_frac_{uuid.uuid4().hex[:10]}"
            mc = AsyncIOMotorClient(self.REAL_MONGO, serverSelectionTimeoutMS=3000)
            s.db = mc[name]
        else:
            from mongomock_motor import AsyncMongoMockClient
            s.db = AsyncMongoMockClient()["frac"]
        self.c = self.TestClient(s.app)
        self.c.__enter__()
        self.addCleanup(self.c.__exit__, None, None, None)
        if self.REAL_MONGO:
            self.addCleanup(lambda: self.c.portal.call(mc.drop_database, name))
        self._run(s.progress_manager.ensure_indexes(s.db))

    def _run(self, coro):
        async def _await():
            return await coro
        return self.c.portal.call(_await)

    def _student(self, name):
        r = self.c.post("/api/students", json={"name": name})
        self.assertEqual(r.status_code, 200, r.text)
        return {"X-Student-Id": r.json()["id"]}

    def _chat(self, h, **body):
        _CaptureChat.calls.clear()
        r = self.c.post("/api/chat", json={"subject": SUBJ, "topic": TOPIC, "lang": "az", **body}, headers=h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn('"done": true', r.text)
        return _CaptureChat.calls[-1]

    def _diagnostic(self, h):
        _CaptureChat.replies = ["Salam! Bu gün adi kəsrləri öyrənəcəyik. 1/4 + 2/4 neçədir?"]
        return self._chat(h, explain=True)

    def _quiz(self, h):
        from tests.test_quiz_progress import _FakeChat
        self.server.make_chat = lambda *a, **k: _FakeChat()
        _FakeChat.replies = [json.dumps({"questions": [
            {"type": "short_answer", "question": "1/4 + 2/4 neçədir?", "correct_answer": "3/4", "hint": "Surətləri topla."},
            {"type": "short_answer", "question": "6/8 kəsrini ixtisar et.", "correct_answer": "3/4", "hint": "2-yə böl."},
            {"type": "multiple_choice", "question": "Hansı böyükdür?", "options": ["1/3", "1/5", "1/7", "1/9"],
             "correct_answer": "1/3", "hint": "Məxrəc kiçikdirsə, hissə böyükdür."}]})]
        r = self.c.post("/api/quiz/generate", json={"subject": SUBJ, "topic": TOPIC, "n_questions": 3}, headers=h)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["quiz_id"]

    def _submit(self, h, quiz_id, qid, ans):
        r = self.c.post("/api/quiz/submit", json={"quiz_id": quiz_id, "question_id": qid, "student_answer": ans},
                        headers=h)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    # ---- a–c: diaqnostika və uyğunlaşma ----
    def test_diagnostic_prompt_uses_curriculum_and_beginner_adaptation(self):
        h = self._student("Ali")
        call = self._diagnostic(h)
        self.assertIn("diaqnostik sual", call["text"])
        self.assertIn("Adi kəsrlər", call["system"])
        self.assertIn("məxrəc", call["system"])                    # curriculum key_concepts
        self.assertIn("məxrəcləri də toplayır", call["system"])    # curriculum common_mistakes
        self.assertIn("daha sadə dil", call["system"])             # mastery yoxdur → yeni başlayan

    def test_wrong_diagnostic_answer_triggers_simpler_explanation_and_hint(self):
        h = self._student("Ali")
        self._diagnostic(h)
        call = self._chat(h, message="3/8")
        self.assertIn("cavabı SƏHVDİR", call["text"])
        self.assertIn("daha sadə dillə", call["text"])
        self.assertIn("əsas məşq sualı", call["text"])
        self.assertIn("Kəsrləri toplayanda", call["text"])          # kurikulum ipucu
        self.assertIn("1/4 + 2/4 neçədir?", call["text"])          # diaqnostik sual kontekstdə

    def test_correct_equivalent_diagnostic_answer_advances(self):
        h = self._student("Ali")
        self._diagnostic(h)
        call = self._chat(h, message="6/8")                         # 6/8 == 3/4
        self.assertIn("Sistem yoxlaması: şagirdin cavabı DÜZDÜR", call["text"])
        self.assertNotIn("cavabı SƏHVDİR", call["text"])

    def test_quiz_answer_stage_checks_last_question(self):
        h = self._student("Ali")
        self._diagnostic(h)
        _CaptureChat.replies = ["İzah... İndi de: 1/5 + 3/5 neçədir?"]
        self._chat(h, message="3/4")
        call = self._chat(h, message="4/10", stage="quiz_answer")
        self.assertIn("cavabı SƏHVDİR", call["text"])
        call = self._chat(h, message="4/5", stage="quiz_answer")
        self.assertIn("1/5 + 3/5", call["text"])  # yeni cavab sonuncu suala qarşı yoxlanır

    # ---- h, j: mastery və təkrar XP qoruması ----
    def test_duplicate_submission_does_not_double_xp_and_mastery_saved(self):
        h = self._student("Ali")
        qid = self._quiz(h)
        first = self._submit(h, qid, "q1", "3/4")
        self.assertTrue(first["correct"])
        self.assertEqual(first["xp_earned"], 20)
        dup = self._submit(h, qid, "q1", "3/4")
        self.assertEqual(dup["xp_earned"], 0)
        self.assertTrue(dup["already_answered"])
        self.assertFalse(self._submit(h, qid, "q2", "6/8")["correct"])   # ixtisar edilməyib
        last = self._submit(h, qid, "q3", "1/3")
        self.assertTrue(last["quiz_complete"])
        self.assertEqual(last["mastery"]["answered"], 3)
        self.assertEqual(last["mastery"]["distinct_correct"], 2)
        stats = self.c.get("/api/progress/stats", headers=h).json()
        self.assertEqual(stats["total_xp"], 40)
        self.assertEqual(self._run(self.server.db.quiz_answers.count_documents({})), 3)

    # ---- k: izolyasiya ----
    def test_student_isolation(self):
        ali, vali = self._student("ali"), self._student("vali")
        self._diagnostic(ali)
        self._chat(ali, message="3/4")
        qid = self._quiz(ali)
        self._submit(ali, qid, "q1", "3/4")
        params = {"subject": SUBJ, "topic": TOPIC}
        self.assertEqual(len(self.c.get("/api/messages", params=params, headers=ali).json()), 3)
        self.assertEqual(self.c.get("/api/messages", params=params, headers=vali).json(), [])
        self.assertEqual(self.c.get("/api/progress/mastery", headers=vali).json(), [])
        self.assertEqual(self.c.get("/api/progress/stats", headers=vali).json()["total_xp"], 0)
        r = self.c.post("/api/quiz/submit", json={"quiz_id": qid, "question_id": "q2", "student_answer": "3/4"},
                        headers=vali)
        self.assertEqual(r.status_code, 404)

    # ---- i: F5 davamlılığı ----
    def test_reload_restores_history_and_mastery(self):
        h = self._student("Ali")
        self._diagnostic(h)
        self._chat(h, message="3/4")
        qid = self._quiz(h)
        self._submit(h, qid, "q1", "3/4")
        # "F5": server state saxlamır; brauzer yeni sorğularla eyni şagird üçün tarixçə və mastery-ni DB-dən alır.
        # (Motor klienti event loop-a bağlı olduğu üçün TestClient yenidən yaradılmır.)
        self.server.make_chat = lambda sid, sysmsg: _CaptureChat(sid, sysmsg)
        hist = self.c.get("/api/messages", params={"subject": SUBJ, "topic": TOPIC}, headers=h).json()
        self.assertEqual([m["role"] for m in hist], ["assistant", "user", "assistant"])
        self.assertEqual(hist[1]["content"], "3/4")
        mastery = self.c.get("/api/progress/mastery", params=params_of(), headers=h).json()
        self.assertEqual(mastery[0]["answered"], 1)
        call = self._chat(h, message="Bəs 2/3 + 1/3?")
        self.assertIn("Şagird: 3/4", call["text"])                 # kontekst bərpa olunub
        self.assertIn("Uyğunlaşma:", call["system"])

    def test_new_lesson_archives_instead_of_deleting(self):
        h = self._student("Ali")
        self._diagnostic(h)
        self._chat(h, message="3/4")
        self._diagnostic(h)  # dərsə yenidən başlamaq
        hist = self.c.get("/api/messages", params=params_of(), headers=h).json()
        self.assertEqual(len(hist), 1)
        db = self.server.db
        self.assertEqual(self._run(db.messages.count_documents({"archived": True})), 3)  # silinmədi

    def test_context_uses_most_recent_messages(self):
        h = self._student("Ali")
        self._diagnostic(h)
        for i in range(12):
            self._chat(h, message=f"sual-{i:02d}")
        call = self._chat(h, message="son")
        self.assertIn("sual-11", call["text"])
        self.assertNotIn("sual-00", call["text"])


def params_of():
    return {"subject": SUBJ, "topic": TOPIC}


if __name__ == "__main__":
    unittest.main()
