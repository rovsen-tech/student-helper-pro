"""Backend API tests for Ağıllı Dərs iteration 2 (subjects + lesson chat)."""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://student-helper-pro-4.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

EXPECTED_SUBJECT_IDS = {"azdili","riyaziyyat","tebiet","informatika","ingilis","tarix","musiqi","tesviri","texnologiya","fiziki"}


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Subjects endpoint ---
def test_root(sess):
    r = sess.get(f"{API}/")
    assert r.status_code == 200


def test_subjects_returns_10(sess):
    r = sess.get(f"{API}/subjects")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 10
    ids = {s["id"] for s in data}
    assert ids == EXPECTED_SUBJECT_IDS
    for s in data:
        for k in ("id", "name", "icon", "color", "description", "topics"):
            assert k in s, f"missing key {k} in subject {s.get('id')}"
        assert isinstance(s["topics"], list) and len(s["topics"]) >= 3


def test_subjects_riyaziyyat_has_adi_kesrler(sess):
    r = sess.get(f"{API}/subjects")
    riy = next(s for s in r.json() if s["id"] == "riyaziyyat")
    assert riy["name"] == "Riyaziyyat"
    assert "Adi kəsrlər" in riy["topics"]


# --- Chat SSE (lesson explain) ---
def _consume_sse(resp, max_seconds=45):
    deltas = []
    done = False
    start = time.time()
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        if not raw:
            continue
        if raw.startswith("data:"):
            payload = raw[len("data:"):].strip()
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            if "delta" in obj:
                deltas.append(obj["delta"])
            if obj.get("done"):
                done = True
                break
        if time.time() - start > max_seconds:
            break
    return "".join(deltas), done


def test_chat_lesson_explain_streams_and_persists(sess):
    payload = {"subject": "Riyaziyyat", "topic": "Adi kəsrlər", "lang": "az", "explain": True}
    with sess.post(f"{API}/chat", json=payload, stream=True, timeout=60) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        full, done = _consume_sse(r)
    assert done is True, "Stream did not end with done:true"
    assert len(full) > 40, f"Explanation too short: {full!r}"

    # small delay for DB write
    time.sleep(1.5)
    r2 = sess.get(f"{API}/messages", params={"subject": "Riyaziyyat", "topic": "Adi kəsrlər"})
    assert r2.status_code == 200
    hist = r2.json()
    assert len(hist) >= 1
    assert any(m["role"] == "assistant" and m["content"] for m in hist)


def test_chat_lesson_followup_question(sess):
    payload = {"subject": "Riyaziyyat", "topic": "Adi kəsrlər", "message": "Bir nümunə ver", "lang": "az"}
    with sess.post(f"{API}/chat", json=payload, stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 10
    time.sleep(1.5)
    r2 = sess.get(f"{API}/messages", params={"subject": "Riyaziyyat", "topic": "Adi kəsrlər"})
    roles = [m["role"] for m in r2.json()]
    assert "user" in roles and "assistant" in roles


def test_chat_general_no_subject(sess):
    payload = {"message": "Salam", "lang": "az"}
    with sess.post(f"{API}/chat", json=payload, stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 3
    r2 = sess.get(f"{API}/messages")
    assert r2.status_code == 200
    assert isinstance(r2.json(), list)


# --- TTS ---
def test_tts_audio_mpeg(sess):
    r = sess.post(f"{API}/tts", json={"text": "Salam dünya", "lang": "az", "speed": 1.0}, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type") == "audio/mpeg"
    assert len(r.content) > 500


def test_tts_empty_returns_400(sess):
    r = sess.post(f"{API}/tts", json={"text": "   ", "lang": "az"}, timeout=30)
    assert r.status_code == 400


# --- Books endpoint (no seed books expected) ---
def test_books_list(sess):
    r = sess.get(f"{API}/books")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_book_not_found(sess):
    r = sess.get(f"{API}/books/nonexistent-id-xyz")
    assert r.status_code == 404


# --- Iter3: lesson stage machine (recall, quiz_next, quiz_answer) + progress + sha256 session_key consistency ---
def test_lesson_stage_machine_and_sha256_session(sess):
    subject, topic = "Riyaziyyat", "Onluq kəsrlər"

    # 1. explain - resets and streams
    with sess.post(f"{API}/chat", json={"subject": subject, "topic": topic, "lang": "az", "explain": True}, stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 20

    # 2. recall
    time.sleep(1)
    with sess.post(f"{API}/chat", json={"subject": subject, "topic": topic, "lang": "az",
                                        "stage": "recall", "message": "Onluq kəsrlər verguldan sonra gələn ədədlərdir."},
                   stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 10

    # 3. quiz_next
    time.sleep(1)
    with sess.post(f"{API}/chat", json={"subject": subject, "topic": topic, "lang": "az", "stage": "quiz_next"},
                   stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 5

    # 4. quiz_answer
    time.sleep(1)
    with sess.post(f"{API}/chat", json={"subject": subject, "topic": topic, "lang": "az",
                                        "stage": "quiz_answer", "message": "0.5"},
                   stream=True, timeout=60) as r:
        assert r.status_code == 200
        full, done = _consume_sse(r)
    assert done and len(full) > 5

    # 5. GET /messages must return the persisted lesson history under the SAME sha256 session_key
    time.sleep(1.5)
    r2 = sess.get(f"{API}/messages", params={"subject": subject, "topic": topic})
    assert r2.status_code == 200
    hist = r2.json()
    roles = [m["role"] for m in hist]
    contents = [m["content"] for m in hist]
    # At least one user (recall or quiz_answer) and multiple assistant messages
    assert "user" in roles and "assistant" in roles
    assert any("Onluq kəsrlər verguldan" in c for c in contents), "recall user msg not persisted"
    assert any("0.5" == c for c in contents), "quiz_answer user msg not persisted"


def test_progress_aggregation(sess):
    r = sess.get(f"{API}/progress")
    assert r.status_code == 200
    data = r.json()
    for k in ("total_questions", "subjects_studied", "lessons_started", "by_subject"):
        assert k in data
    assert isinstance(data["by_subject"], list)
    # after prior tests we should have Riyaziyyat studied
    subjects = {b["subject"] for b in data["by_subject"]}
    assert "Riyaziyyat" in subjects
    assert data["lessons_started"] >= 1
