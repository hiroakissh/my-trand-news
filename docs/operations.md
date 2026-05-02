# Operations

## Daily Flow

1. Load `.env` and `config/topics.yml`.
2. Build RSS sources from topic queries and explicit feeds.
3. Fetch each source independently. A failed source is recorded as a warning and does not stop the whole run.
4. Deduplicate articles, keep the newest items, and generate one PDF per topic.
5. Write `manifest.json` and `summary.txt` under `output/daily/YYYY-MM-DD/`.
6. Send all PDFs to `NEWS_MAIL_TO` through Gmail SMTP unless dry-run mode is enabled.
7. Remove old dated output directories based on `keep_days`.

## Files To Edit

- `config/topics.yml`: topics, search queries, feed URLs, output retention.
- `.env`: Gmail recipient/sender and SMTP app password.
- `scripts/run_daily.sh`: automation entrypoint.

## Failure Handling

- Source fetch failures are logged and included in the topic PDF.
- Missing mail settings fail the run before SMTP login.
- Generated output is kept even if email delivery fails, so the PDFs can be inspected and resent.
- Logs rotate at `logs/daily-news.log`.

## Codex Automation

Use this project directory as the automation workspace and run:

```text
Run ./scripts/run_daily.sh and report whether the daily news PDFs were generated and mailed successfully.
```

Before activating the 8:00 automation, run this once:

```bash
./scripts/run_daily.sh
```

For a safe check without sending email:

```bash
NEWS_DRY_RUN=true ./scripts/run_daily.sh
```
