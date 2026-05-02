from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Mapping

from .config import AppConfig, TopicConfig
from .models import DailyDigest, NewsItem, TopicDigest, TopicInsight


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


def load_daily_digest_from_manifest(
    *,
    config: AppConfig,
    run_dir: Path,
    insights: Mapping[str, TopicInsight] | None = None,
) -> DailyDigest:
    manifest_path = run_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    topic_configs = {topic.id: topic for topic in config.topics}
    insight_map = insights or {}

    topics: list[TopicDigest] = []
    for raw_topic in payload.get("topics", []):
        topic_id = str(raw_topic.get("id", "")).strip()
        topic_config = topic_configs.get(topic_id) or TopicConfig(
            id=topic_id,
            title=str(raw_topic.get("title") or topic_id),
            queries=(),
            feeds=(),
            max_items=None,
        )
        topics.append(
            TopicDigest(
                topic=topic_config,
                items=tuple(_item_from_payload(item) for item in raw_topic.get("items", [])),
                errors=tuple(str(error) for error in raw_topic.get("errors", [])),
                insight=insight_map.get(topic_id),
            )
        )

    return DailyDigest(
        run_date=date.fromisoformat(str(payload["run_date"])),
        generated_at=datetime.fromisoformat(str(payload["generated_at"])),
        topics=tuple(topics),
        output_dir=run_dir,
    )


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


def _item_from_payload(payload: dict[str, object]) -> NewsItem:
    published_at = payload.get("published_at")
    return NewsItem(
        title=str(payload.get("title") or ""),
        url=str(payload.get("url") or ""),
        source=str(payload.get("source") or ""),
        summary=str(payload.get("summary") or ""),
        published_at=datetime.fromisoformat(str(published_at)) if published_at else None,
    )
