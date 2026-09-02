import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
APP_NAME = os.getenv("APP_NAME", "ChatGPT Platform")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_password_reset_email(to_email: str, user_name: str, reset_token: str) -> bool:
    """
    Sends a password reset email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        # Log the reset link if email not configured (development mode)
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        logger.warning(
            f"[DEV MODE] Email not configured. Password reset link for {to_email}:\n{reset_link}"
        )
        print(f"\n{'='*60}")
        print(f"PASSWORD RESET LINK (Email not configured)")
        print(f"User: {to_email}")
        print(f"Link: {reset_link}")
        print(f"{'='*60}\n")
        return True  # Return True so the API doesn't fail in dev

    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Reset Your {APP_NAME} Password"
    msg["From"] = f"{APP_NAME} <{EMAIL_FROM}>"
    msg["To"] = to_email

    # Plain text fallback
    text_body = f"""Hi {user_name},

You requested a password reset for your {APP_NAME} account.

Click the link below to reset your password (expires in 1 hour):
{reset_link}

If you did not request this, you can safely ignore this email.

The {APP_NAME} Team
"""

    # HTML body
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#0f0f0f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f0f;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#1a1a1a;border-radius:12px;overflow:hidden;border:1px solid #333;">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#10b981,#3b82f6);padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#fff;font-size:24px;font-weight:700;">🔐 Password Reset</h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">{APP_NAME}</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <p style="margin:0 0 16px;color:#e5e7eb;font-size:16px;">Hi <strong style="color:#fff;">{user_name}</strong>,</p>
              <p style="margin:0 0 24px;color:#9ca3af;font-size:15px;line-height:1.6;">
                We received a request to reset the password for your {APP_NAME} account. 
                Click the button below to choose a new password.
              </p>
              <div style="text-align:center;margin:32px 0;">
                <a href="{reset_link}" 
                   style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#10b981,#3b82f6);color:#fff;text-decoration:none;border-radius:8px;font-size:16px;font-weight:600;letter-spacing:0.3px;">
                  Reset Password
                </a>
              </div>
              <p style="margin:0 0 8px;color:#6b7280;font-size:13px;">
                This link expires in <strong style="color:#f59e0b;">1 hour</strong>.
              </p>
              <p style="margin:0 0 24px;color:#6b7280;font-size:13px;">
                If you did not request a password reset, you can safely ignore this email.
              </p>
              <hr style="border:none;border-top:1px solid #333;margin:24px 0;">
              <p style="margin:0;color:#4b5563;font-size:12px;">
                Or copy this link into your browser:<br>
                <a href="{reset_link}" style="color:#3b82f6;word-break:break-all;">{reset_link}</a>
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background:#111;padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#4b5563;font-size:12px;">
                &copy; 2026 {APP_NAME}. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
        logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return False
