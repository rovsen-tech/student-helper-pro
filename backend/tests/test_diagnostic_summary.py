# Tests: subjects lesson_count, diagnostic-stage chat flow, lesson summary create/list (iteration 7)
import os
import json
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def read_sse(resp):
    full, err = "", False
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            obj = json.loads(line[6:])
        except Exception:
            continue
        if obj.get("delta"):
            full += obj["delta"]
        if obj.get("error"):
            err = True
    return full, err


@pytest.fixture(scope="module")
def student():
    r = requests.post(f"{API}/students", json={"name": f"TEST_diag_{uuid.uuid4().hex[:6]}"})
    assert r.status_code in (200, 201), r.text
    sid = r.json()["id"]
    s = requests.Session()
    s.headers.update({"X-Student-Id": sid, "Content-Type": "application/json"})
    yield s, sid
    try:
        requests.delete(f"{API}/students/{sid}")
    except Exception:
        pass


# Subjects: real lesson count
class TestSubjects:
    def test_riyaziyyat_lesson_count_39(self):
        r = requests.get(f"{API}/subjects")
        assert r.status_code == 200
        data = r.json()
        assert all("lesson_count" in s for s in data)
        riy = [s for s in data if s["name"].lower().startswith("riyaz") or s["id"] in ("math", "riyaziyyat")]
        assert riy, [s["id"] for s in data]
        assert riy[0]["lesson_count"] == 39

    def test_other_subjects_fallback_topic_count(self):
        data = requests.get(f"{API}/subjects").json()
        for s in data:
            if s["lesson_count"] != 39:
                assert s["lesson_count"] == len(s["topics"]), s["id"]


# Diagnostic -> explain -> summary flow
class TestDiagnosticAndSummary:
    SUBJECT = "Riyaziyyat"
    TOPIC = "TEST_Kəsrlərin toplanması"

    def test_summaries_empty_initially(self, student):
        s, _ = student
        r = s.get(f"{API}/lesson-summaries")
        assert r.status_code == 200
        assert r.json() == []

    def test_explain_returns_diagnostic_question(self, student):
        s, _ = student
        r = s.post(f"{API}/chat", json={"subject": self.SUBJECT, "topic": self.TOPIC, "lang": "az", "explain": True},
                   stream=True, timeout=120)
        assert r.status_code == 200
        full, err = read_sse(r)
        assert not err and full.strip()
        assert "?" in full  # diagnostic question
        msgs = s.get(f"{API}/messages", params={"subject": self.SUBJECT, "topic": self.TOPIC}).json()
        assert len(msgs) == 1 and msgs[0]["role"] == "assistant"

    def test_diagnostic_answer_then_explain(self, student):
        s, _ = student
        r = s.post(f"{API}/chat", json={"subject": self.SUBJECT, "topic": self.TOPIC, "lang": "az",
                                        "message": "Bilmirəm"}, stream=True, timeout=120)
        assert r.status_code == 200
        full, err = read_sse(r)
        assert not err and len(full.strip()) > 50
        msgs = s.get(f"{API}/messages", params={"subject": self.SUBJECT, "topic": self.TOPIC}).json()
        assert [m["role"] for m in msgs] == ["assistant", "user", "assistant"]

    def test_create_summary_and_list(self, student):
        s, sid = student
        r = s.post(f"{API}/lesson-summary", json={"subject": self.SUBJECT, "topic": self.TOPIC, "lang": "az"},
                   timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "_id" not in d
        assert d["subject"] == self.SUBJECT and d["topic"] == self.TOPIC and d["student_id"] == sid
        assert isinstance(d["summary"], str) and len(d["summary"]) > 20
        print("SUMMARY:", d["summary"])
        lst = s.get(f"{API}/lesson-summaries").json()
        assert lst and lst[0]["id"] == d["id"]
        assert "_id" not in lst[0]

    def test_summaries_isolated_per_student(self):
        r = requests.get(f"{API}/lesson-summaries", headers={"X-Student-Id": f"nonexist-{uuid.uuid4().hex[:6]}"})
        assert r.status_code in (200, 400, 404)
        if r.status_code == 200:
            assert all(x["topic"] != self.TOPIC for x in r.json())

    def test_summary_validation(self, student):
        s, _ = student
        r = s.post(f"{API}/lesson-summary", json={"subject": "", "topic": "x"})
        assert r.status_code == 422
