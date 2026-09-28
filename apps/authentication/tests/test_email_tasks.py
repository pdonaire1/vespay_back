import logging
from pathlib import Path
from unittest import mock

from celery.exceptions import Retry
from django.core import mail
from django.test import SimpleTestCase, override_settings

from apps.authentication import tasks


class VerificationOtpEmailTaskTests(SimpleTestCase):
    def test_delivers_email_with_code_and_subject(self):
        tasks.send_verification_otp_email("user@vespay.com", "123456")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["user@vespay.com"])
        self.assertEqual(message.subject, "Tu código de verificación VesPay")
        self.assertIn("123456", message.body)

    def test_includes_html_alternative_and_inline_logo(self):
        tasks.send_verification_otp_email("user@vespay.com", "123456")

        message = mail.outbox[0]
        self.assertEqual(message.mixed_subtype, "related")
        html = next(
            (body for body, mimetype in message.alternatives if mimetype == "text/html"), None
        )
        self.assertIsNotNone(html)
        self.assertIn("123456", html)
        self.assertIn("cid:vespay-logo", html)

        logo = next(
            (part for part in message.attachments if part.get_filename() == "vespay_logo_long.png"),
            None,
        )
        self.assertIsNotNone(logo)
        self.assertEqual(logo.get_content_type(), "image/png")
        self.assertEqual(logo["Content-ID"], "<vespay-logo>")

    @override_settings(EMAIL_LOGO_PATH=Path("/nonexistent/logo.png"))
    def test_falls_back_to_text_header_when_logo_missing(self):
        with self.assertLogs("apps.authentication.tasks", level=logging.WARNING):
            tasks.send_verification_otp_email("user@vespay.com", "123456")

        message = mail.outbox[0]
        self.assertEqual(message.attachments, [])
        html = next(
            (body for body, mimetype in message.alternatives if mimetype == "text/html"), None
        )
        self.assertNotIn("cid:vespay-logo", html)

    def test_retries_when_smtp_fails(self):
        with (
            mock.patch.object(tasks.EmailMultiAlternatives, "send", side_effect=Exception("smtp down")),
            mock.patch.object(
                tasks.send_verification_otp_email, "retry", side_effect=Retry()
            ) as retry,
            self.assertRaises(Retry),
        ):
            tasks.send_verification_otp_email.run("user@vespay.com", "123456")

        self.assertTrue(retry.called)


@override_settings(FRONTEND_URL="https://app.vespay.com/")
class PasswordResetEmailTaskTests(SimpleTestCase):
    def test_builds_reset_deep_link_in_body(self):
        tasks.send_password_reset_email("user@vespay.com", "654321")

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["user@vespay.com"])
        self.assertEqual(message.subject, "Restablece tu contraseña VesPay")
        self.assertIn("654321", message.body)
        self.assertIn(
            "https://app.vespay.com/#/auth/verify-otp?email=user@vespay.com&mode=reset&code=654321",
            message.body,
        )

    def test_retries_when_smtp_fails(self):
        with (
            mock.patch.object(tasks.EmailMultiAlternatives, "send", side_effect=Exception("smtp down")),
            mock.patch.object(
                tasks.send_password_reset_email, "retry", side_effect=Retry()
            ) as retry,
            self.assertRaises(Retry),
        ):
            tasks.send_password_reset_email.run("user@vespay.com", "654321")

        self.assertTrue(retry.called)
