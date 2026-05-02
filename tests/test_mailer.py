from pathlib import Path

from trend_news.mailer import (
    GmailOAuthSettings,
    build_mime_message,
    encode_message,
    load_gmail_oauth_settings_from_env,
)


def test_load_gmail_oauth_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("NEWS_MAIL_FROM", "sender@example.com")
    monkeypatch.setenv("NEWS_MAIL_TO", "one@example.com, two@example.com")
    monkeypatch.setenv("GMAIL_OAUTH_CREDENTIALS_FILE", "secrets/client.json")
    monkeypatch.setenv("GMAIL_OAUTH_TOKEN_FILE", "data/token.json")

    settings = load_gmail_oauth_settings_from_env()

    assert settings.mail_from == "sender@example.com"
    assert settings.mail_to == ("one@example.com", "two@example.com")
    assert settings.credentials_file == Path("secrets/client.json")
    assert settings.token_file == Path("data/token.json")


def test_build_mime_message_with_pdf_attachment(tmp_path: Path) -> None:
    pdf_path = tmp_path / "news.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    settings = GmailOAuthSettings(
        credentials_file=Path("secrets/client.json"),
        token_file=Path("data/token.json"),
        mail_from="sender@example.com",
        mail_to=("receiver@example.com",),
    )

    message = build_mime_message(
        settings=settings,
        subject="Daily news",
        body="Attached.",
        attachments=(pdf_path,),
    )

    assert message["From"] == "sender@example.com"
    assert message["To"] == "receiver@example.com"
    assert message["Subject"] == "Daily news"
    assert any(part.get_filename() == "news.pdf" for part in message.walk())
    assert encode_message(message)
