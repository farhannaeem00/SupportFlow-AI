
import smtplib
from email.message import EmailMessage

from app.config import settings


def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """Send a plain-text email using the configured SMTP server."""

    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP configuration is incomplete.")

    if bool(settings.smtp_username) != bool(settings.smtp_password):
        raise RuntimeError(
            "SMTP username and password must both be configured."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=15,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        if settings.smtp_username:
            smtp.login(
                settings.smtp_username,
                settings.smtp_password,
            )

        smtp.send_message(message)


def send_password_reset_email(
    to_email: str,
    reset_url: str,
) -> None:
    """Send the existing password-reset email."""

    body = f"""Hello,

We received a request to reset your SupportFlow AI password.

Use the following link to choose a new password:

{reset_url}

This link expires in {settings.password_reset_token_expire_minutes} minutes.
It can only be used once.

If you did not request this reset, you can safely ignore this email.

SupportFlow AI
"""

    send_email(
        to_email=to_email,
        subject="Reset your SupportFlow AI password",
        body=body,
    )
