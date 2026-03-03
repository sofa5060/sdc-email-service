# SDC Email Service

FastAPI service for handling inquiry submissions and sending email notifications.

## Required Environment Variables

- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_PORT` (default: `587`)
- `MAIL_SERVER`
- `MAIL_RECIPIENT`
- `MAIL_STARTTLS` (default: `True`)
- `MAIL_SSL_TLS` (default: `False`)
- `RECAPTCHA_SECRET_KEY` (required for backend reCAPTCHA v3 verification)

## Optional reCAPTCHA Environment Variables

- `RECAPTCHA_ALLOWED_HOSTNAMES`
  - Comma-separated list of allowed hostnames from Google's verification response.
  - Example: `studio-medical-center.com,www.studio-medical-center.com`
- `RECAPTCHA_MIN_SCORE`
  - Minimum accepted score for reCAPTCHA v3.
  - Default: `0.5`

## Local Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set all required environment variables.

3. Run the API:

```bash
uvicorn main:app --reload
```

## Production Setup (Render)

Set the same environment variables in Render, especially:

- `RECAPTCHA_SECRET_KEY`
- Optional hardening:
  - `RECAPTCHA_ALLOWED_HOSTNAMES`
  - `RECAPTCHA_MIN_SCORE`

## Example cURL Request (`/send-inquiry`)

```bash
curl -X POST "https://sdc-email-service.onrender.com/send-inquiry" \
  -F "name=John Doe" \
  -F "phone=+15555550123" \
  -F "email=john@example.com" \
  -F "inquiry_type=online_diagnosis" \
  -F "message=I need a consultation" \
  -F "recaptcha_token=RECAPTCHA_TOKEN_FROM_CLIENT" \
  -F "recaptcha_action=online_diagnosis_submit" \
  -F "files=@./report.pdf"
```

## Tests

Run:

```bash
pytest -q
```
