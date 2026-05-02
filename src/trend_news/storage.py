from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .models import DailyDigest, NewsItem, TopicDigest


def prepare_run_dir(output_dir: Path, run_date: str) -> Path:
    path = output_dir / run_date
    if path.exists():
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(value: str) -> str:
    allowed = [char if char.isalnum() or char in {"-", "_"} else "-" for char in value]
    return "".join(allowed).strip("-") or "topic"


def write_manifest(digest: DailyDigest) -> Path:
    path = digest.output_dir / "manifest.json"
    payload = {
        "run_date": digest.run_date.isoformat(),
        "generated_at": digest.generated_at.isoformat(),
        "total_items": digest.total_items,
        "topics": [_topic_payload(topic) for topic in digest.topics],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_summary(digest: DailyDigest) -> Path:
    path = digest.output_dir / "summary.txt"
    lines = [
        f"Daily news digest: {digest.run_date.isoformat()}",
        f"Generated at: {digest.generated_at.isoformat()}",
        f"Total items: {digest.total_items}",
        "",
    ]
    for topic in digest.topics:
        lines.append(f"[{topic.topic.title}] {len(topic.items)} items")
        for item in topic.items[:5]:
            lines.append(f"- {item.title}")
        if topic.errors:
            lines.append("Warnings:")
            lines.extend(f"- {error}" for error in topic.errors)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cleanup_old_runs(output_dir: Path, keep_days: int, now: datetime) -> None:
    if not output_dir.exists():
        return
    cutoff = now.date() - timedelta(days=keep_days)
    for child in output_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            child_date = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if child_date < cutoff:
            shutil.rmtree(child)


def _topic_payload(topic: TopicDigest) -> dict[str, object]:
    return {
        "id": topic.topic.id,
        "title": topic.topic.title,
        "item_count": len(topic.items),
        "errors": list(topic.errors),
        "items": [_item_payload(item) for item in topic.items],
    }


def _item_payload(item: NewsItem) -> dict[str, object]:
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "summary": item.summary,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }
