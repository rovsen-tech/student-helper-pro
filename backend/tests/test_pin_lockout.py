"""Valideyn PIN-i üçün brute-force qorunması (5 səhv -> 5 dəqiqə 429).

TEST_REAL_MONGO_URL verilərsə REAL MongoDB-də (hər test üçün ayrıca, sonda silinən baza), əks halda mongomock-da.
"""
import os
import sys
import unittest
import uuid
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_quiz_progress import _install_stubs, _FakeChat  # noqa: E402


class PinLockout(unittest.TestCase):
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
        s.make_chat = lambda *a, **k: _FakeChat()
        s.init_storage = lambda *a, **k: "k"
        real_now = s._now
        self.offset = timedelta(0)
        s._now = lambda: real_now() + self.offset
        self.addCleanup(setattr, s, "_now", real_now)
        if self.REAL_MONGO:
            from motor.motor_asyncio import AsyncIOMotorClient
            name = f"t_pin_{uuid.uuid4().hex[:10]}"
            mc = AsyncIOMotorClient(self.REAL_MONGO, serverSelectionTimeoutMS=3000)
            s.db = mc[name]
        else:
            from mongomock_motor import AsyncMongoMockClient
            s.db = AsyncMongoMockClient()["pinlock"]
        self.c = self.TestClient(s.app)
        self.c.__enter__()
        self.addCleanup(self.c.__exit__, None, None, None)
        if self.REAL_MONGO:
            self.addCleanup(lambda: self.c.portal.call(mc.drop_database, name))
        self.assertEqual(self.c.post("/api/parent/pin", json={"pin": "1234"}).json(), {"ok": True})

    def verify(self, pin):
        return self.c.post("/api/parent/verify", json={"pin": pin})

    def test_five_failures_lock_then_expire(self):
        for _ in range(4):
            self.assertEqual(self.verify("0000").json(), {"ok": False})
        r = self.verify("0000")
        self.assertEqual(r.status_code, 429)
        self.assertIn("dəqiqə", r.json()["detail"])
        self.assertEqual(r.headers.get("retry-after"), "300")
        # Locked: even the correct PIN is refused.
        self.assertEqual(self.verify("1234").status_code, 429)
        # Old-PIN change path is locked too (no bypass).
        self.assertEqual(self.c.post("/api/parent/pin", json={"pin": "5678", "old_pin": "1234"}).status_code, 429)
        self.offset = timedelta(seconds=301)
        self.assertEqual(self.verify("1234").json(), {"ok": True})

    def test_success_resets_counter(self):
        for _ in range(4):
            self.verify("0000")
        self.assertTrue(self.verify("1234").json()["ok"])
        for _ in range(4):
            self.assertEqual(self.verify("0000").status_code, 200)
        self.assertEqual(self.verify("0000").status_code, 429)

    def test_lock_fields_not_exposed_and_hash_hidden(self):
        for _ in range(5):
            self.verify("9999")
        st = self.c.get("/api/parent/pin-status").json()
        self.assertEqual(st, {"has_pin": True})
