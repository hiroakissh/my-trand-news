from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .config import load_config
from .feeds import collect_topic_digests
from .logging_config import setup_logging
from .mailer import (
    authorize_gmail,
    build_email_body,
    load_gmail_oauth_settings_from_env,
    send_digest_email,
)
from .models import DailyDigest
from .pdf import generate_topic_pdf
from .storage import cleanup_old_runs, prepare_run_dir, safe_filename, write_manifest, write_summary


LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return run(args)
        if args.command == "auth-gmail":
            return auth_gmail(args)
    except RuntimeError as exc:
        if logging.getLogger().handlers:
            LOGGER.error("%s", exc)
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trend-news")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Generate PDFs and send the digest email.")
    run_parser.add_argument("--config", default="config/topics.yml", help="Path to YAML config.")
    run_parser.add_argument("--date", help="Run date as YYYY-MM-DD. Defaults to today.")
    run_parser.add_argument("--dry-run", action="store_true", help="Generate files but do not email.")
    run_parser.add_argument("--no-email", action="store_true", help="Generate files without email.")
    run_parser.add_argument(
        "--log-level",
        default=os.getenv("NEWS_LOG_LEVEL", "INFO"),
        help="Python logging level.",
    )

    auth_parser = subparsers.add_parser(
        "auth-gmail",
        help="Create or refresh the Gmail OAuth token for scheduled sends.",
    )
    auth_parser.add_argument(
        "--log-level",
        default=os.getenv("NEWS_LOG_LEVEL", "INFO"),
        help="Python logging level.",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    setup_logging(args.log_level)

    config = load_config(args.config)
    zone = ZoneInfo(config.timezone)
    now = datetime.now(zone)
    run_date = date.fromisoformat(args.date) if args.date else now.date()
    run_dir = prepare_run_dir(config.output_dir, run_date.isoformat())

    LOGGER.info("Starting daily news run for %s", run_date.isoformat())
    topic_digests = collect_topic_digests(config, now)
    digest = DailyDigest(
        run_date=run_date,
        generated_at=now,
        topics=topic_digests,
        output_dir=run_dir,
    )

    pdf_paths: list[Path] = []
    for topic_digest in digest.topics:
        filename = f"{safe_filename(topic_digest.topic.id)}.pdf"
        pdf_paths.append(generate_topic_pdf(topic_digest, run_dir / filename, now))

    manifest_path = write_manifest(digest)
    summary_path = write_summary(digest)
    cleanup_old_runs(config.output_dir, config.keep_days, now)

    LOGGER.info("Wrote %s PDFs to %s", len(pdf_paths), run_dir)
    LOGGER.info("Wrote manifest: %s", manifest_path)
    LOGGER.info("Wrote summary: %s", summary_path)

    dry_run = args.dry_run or _env_flag("NEWS_DRY_RUN") or args.no_email
    if dry_run:
        LOGGER.info("Dry run enabled; skipping email delivery.")
        return 0

    settings = load_gmail_oauth_settings_from_env()
    subject = f"{config.mail.subject_prefix} {run_date.isoformat()}"
    message_id = send_digest_email(
        settings=settings,
        subject=subject,
        body=build_email_body(digest),
        attachments=tuple(pdf_paths),
    )
    LOGGER.info(
        "Sent digest email to %s via Gmail API message_id=%s",
        ", ".join(settings.mail_to),
        message_id,
    )
    return 0


def auth_gmail(args: argparse.Namespace) -> int:
    load_dotenv()
    setup_logging(args.log_level)
    settings = load_gmail_oauth_settings_from_env(require_mail=False)
    token_path = authorize_gmail(settings)
    LOGGER.info("Gmail OAuth token saved to %s", token_path)
    return 0


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
