from datetime import datetime, timezone

from trend_news.config import GoogleNewsConfig
from trend_news.feeds import build_google_news_url, dedupe_items, normalized_url
from trend_news.models import NewsItem


def test_build_google_news_url_adds_lookback() -> None:
    url = build_google_news_url("OpenAI", GoogleNewsConfig())

    assert "OpenAI+when%3A1d" in url
    assert "ceid=JP%3Aja" in url


def test_normalized_url_removes_tracking_params() -> None:
    url = normalized_url("https://Example.com/a/?utm_source=x&keep=1#fragment")

    assert url == "https://example.com/a?keep=1"


def test_dedupe_items_prefers_first_url() -> None:
    item = NewsItem(
        title="Title",
        url="https://example.com/a?utm_source=x",
        source="source",
        summary="",
        published_at=datetime.now(timezone.utc),
    )
    duplicate = NewsItem(
        title="Title duplicate",
        url="https://example.com/a",
        source="source",
        summary="",
        published_at=datetime.now(timezone.utc),
    )

    assert dedupe_items([item, duplicate]) == (item,)
