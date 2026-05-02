from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


_TOPIC_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str


@dataclass(frozen=True)
class GoogleNewsConfig:
    enabled: bool = True
    language: str = "ja"
    country: str = "JP"
    ceid: str = "JP:ja"
    lookback_query: str = "when:1d"


@dataclass(frozen=True)
class MailConfig:
    subject_prefix: str = "Daily Trend News"


@dataclass(frozen=True)
class TopicConfig:
    id: str
    title: str
    queries: tuple[str, ...]
    feeds: tuple[FeedConfig, ...]
    max_items: int | None
    enabled: bool = True


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    lookback_hours: int
    max_items_per_topic: int
    include_undated: bool
    output_dir: Path
    keep_days: int
    google_news: GoogleNewsConfig
    mail: MailConfig
    topics: tuple[TopicConfig, ...]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")

    topics = tuple(_parse_topic(item) for item in raw.get("topics", []))
    if not topics:
        raise ValueError("At least one topic must be configured.")

    google_news_raw = _as_dict(raw.get("google_news", {}), "google_news")
    mail_raw = _as_dict(raw.get("mail", {}), "mail")

    return AppConfig(
        timezone=str(raw.get("timezone", "Asia/Tokyo")),
        lookback_hours=_positive_int(raw.get("lookback_hours", 24), "lookback_hours"),
        max_items_per_topic=_positive_int(
            raw.get("max_items_per_topic", 8), "max_items_per_topic"
        ),
        include_undated=bool(raw.get("include_undated", True)),
        output_dir=Path(str(raw.get("output_dir", "output/daily"))),
        keep_days=_positive_int(raw.get("keep_days", 30), "keep_days"),
        google_news=GoogleNewsConfig(
            enabled=bool(google_news_raw.get("enabled", True)),
            language=str(google_news_raw.get("language", "ja")),
            country=str(google_news_raw.get("country", "JP")),
            ceid=str(google_news_raw.get("ceid", "JP:ja")),
            lookback_query=str(google_news_raw.get("lookback_query", "when:1d")),
        ),
        mail=MailConfig(
            subject_prefix=str(mail_raw.get("subject_prefix", "Daily Trend News")),
        ),
        topics=topics,
    )


def _parse_topic(raw_topic: Any) -> TopicConfig:
    topic = _as_dict(raw_topic, "topic")
    topic_id = str(topic.get("id", "")).strip()
    if not _TOPIC_ID_PATTERN.match(topic_id):
        raise ValueError(
            f"Invalid topic id '{topic_id}'. Use lowercase letters, numbers, '-' or '_'."
        )

    title = str(topic.get("title", "")).strip()
    if not title:
        raise ValueError(f"Topic '{topic_id}' must have a title.")

    queries = tuple(str(value).strip() for value in topic.get("queries", []) if value)
    feeds = tuple(_parse_feed(feed) for feed in topic.get("feeds", []))
    if not queries and not feeds:
        raise ValueError(f"Topic '{topic_id}' must have queries or feeds.")

    max_items = topic.get("max_items")
    return TopicConfig(
        id=topic_id,
        title=title,
        queries=queries,
        feeds=feeds,
        max_items=_positive_int(max_items, f"{topic_id}.max_items")
        if max_items is not None
        else None,
        enabled=bool(topic.get("enabled", True)),
    )


def _parse_feed(raw_feed: Any) -> FeedConfig:
    feed = _as_dict(raw_feed, "feed")
    name = str(feed.get("name", "")).strip()
    url = str(feed.get("url", "")).strip()
    if not name or not url:
        raise ValueError("Each feed must have name and url.")
    return FeedConfig(name=name, url=url)


def _as_dict(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping.")
    return value


def _positive_int(value: Any, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return parsed
