# Optional email. send_email() does nothing unless SMTP_HOST is set, and never raises: a mail problem must not stop a ticket from being saved.

import logging
import smtplib
import textwrap
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host or not to:
        return False
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if server.has_extn("starttls"):  # encrypt when the server offers it (most providers do; a plain local relay may not)
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return True
    except Exception:  # noqa: BLE001 - any mail failure is logged and swallowed on purpose
        log.warning("email to %s failed", to, exc_info=True)
        return False


# ---- notices to the citizen who asked for updates (FR-11) ----
# the text holds only the reference code and the status: no description, no location, no contractor, nothing another person could use
_NOTICES = {
    "received": ("We received your report {code}", "Thank you. We received your water report with the reference code {code}. We will email you when the authority looks at it and when it is resolved."),
    "in_review": ("Your report {code} is being looked at", "The authority is now looking at your report {code}."),
    "resolved": ("Your report {code} is resolved", "Your report {code} has been resolved. If the problem comes back, please report it again."),
}


def notify_citizen(email: str | None, code: str, event: str) -> bool:
    if not email or event not in _NOTICES:
        return False
    subject, body = _NOTICES[event]
    footer = (
        f"\n\nYou can check the status any time at {settings.frontend_url}/reports with your code.\n"
        "You get this email because you asked for updates when you reported a water problem on HydroSentinel. We use your address only for updates about this report."
    )
    text = "\n\n".join(textwrap.fill(part, 70) if part else "" for part in (body.format(code=code) + footer).split("\n\n"))   # short lines, so the mail stays plain and readable
    return send_email(email, subject.format(code=code), text)
