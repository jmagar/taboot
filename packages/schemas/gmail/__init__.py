"""Gmail entity schemas.

This module contains Pydantic schemas for Gmail entities:
- Email: Individual email messages
- Thread: Email conversation threads
- GmailLabel: Gmail labels (system or user-defined)
- Attachment: Email attachments

All entities include temporal tracking and extraction metadata.
"""

from packages.schemas.gmail.attachment import Attachment
from packages.schemas.gmail.email import Email
from packages.schemas.gmail.gmail_label import GmailLabel
from packages.schemas.gmail.thread import Thread

__all__ = [
    "Attachment",
    "Email",
    "GmailLabel",
    "Thread",
]
