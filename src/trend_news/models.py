from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import TopicConfig


@dataclass(frozen=True)
class NewsItem:
    title: str
    url: str
    source: str
    summary: str
    published_at: datetime | None


@dataclass(frozen=True)
class TopicDigest:
    topic: TopicConfig
    items: tuple[NewsItem, ...]
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class DailyDigest:
    run_date: date
    generated_at: datetime
    topics: tuple[TopicDigest, ...]
    output_dir: Path

    @property
    def total_items(self) -> int:
        return sum(len(topic.items) for topic in self.topics)
