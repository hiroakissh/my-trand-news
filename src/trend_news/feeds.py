from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import requests

from .config import AppConfig, FeedConfig, GoogleNewsConfig, TopicConfig
from .models import NewsItem, TopicDigest
from .text import clean_text


LOGGER = logging.getLogger(__name__)
USER_AGENT = "my-trend-news/0.1 (+https://localhost)"


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str


def collect_topic_digests(config: AppConfig, now: datetime) -> tuple[TopicDigest, ...]:
    digests: list[TopicDigest] = []
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=config.lookback_hours)

    for topic in config.topics:
        if not topic.enabled:
            continue

        items: list[NewsItem] = []
        errors: list[str] = []
        for source in build_sources(topic, config.google_news):
            try:
                items.extend(fetch_source_items(source, cutoff, config.include_undated))
            except Exception as exc:  # noqa: BLE001 - keep one failed source from killing a run.
                message = f"{source.name}: {exc}"
                LOGGER.warning("Failed to fetch %s", message)
                errors.append(message)

        deduped = dedupe_items(items)
        max_items = topic.max_items or config.max_items_per_topic
        digests.append(
            TopicDigest(
                topic=topic,
                items=tuple(sort_items(deduped)[:max_items]),
                errors=tuple(errors),
            )
        )

    return tuple(digests)


def build_sources(topic: TopicConfig, google_news: GoogleNewsConfig) -> tuple[FeedSource, ...]:
    sources: list[FeedSource] = [
        FeedSource(name=feed.name, url=feed.url) for feed in topic.feeds
    ]
    if google_news.enabled:
        for query in topic.queries:
            sources.append(
                FeedSource(
                    name=f"Google News: {query}",
                    url=build_google_news_url(query, google_news),
                )
            )
    return tuple(sources)


def build_google_news_url(query: str, google_news: GoogleNewsConfig) -> str:
    normalized_query = query.strip()
    if google_news.lookback_query and "when:" not in normalized_query:
        normalized_query = f"{normalized_query} {google_news.lookback_query}"

    params = {
        "q": normalized_query,
        "hl": google_news.language,
        "gl": google_news.country,
        "ceid": google_news.ceid,
    }
    return f"https://news.google.com/rss/search?{urlencode(params)}"


def fetch_source_items(
    source: FeedSource,
    cutoff: datetime,
    include_undated: bool,
) -> tuple[NewsItem, ...]:
    response = requests.get(
        source.url,
        timeout=(5, 20),
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()

    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(str(parsed.bozo_exception))

    feed_title = clean_text(parsed.feed.get("title") if parsed.feed else "") or source.name
    items: list[NewsItem] = []
    for entry in parsed.entries:
        item = parse_entry(entry, feed_title)
        if not item.title or not item.url:
            continue
        if item.published_at is None and not include_undated:
            continue
        if item.published_at is not None and item.published_at < cutoff:
            continue
        items.append(item)

    LOGGER.info("Fetched %s items from %s", len(items), source.name)
    return tuple(items)


def parse_entry(entry: Any, fallback_source: str) -> NewsItem:
    source_detail = entry.get("source") if hasattr(entry, "get") else None
    source = ""
    if isinstance(source_detail, dict):
        source = clean_text(source_detail.get("title"))
    if not source:
        source = fallback_source

    summary = entry.get("summary") or entry.get("description") or ""
    return NewsItem(
        title=clean_text(entry.get("title"), max_length=220),
        url=str(entry.get("link") or "").strip(),
        source=source,
        summary=clean_text(summary, max_length=600),
        published_at=parse_entry_datetime(entry),
    )


def parse_entry_datetime(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed_time = entry.get(key)
        if parsed_time:
            return datetime.fromtimestamp(calendar.timegm(parsed_time), tz=timezone.utc)

    for key in ("published", "updated", "created"):
        raw_value = entry.get(key)
        if not raw_value:
            continue
        try:
            parsed = parsedate_to_datetime(str(raw_value))
        except (TypeError, ValueError):
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return None


def dedupe_items(items: list[NewsItem]) -> tuple[NewsItem, ...]:
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = normalized_url(item.url) or item.title.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return tuple(unique)


def normalized_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid", "mc_cid", "mc_eid"}
    ]
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            urlencode(query),
            "",
        )
    )


def sort_items(items: tuple[NewsItem, ...]) -> list[NewsItem]:
    return sorted(
        items,
        key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
