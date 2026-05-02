#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

RUN_DATE="$(python - <<'PY'
from datetime import datetime
from zoneinfo import ZoneInfo

from trend_news.config import load_config

config = load_config("config/topics.yml")
print(datetime.now(ZoneInfo(config.timezone)).date().isoformat())
PY
)"

python -m trend_news run --config config/topics.yml --date "$RUN_DATE"

RUN_DIR="output/daily/$RUN_DATE"
if ! compgen -G "$RUN_DIR/*.pdf" >/dev/null; then
  echo "No PDFs found in $RUN_DIR"
  exit 1
fi

if [[ "${NEWS_SKIP_GIT_PUSH:-false}" == "true" ]]; then
  echo "NEWS_SKIP_GIT_PUSH=true; skipping git commit and push."
  exit 0
fi

if ! git diff --cached --quiet; then
  echo "There are already staged changes. Aborting before PDF commit."
  git status --short
  exit 1
fi

git add -f "$RUN_DIR"/*.pdf

if git diff --cached --quiet -- "$RUN_DIR"; then
  echo "No PDF changes to commit for $RUN_DATE."
  exit 0
fi

git commit -m "chore: add daily news PDFs $RUN_DATE"

BRANCH="$(git branch --show-current)"
git push origin "$BRANCH"
