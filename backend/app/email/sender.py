"""Email delivery adapters. Message bodies are not written to application logs."""

import smtplib
import uuid
from dataclasses import dataclass
from email.message import EmailMessage as MimeEmail
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Deliver one message."""


class FileEmailSender:
    """Development mailbox. Files live under a gitignored directory."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def send(self, message: EmailMessage) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{uuid.uuid4()}.txt"
        contents = f"To: {message.to}\nSubject: {message.subject}\n\n{message.body}\n"
        path.write_text(contents, encoding="utf-8")


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        mime = MimeEmail()
        mime["Subject"] = message.subject
        mime["From"] = self._settings.smtp_from
        mime["To"] = message.to
        mime.set_content(message.body)
        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=10) as smtp:
            if self._settings.smtp_use_tls:
                smtp.starttls()
            if self._settings.smtp_user:
                smtp.login(self._settings.smtp_user, self._settings.smtp_password)
            smtp.send_message(mime)


class InMemoryEmailSender:
    """Test double that keeps messages in process memory."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()


_memory_sender = InMemoryEmailSender()


def get_memory_sender() -> InMemoryEmailSender:
    return _memory_sender


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_backend == "memory":
        return _memory_sender
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    return FileEmailSender(Path(settings.email_outbox_dir))
