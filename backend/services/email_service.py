import logging
import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("nexusdesk.service.email")

class EmailService:
    def __init__(self):

        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user)

        logger.info("DEBUG: SMTP_USER=%s, SMTP_PASS=%s", self.smtp_user, 'SET' if self.smtp_password else 'MISSING')

        self.real_mode = bool(self.smtp_user and self.smtp_password)

        if self.real_mode:
            logger.info("Email Service initialized in REAL MODE (%s)", self.smtp_server)
        else:
            logger.info("Email Service initialized in SIMULATION MODE (Set SMTP_USER and SMTP_PASSWORD to enable real emails)")

    async def send_status_update(self, user_email: str, ticket_id: str, ticket_title: str, new_status: str):

        subject = f"Update on your ticket: #{ticket_id[:8]}"

        status_messages = {
            "open": "has been successfully submitted and is in our queue.",
            "in_progress": "is now being processed by our AI Engine.",
            "escalated": "has been escalated to our human specialists for further review.",
            "resolved": "has been RESOLVED. You can view the resolution in your dashboard.",
            "failed": "could not be resolved automatically. A human agent will contact you soon.",
            "linked": "has been identified as a duplicate and linked to an existing incident.",
        }

        message = status_messages.get(new_status, f"status has changed to {new_status}.")

        body = f"""
        Hi there,

        This is an automated update regarding your support ticket:
        "{ticket_title}"

        Your ticket {message}

        Ticket ID: {ticket_id}
        Current Status: {new_status.upper()}

        You can track the live progress here: {os.getenv('APP_URL', 'http://localhost:5173/')}

        Thank you,
        NexusDesk AI Support Team
        """

        if self.real_mode:

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._send_smtp, user_email, subject, body)
        else:

            print(f"\n--- [SIMULATED EMAIL SENT] ---\nTo: {user_email}\nSubject: {subject}\n{body}\n------------------------------\n")

    def _send_smtp(self, to_email: str, subject: str, body: str):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            logger.info("REAL EMAIL SENT to %s", to_email)
        except Exception as e:
            logger.error("Failed to send real email: %s", str(e))

email_service = EmailService()