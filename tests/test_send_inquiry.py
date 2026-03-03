import importlib
import os
import sys

from fastapi.testclient import TestClient


def load_main_module():
    os.environ.setdefault("MAIL_USERNAME", "test-user")
    os.environ.setdefault("MAIL_PASSWORD", "test-pass")
    os.environ.setdefault("MAIL_FROM", "no-reply@example.com")
    os.environ.setdefault("MAIL_PORT", "587")
    os.environ.setdefault("MAIL_SERVER", "smtp.example.com")
    os.environ.setdefault("MAIL_RECIPIENT", "recipient@example.com")
    os.environ.setdefault("RECAPTCHA_SECRET_KEY", "test-secret")
    os.environ.setdefault("RECAPTCHA_ALLOWED_HOSTNAMES", "localhost")
    os.environ.setdefault("RECAPTCHA_MIN_SCORE", "0.5")

    if "main" in sys.modules:
        return importlib.reload(sys.modules["main"])
    return importlib.import_module("main")


def make_payload():
    return {
        "name": "John Doe",
        "phone": "+15555550123",
        "email": "john@example.com",
        "inquiry_type": "online_diagnosis",
        "message": "Need an appointment",
        "recaptcha_token": "token123",
        "recaptcha_action": "online_diagnosis_submit",
    }


def make_file():
    return {"files": ("report.txt", b"test file", "text/plain")}


def test_valid_captcha_sends_email(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_verify(*args, **kwargs):
        return {
            "ok": True,
            "reason": "passed",
            "score": 0.9,
            "action": "online_diagnosis_submit",
            "hostname": "localhost",
        }

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main, "verify_recaptcha_token", fake_verify)
    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=make_payload(), files=make_file())

    assert response.status_code == 200
    assert sent["count"] == 1


def test_missing_token_returns_400(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    payload = make_payload()
    payload["recaptcha_token"] = ""
    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=payload, files=make_file())

    assert response.status_code == 400
    assert sent["count"] == 0


def test_invalid_captcha_returns_403(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_verify(*args, **kwargs):
        return {
            "ok": False,
            "reason": "google_reported_failure",
            "score": 0.9,
            "action": "online_diagnosis_submit",
            "hostname": "localhost",
        }

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main, "verify_recaptcha_token", fake_verify)
    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=make_payload(), files=make_file())

    assert response.status_code == 403
    assert sent["count"] == 0


def test_wrong_action_returns_403(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    payload = make_payload()
    payload["recaptcha_action"] = "different_action"
    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=payload, files=make_file())

    assert response.status_code == 403
    assert sent["count"] == 0


def test_low_score_returns_403(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_verify(*args, **kwargs):
        return {
            "ok": False,
            "reason": "low_score",
            "score": 0.1,
            "action": "online_diagnosis_submit",
            "hostname": "localhost",
        }

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main, "verify_recaptcha_token", fake_verify)
    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=make_payload(), files=make_file())

    assert response.status_code == 403
    assert sent["count"] == 0


def test_google_verification_error_returns_403(monkeypatch):
    main = load_main_module()
    sent = {"count": 0}

    async def fake_verify(*args, **kwargs):
        return {
            "ok": False,
            "reason": "verification_request_failed",
            "score": None,
            "action": None,
            "hostname": None,
        }

    async def fake_send_message(message):
        sent["count"] += 1

    monkeypatch.setattr(main, "verify_recaptcha_token", fake_verify)
    monkeypatch.setattr(main.fm, "send_message", fake_send_message)

    client = TestClient(main.app)
    response = client.post("/send-inquiry", data=make_payload(), files=make_file())

    assert response.status_code == 403
    assert sent["count"] == 0
