from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SourceReference, TopicInsight
from .text import clean_text


def load_topic_insights(path: str | Path | None) -> dict[str, TopicInsight]:
    if not path:
        return {}

    summary_path = Path(path)
    if not summary_path.exists():
        raise RuntimeError(f"Summary file does not exist: {summary_path}")

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    topics = _extract_topics(payload)
    insights: dict[str, TopicInsight] = {}
    for raw_topic in topics:
        topic = _as_dict(raw_topic, "summary topic")
        topic_id = clean_text(str(topic.get("topic_id") or topic.get("id") or ""))
        if not topic_id:
            raise RuntimeError("Each summary topic must have topic_id.")

        insights[topic_id] = TopicInsight(
            topic_id=topic_id,
            summary=clean_text(topic.get("summary"), max_length=1200),
            key_points=tuple(
                clean_text(value, max_length=400)
                for value in _as_list(topic.get("key_points"))
                if clean_text(value)
            ),
            background=clean_text(topic.get("background"), max_length=1000),
            personal_takeaway=clean_text(
                topic.get("personal_takeaway"),
                max_length=1000,
            ),
            sources=tuple(_parse_source(value) for value in _as_list(topic.get("sources"))),
        )
    return insights


def _extract_topics(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    data = _as_dict(payload, "summary file")
    topics = data.get("topics")
    if not isinstance(topics, list):
        raise RuntimeError("Summary file must contain a topics list.")
    return topics


def _parse_source(value: Any) -> SourceReference:
    source = _as_dict(value, "summary source")
    return SourceReference(
        title=clean_text(source.get("title"), max_length=220),
        url=str(source.get("url") or "").strip(),
    )


def _as_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{name} must be an object.")
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RuntimeError("Expected a list in summary file.")
    return value
