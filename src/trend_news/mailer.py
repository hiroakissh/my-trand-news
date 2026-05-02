from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from .models import DailyDigest


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    mail_from: str
    mail_to: tuple[str, ...]


def load_smtp_settings_from_env() -> SmtpSettings:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USER") or os.getenv("NEWS_MAIL_FROM") or ""
    password = os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD") or ""
    mail_from = os.getenv("NEWS_MAIL_FROM") or username
    mail_to = tuple(
        address.strip()
        for address in os.getenv("NEWS_MAIL_TO", "").split(",")
        if address.strip()
    )

    missing = []
    if not username:
        missing.append("SMTP_USER or NEWS_MAIL_FROM")
    if not password:
        missing.append("SMTP_PASSWORD")
    if not mail_from:
        missing.append("NEWS_MAIL_FROM")
    if not mail_to:
        missing.append("NEWS_MAIL_TO")
    if missing:
        raise RuntimeError(f"Missing mail settings: {', '.join(missing)}")

    return SmtpSettings(
        host=host,
        port=port,
        username=username,
        password=password,
        mail_from=mail_from,
        mail_to=mail_to,
    )


def build_email_body(digest: DailyDigest) -> str:
    lines = [
        f"{digest.run_date.isoformat()} のニュースPDFを作成しました。",
        "",
        f"保存先: {digest.output_dir}",
        f"総件数: {digest.total_items}",
        "",
    ]
    for topic in digest.topics:
        lines.append(f"- {topic.topic.title}: {len(topic.items)}件")
        if topic.errors:
            lines.append(f"  取得警告: {len(topic.errors)}件")
    lines.extend(["", "添付PDFを確認してください。"])
    return "\n".join(lines)


def send_digest_email(
    *,
    settings: SmtpSettings,
    subject: str,
    body: str,
    attachments: tuple[Path, ...],
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.mail_from
    message["To"] = ", ".join(settings.mail_to)
    message.set_content(body)

    for attachment in attachments:
        message.add_attachment(
            attachment.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=attachment.name,
        )

    with smtplib.SMTP(settings.host, settings.port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)
