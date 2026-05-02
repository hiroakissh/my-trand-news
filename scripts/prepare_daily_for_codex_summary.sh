#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

RUN_DATE="${1:-}"
if [[ -z "$RUN_DATE" ]]; then
  RUN_DATE="$(python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from trend_news.config import load_config

config = load_config("config/topics.yml")
print(datetime.now(ZoneInfo(config.timezone)).date().isoformat())
PY
)"
fi

python -m trend_news run --config config/topics.yml --date "$RUN_DATE" --no-email

echo "RUN_DATE=$RUN_DATE"
echo "MANIFEST=output/daily/$RUN_DATE/manifest.json"
echo "SUMMARY_JSON=output/daily/$RUN_DATE/codex_summary.json"
