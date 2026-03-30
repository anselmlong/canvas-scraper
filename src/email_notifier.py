"""Email notifier for sending HTML reports via Gmail."""

import smtplib
import ssl
import logging
from pathlib import Path
from typing import Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends HTML email notifications via Gmail SMTP."""

    def __init__(self, config):
        """Initialize email notifier.

        Args:
            config: Config instance
        """
        self.config = config
        self.smtp_server = config.get("notification.email.smtp_server", "smtp.gmail.com")
        self.smtp_port = config.get("notification.email.smtp_port", 587)
        self.from_name = config.get("notification.email.from_name", "Canvas Scraper")
        self.recipient = config.get("notification.email.recipient")
        self.username = config.email_username
        self.password = config.email_password

        # Gmail/SMTP servers typically require a real email address in the
        # RFC5322 "From" header (a display name alone is invalid).
        self.from_address = config.get("notification.email.from_address", self.username)

        # Load Jinja2 template
        template_dir = self.config.internal_resource_dir / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = env.get_template("email_report.html")

        logger.info(
            "Initialized email notifier (recipient: %s, from: %s)",
            self.recipient,
            formataddr((self.from_name, self.from_address)),
        )

    def _create_smtp_connection(self, timeout: int = 30):
        """Create and return an authenticated-ready SMTP connection.

        Port 465 uses implicit TLS (SMTP_SSL), port 587 uses STARTTLS.
        Some networks/firewalls block STARTTLS upgrades, so port 465 is more reliable.
        """
        if self.smtp_port == 465:
            context = ssl.create_default_context()
            return smtplib.SMTP_SSL(
                self.smtp_server, self.smtp_port, timeout=timeout, context=context
            )
        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)
        server.starttls()
        return server

    def send_report(self, report_data: Dict[str, Any]) -> bool:
        """Send email report.

        Args:
            report_data: Report data dict from ReportGenerator

        Returns:
            True if successful, False otherwise
        """
        try:
            # Render HTML from template
            html_body = self.template.render(**report_data)

            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Canvas Scraper Report - {report_data['timestamp']}"
            msg["From"] = formataddr((self.from_name, self.from_address))
            msg["To"] = self.recipient

            # Attach HTML content
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            with self._create_smtp_connection(timeout=30) as server:
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {self.recipient}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("Email authentication failed. Check your credentials.")
            logger.error(
                "For Gmail, make sure you're using an App Password, not your regular password."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def test_connection(self) -> tuple[bool, str]:
        """Test email connection and credentials.

        Returns:
            Tuple of (success, message)
        """
        try:
            with self._create_smtp_connection(timeout=10) as server:
                server.login(self.username, self.password)

            return True, "Email connection successful"

        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check your email credentials."
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def send_test_email(self) -> bool:
        """Send a test email to verify configuration.

        Returns:
            True if successful, False otherwise
        """
        test_report = {
            "timestamp": "Test Run",
            "new_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "total_size_mb": "0.0",
            "new_files": {},
            "updated_files": {},
            "skipped_files": {},
            "failed_files": {},
            "new_courses": [],
            "next_run_time": "Next scheduled run",
            "announcement_count": 0,
            "assignment_count": 0,
            "new_announcements": {},
            "upcoming_assignments": {},
        }

        return self.send_report(test_report)
