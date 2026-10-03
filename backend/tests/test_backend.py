"""Backend regression tests for Ağıllı Dərs."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://student-helper-pro-4.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def test_root():
    r = requests.get(f"{API}/", timeout=30)
    assert r.status_code == 200
    assert "hazırdır" in r.json().get("message", "")


def test_subjects_returns_10():
    r = requests.get(f"{API}/subjects", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 10
    ids = {s["id"] for s in data}
    assert "informatika" in ids


def test_tts_speechprep_fractions_percent():
    r = requests.post(f"{API}/tts", json={"text": "3/4 və 25%", "lang": "az", "speed": 1.0, "voice": "coral"}, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/mpeg")
    assert len(r.content) > 500


def test_tts_voice_nova_ok():
    r = requests.post(f"{API}/tts", json={"text": "Salam", "lang": "az", "speed": 1.0, "voice": "nova"}, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/mpeg")


def test_tts_invalid_voice_falls_back():
    r = requests.post(f"{API}/tts", json={"text": "Salam", "lang": "az", "speed": 1.0, "voice": "bogus"}, timeout=60)
    assert r.status_code == 200


def test_tts_empty_text_400():
    r = requests.post(f"{API}/tts", json={"text": "   ", "lang": "az", "speed": 1.0, "voice": "coral"}, timeout=30)
    assert r.status_code == 400


def test_chat_sse_general():
    body = {"message": "Salam, sən kimsən?", "lang": "az"}
    r = requests.post(f"{API}/chat", json=body, stream=True, timeout=90)
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    saw_delta = False
    saw_done = False
    for raw in r.iter_lines(decode_unicode=True):
        if not raw:
            continue
        if raw.startswith("data: "):
            payload = raw[6:]
            if '"delta"' in payload:
                saw_delta = True
            if '"done"' in payload:
                saw_done = True
                break
    assert saw_delta
    assert saw_done


def test_messages_endpoint():
    r = requests.get(f"{API}/messages", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_progress_endpoint():
    r = requests.get(f"{API}/progress", timeout=30)
    assert r.status_code == 200
    assert "total_questions" in r.json()


def test_books_endpoint():
    r = requests.get(f"{API}/books", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
