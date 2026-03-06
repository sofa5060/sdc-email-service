import os
import html
import logging
from typing import Any, Dict, List, Optional
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr

app = FastAPI()
logger = logging.getLogger("sdc-email-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_FROM=os.environ.get("MAIL_FROM"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    MAIL_SERVER=os.environ.get("MAIL_SERVER"),
    MAIL_STARTTLS=os.environ.get("MAIL_STARTTLS", "True") == "True",
    MAIL_SSL_TLS=os.environ.get("MAIL_SSL_TLS", "False") == "True",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
fm = FastMail(conf)


def parse_min_score(value: Optional[str], default: float = 0.5) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        logger.warning(
            "invalid recaptcha min score value",
            extra={"event": "config_warning", "reason": "invalid_min_score"},
        )
        return default


RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "").strip()
RECAPTCHA_MIN_SCORE = parse_min_score(os.environ.get("RECAPTCHA_MIN_SCORE"), 0.5)
RECAPTCHA_EXPECTED_ACTION = "online_diagnosis_submit"


async def verify_recaptcha_token(
    token: str,
    expected_action: str,
    remote_ip: Optional[str] = None,
) -> Dict[str, Any]:
    if not RECAPTCHA_SECRET_KEY:
        return {"ok": False, "reason": "missing_secret"}

    payload = {"secret": RECAPTCHA_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data=payload,
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return {"ok": False, "reason": "verification_request_failed"}

    action = data.get("action")
    hostname = (data.get("hostname") or "").lower()
    score = float(data.get("score") or 0.0)
    success = bool(data.get("success"))

    if not success:
        return {
            "ok": False,
            "reason": "google_reported_failure",
            "score": score,
            "action": action,
            "hostname": hostname,
        }
    if action != expected_action:
        return {
            "ok": False,
            "reason": "action_mismatch",
            "score": score,
            "action": action,
            "hostname": hostname,
        }
    if score < RECAPTCHA_MIN_SCORE:
        return {
            "ok": False,
            "reason": "low_score",
            "score": score,
            "action": action,
            "hostname": hostname,
        }
    return {
        "ok": True,
        "reason": "passed",
        "score": score,
        "action": action,
        "hostname": hostname,
    }


@app.on_event("startup")
async def startup_event():
    print("--- STARTING EMAIL CONNECTION TEST ---")
    try:
        print(f"Configured for: {conf.MAIL_SERVER}:{conf.MAIL_PORT}")
    except Exception as e:
        print(f"!!! CONFIGURATION ERROR !!!: {e}")

@app.post("/send-inquiry")
async def send_inquiry(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    inquiry_type: str = Form(...),
    message: str = Form(""),
    recaptcha_token: str = Form(""),
    recaptcha_action: str = Form(""),
    files: Optional[List[UploadFile]] = File(None)
):
    print(f"Received request from {email}")

    if not recaptcha_token or not recaptcha_action:
        raise HTTPException(status_code=400, detail="Missing required captcha fields.")
    if recaptcha_action != RECAPTCHA_EXPECTED_ACTION:
        logger.info(
            "captcha rejected",
            extra={
                "event": "captcha_rejected",
                "reason": "action_not_expected",
                "action": recaptcha_action,
            },
        )
        raise HTTPException(status_code=403, detail="Request rejected.")

    remote_ip = request.client.host if request.client else None
    verification = await verify_recaptcha_token(
        token=recaptcha_token,
        expected_action=RECAPTCHA_EXPECTED_ACTION,
        remote_ip=remote_ip,
    )
    log_payload = {
        "event": "captcha_result",
        "ok": verification.get("ok"),
        "reason": verification.get("reason"),
        "score": verification.get("score"),
        "action": verification.get("action"),
        "hostname": verification.get("hostname"),
    }
    if verification.get("ok"):
        logger.info("captcha verified", extra=log_payload)
    else:
        logger.warning("captcha rejected", extra=log_payload)
        raise HTTPException(status_code=403, detail="Request could not be verified.")

    safe_name = html.escape(name)
    safe_phone = html.escape(phone)
    safe_email = html.escape(str(email))
    safe_inquiry_type = html.escape(inquiry_type)
    safe_message = html.escape(message).replace("\n", "<br>")

    message_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>New Inquiry</title>
    </head>
    <body style="margin:0;padding:0;background-color:#0b0a07;font-family:Segoe UI,Arial,sans-serif;color:#f3e7c2;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#0b0a07;padding:32px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#15120b;border-radius:16px;overflow:hidden;border:1px solid #6f5522;">
              <tr>
                <td style="background:linear-gradient(135deg,#3f2c0b,#b78a2f);padding:28px 32px;border-bottom:1px solid #d4af37;">
                  <h1 style="margin:0;font-size:24px;line-height:1.3;color:#fff4d6;font-weight:700;">New Patient Inquiry</h1>
                  <p style="margin:8px 0 0;font-size:14px;color:#f5deb1;">Studio Medical Center Contact Form Submission</p>
                </td>
              </tr>
              <tr>
                <td style="padding:28px 32px 8px;">
                  <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#ddc892;">
                    A new inquiry was submitted through the website. Details are below.
                  </p>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:separate;border-spacing:0 12px;">
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#c9a95b;vertical-align:top;">Full Name</td>
                      <td style="font-size:15px;color:#f5e6bf;background:#1d1810;border:1px solid #5f4a1d;border-radius:10px;padding:10px 12px;">{safe_name}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#c9a95b;vertical-align:top;">Phone Number</td>
                      <td style="font-size:15px;color:#f5e6bf;background:#1d1810;border:1px solid #5f4a1d;border-radius:10px;padding:10px 12px;">{safe_phone}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#c9a95b;vertical-align:top;">Email Address</td>
                      <td style="font-size:15px;color:#f5e6bf;background:#1d1810;border:1px solid #5f4a1d;border-radius:10px;padding:10px 12px;">{safe_email}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#c9a95b;vertical-align:top;">Inquiry Type</td>
                      <td style="font-size:15px;color:#fff2cc;background:#2a210f;border:1px solid #d4af37;border-radius:10px;padding:10px 12px;font-weight:700;">{safe_inquiry_type}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#c9a95b;vertical-align:top;">Message</td>
                      <td style="font-size:15px;line-height:1.7;color:#f5e6bf;background:#1d1810;border:1px solid #5f4a1d;border-radius:10px;padding:12px;">{safe_message}</td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 32px 28px;">
                  <div style="padding-top:14px;border-top:1px solid #5f4a1d;">
                    <p style="margin:0;font-size:12px;line-height:1.6;color:#aa8e52;">
                      This message was generated automatically by the Studio Medical Center inquiry service.
                    </p>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    message_object = MessageSchema(
        subject=f"New Inquiry from {name} - {inquiry_type}",
        recipients=[os.environ.get("MAIL_RECIPIENT")],
        body=message_body,
        subtype=MessageType.html,
        attachments=files or []
    )

    try:
        await fm.send_message(message_object)
        print("Email sent successfully!")
        return {"status": "Email sent successfully"}
    except Exception as e:
        print(f"!!! SENDING FAILED !!!: {e}")
        raise HTTPException(status_code=500, detail=str(e))
