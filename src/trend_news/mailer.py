from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .models import DailyDigest


GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SCOPES = (GMAIL_SEND_SCOPE,)


@dataclass(frozen=True)
class GmailOAuthSettings:
    credentials_file: Path
    token_file: Path
    mail_from: str
    mail_to: tuple[str, ...]


def load_gmail_oauth_settings_from_env(*, require_mail: bool = True) -> GmailOAuthSettings:
    credentials_file = Path(
        os.getenv("GMAIL_OAUTH_CREDENTIALS_FILE")
        or os.getenv("GMAIL_CREDENTIALS_FILE")
        or "secrets/gmail_oauth_client.json"
    )
    token_file = Path(
        os.getenv("GMAIL_OAUTH_TOKEN_FILE")
        or os.getenv("GMAIL_TOKEN_FILE")
        or "data/gmail_token.json"
    )
    mail_from = os.getenv("NEWS_MAIL_FROM", "").strip()
    mail_to = tuple(
        address.strip()
        for address in os.getenv("NEWS_MAIL_TO", "").split(",")
        if address.strip()
    )

    missing = []
    if require_mail and not mail_from:
        missing.append("NEWS_MAIL_FROM")
    if require_mail and not mail_to:
        missing.append("NEWS_MAIL_TO")
    if missing:
        raise RuntimeError(f"Missing mail settings: {', '.join(missing)}")

    return GmailOAuthSettings(
        credentials_file=credentials_file,
        token_file=token_file,
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
    settings: GmailOAuthSettings,
    subject: str,
    body: str,
    attachments: tuple[Path, ...],
) -> str:
    credentials = load_gmail_credentials(settings, interactive=False)
    message = build_mime_message(
        settings=settings,
        subject=subject,
        body=body,
        attachments=attachments,
    )
    raw_message = encode_message(message)

    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    response = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw_message})
        .execute()
    )
    return str(response.get("id", ""))


def authorize_gmail(settings: GmailOAuthSettings) -> Path:
    load_gmail_credentials(settings, interactive=True)
    return settings.token_file


def load_gmail_credentials(
    settings: GmailOAuthSettings,
    *,
    interactive: bool,
) -> Credentials:
    credentials = None
    if settings.token_file.exists():
        credentials = Credentials.from_authorized_user_file(
            str(settings.token_file),
            list(GMAIL_SCOPES),
        )

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            if not interactive:
                raise RuntimeError(
                    "Gmail OAuth token could not be refreshed. "
                    "Run `python -m trend_news auth-gmail` again."
                ) from exc
        else:
            _write_credentials(settings.token_file, credentials)
            return credentials

    if not interactive:
        raise RuntimeError(
            "Gmail OAuth token is missing or invalid. "
            "Run `python -m trend_news auth-gmail` once before scheduled runs."
        )

    if not settings.credentials_file.exists():
        raise RuntimeError(
            "Gmail OAuth client file is missing: "
            f"{settings.credentials_file}. Download a Desktop OAuth client JSON "
            "from Google Cloud and set GMAIL_OAUTH_CREDENTIALS_FILE if needed."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.credentials_file),
        list(GMAIL_SCOPES),
    )
    credentials = flow.run_local_server(port=0)
    _write_credentials(settings.token_file, credentials)
    return credentials


def build_mime_message(
    *,
    settings: GmailOAuthSettings,
    subject: str,
    body: str,
    attachments: tuple[Path, ...],
) -> EmailMessage:
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

    return message


def encode_message(message: EmailMessage) -> str:
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def _write_credentials(path: Path, credentials: Credentials) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")
