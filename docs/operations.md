# Operations

## Daily Flow

1. Load `.env` and `config/topics.yml`.
2. Build RSS sources from topic queries and explicit feeds.
3. Fetch each source independently. A failed source is recorded as a warning and does not stop the whole run.
4. Deduplicate articles, keep the newest items, and generate one PDF per topic.
5. Write `manifest.json` and `summary.txt` under `output/daily/YYYY-MM-DD/`.
6. Send all PDFs to `NEWS_MAIL_TO` through Gmail API unless dry-run mode is enabled.
7. Remove old dated output directories based on `keep_days`.

## Files To Edit

- `config/topics.yml`: topics, search queries, feed URLs, output retention.
- `.env`: Gmail recipient/sender and OAuth file paths.
- `secrets/gmail_oauth_client.json`: Google Cloud Desktop OAuth client JSON. Never commit it.
- `data/gmail_token.json`: locally generated OAuth access/refresh token. Never commit it.
- `scripts/run_daily.sh`: automation entrypoint.
- `scripts/run_daily_and_push.sh`: automation entrypoint that mails the digest, commits generated PDFs, and pushes them.

## Failure Handling

- Source fetch failures are logged and included in the topic PDF.
- Missing mail settings fail the run before Gmail API delivery.
- Missing or invalid OAuth tokens fail with an instruction to run `python -m trend_news auth-gmail`.
- Generated output is kept even if email delivery fails, so the PDFs can be inspected and resent.
- Logs rotate at `logs/daily-news.log`.

## Gmail OAuth Setup

After downloading the Desktop OAuth client JSON from Google Cloud:

```bash
mkdir -p secrets
mv /path/to/downloaded-client.json secrets/gmail_oauth_client.json
cp .env.example .env
python -m trend_news auth-gmail
```

The authorization flow requests only `https://www.googleapis.com/auth/gmail.send`.
If the scope is changed later, remove `data/gmail_token.json` and run `auth-gmail` again.

## Codex Automation

Use this project directory as the automation workspace and run:

```text
Run ./scripts/run_daily.sh and report whether the daily news PDFs were generated and mailed successfully.
```

If generated PDFs should be pushed to GitHub after delivery, run:

```text
Run ./scripts/run_daily_and_push.sh and report whether the daily news PDFs were generated, mailed, committed, and pushed successfully.
```

Before activating the 8:00 automation, run this once:

```bash
./scripts/run_daily.sh
```

For a safe check without sending email:

```bash
NEWS_DRY_RUN=true ./scripts/run_daily.sh
```
