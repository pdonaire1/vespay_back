import logging
import mimetypes
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from celery import shared_task

logger = logging.getLogger(__name__)

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "max_retries": 3,
    "ignore_result": True,
}


def _logo_available() -> bool:
    return Path(settings.EMAIL_LOGO_PATH).is_file()


def _send_html_email(subject, to, text_message, html_message, cid=None):
    message = EmailMultiAlternatives(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [to],
    )
    message.attach_alternative(html_message, "text/html")

    if _logo_available():
        if cid:
            logo_path = Path(settings.EMAIL_LOGO_PATH)
            mime_type, _ = mimetypes.guess_type(str(logo_path))
            image = MIMEImage(
                logo_path.read_bytes(), _subtype=(mime_type or "image/png").split("/")[-1]
            )
            image.add_header("Content-ID", f"<{cid}>")
            image.add_header("Content-Disposition", "inline", filename=logo_path.name)
            message.attach(image)
            message.mixed_subtype = "related"
    else:
        logger.warning(
            "Email logo not found at %s; sending text header fallback.",
            settings.EMAIL_LOGO_PATH,
        )

    message.send(fail_silently=False)


@shared_task(**_RETRY_KWARGS)
def send_verification_otp_email(email: str, code: str) -> None:
    logo_cid = settings.EMAIL_LOGO_CID if _logo_available() else None
    context = {"otp_code": code, "email": email, "logo_cid": logo_cid}
    subject = "Tu código de verificación VesPay"
    text_message = render_to_string("emails/otp_code.txt", context)
    html_message = render_to_string("emails/otp_code.html", context)
    _send_html_email(subject, email, text_message, html_message, logo_cid)


@shared_task(**_RETRY_KWARGS)
def send_password_reset_email(email: str, code: str) -> None:
    reset_link = (
        f"{settings.FRONTEND_URL.rstrip('/')}/#/auth/verify-otp"
        f"?email={email}&mode=reset&code={code}"
    )
    logo_cid = settings.EMAIL_LOGO_CID if _logo_available() else None
    context = {
        "otp_code": code,
        "email": email,
        "reset_link": reset_link,
        "logo_cid": logo_cid,
    }
    subject = "Restablece tu contraseña VesPay"
    text_message = render_to_string("emails/password_reset_code.txt", context)
    html_message = render_to_string("emails/password_reset_code.html", context)
    _send_html_email(subject, email, text_message, html_message, logo_cid)
