import os
import asyncio
import html
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr

app = FastAPI()

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

@app.on_event("startup")
async def startup_event():
    print("--- STARTING EMAIL CONNECTION TEST ---")
    try:
        print(f"Configured for: {conf.MAIL_SERVER}:{conf.MAIL_PORT}")
    except Exception as e:
        print(f"!!! CONFIGURATION ERROR !!!: {e}")

@app.post("/send-inquiry")
async def send_inquiry(
    name: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    inquiry_type: str = Form(...),
    message: str = Form(...),
    files: List[UploadFile] = File(...)
):
    print(f"Received request from {email}")

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
    <body style="margin:0;padding:0;background-color:#f3f4f6;font-family:Segoe UI,Arial,sans-serif;color:#111827;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f3f4f6;padding:32px 12px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e5e7eb;">
              <tr>
                <td style="background:linear-gradient(135deg,#92400e,#f59e0b);padding:28px 32px;">
                  <h1 style="margin:0;font-size:24px;line-height:1.3;color:#ffffff;font-weight:700;">New Patient Inquiry</h1>
                  <p style="margin:8px 0 0;font-size:14px;color:#fef3c7;">Studio Medical Center Contact Form Submission</p>
                </td>
              </tr>
              <tr>
                <td style="padding:28px 32px 8px;">
                  <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#374151;">
                    A new inquiry was submitted through the website. Details are below.
                  </p>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:separate;border-spacing:0 12px;">
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#6b7280;vertical-align:top;">Full Name</td>
                      <td style="font-size:15px;color:#111827;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;">{safe_name}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#6b7280;vertical-align:top;">Phone Number</td>
                      <td style="font-size:15px;color:#111827;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;">{safe_phone}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#6b7280;vertical-align:top;">Email Address</td>
                      <td style="font-size:15px;color:#111827;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;">{safe_email}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#6b7280;vertical-align:top;">Inquiry Type</td>
                      <td style="font-size:15px;color:#111827;background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:10px 12px;font-weight:600;">{safe_inquiry_type}</td>
                    </tr>
                    <tr>
                      <td style="width:140px;font-size:13px;font-weight:600;color:#6b7280;vertical-align:top;">Message</td>
                      <td style="font-size:15px;line-height:1.7;color:#111827;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:12px;">{safe_message}</td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 32px 28px;">
                  <div style="padding-top:14px;border-top:1px solid #e5e7eb;">
                    <p style="margin:0;font-size:12px;line-height:1.6;color:#9ca3af;">
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
        attachments=files
    )

    fm = FastMail(conf)

    try:
        await fm.send_message(message_object)
        print("Email sent successfully!")
        return {"status": "Email sent successfully"}
    except Exception as e:
        print(f"!!! SENDING FAILED !!!: {e}")
        raise HTTPException(status_code=500, detail=str(e))
