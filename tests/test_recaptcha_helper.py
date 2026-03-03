import importlib
import os
import sys
import asyncio


def load_main_module():
    os.environ.setdefault("MAIL_USERNAME", "test-user")
    os.environ.setdefault("MAIL_PASSWORD", "test-pass")
    os.environ.setdefault("MAIL_FROM", "no-reply@example.com")
    os.environ.setdefault("MAIL_PORT", "587")
    os.environ.setdefault("MAIL_SERVER", "smtp.example.com")
    os.environ.setdefault("MAIL_RECIPIENT", "recipient@example.com")
    os.environ.setdefault("RECAPTCHA_SECRET_KEY", "test-secret")

    if "main" in sys.modules:
        return importlib.reload(sys.modules["main"])
    return importlib.import_module("main")


def test_verify_recaptcha_handles_network_error(monkeypatch):
    main = load_main_module()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise main.httpx.ReadTimeout("timeout")

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda *args, **kwargs: FakeClient())

    result = asyncio.run(
        main.verify_recaptcha_token(
            token="test-token",
            expected_action="online_diagnosis_submit",
            remote_ip="127.0.0.1",
        )
    )
    assert result["ok"] is False
    assert result["reason"] == "verification_request_failed"
