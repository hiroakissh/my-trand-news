import json
from datetime import datetime
from pathlib import Path

from trend_news.config import load_config
from trend_news.insights import load_topic_insights
from trend_news.models import SourceReference, TopicDigest, TopicInsight
from trend_news.pdf import generate_topic_pdf
from trend_news.storage import load_daily_digest_from_manifest


def test_load_topic_insights(tmp_path: Path) -> None:
    summary_path = tmp_path / "codex_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "run_date": "2026-05-02",
                "topics": [
                    {
                        "topic_id": "swift",
                        "summary": "Swiftの動向まとめ",
                        "key_points": ["Swift 6関連の更新", "開発者向け情報"],
                        "background": "Apple開発者向けの文脈",
                        "personal_takeaway": "移行計画を確認する",
                        "sources": [
                            {"title": "Swift article", "url": "https://example.com/swift"}
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    insights = load_topic_insights(summary_path)

    assert insights["swift"].summary == "Swiftの動向まとめ"
    assert insights["swift"].key_points == ("Swift 6関連の更新", "開発者向け情報")
    assert insights["swift"].sources[0].url == "https://example.com/swift"


def test_load_daily_digest_from_manifest_applies_insights(tmp_path: Path) -> None:
    config_path = tmp_path / "topics.yml"
    config_path.write_text(
        """
topics:
  - id: swift
    title: Swift
    queries:
      - Swift
""",
        encoding="utf-8",
    )
    run_dir = tmp_path / "output" / "2026-05-02"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_date": "2026-05-02",
                "generated_at": "2026-05-02T08:00:00+09:00",
                "total_items": 1,
                "topics": [
                    {
                        "id": "swift",
                        "title": "Swift",
                        "item_count": 1,
                        "errors": [],
                        "items": [
                            {
                                "title": "Swift news",
                                "url": "https://example.com",
                                "source": "Example",
                                "summary": "Summary",
                                "published_at": "2026-05-02T00:00:00+00:00",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    insights = load_topic_insights(
        _write_summary_file(tmp_path / "codex_summary.json")
    )

    digest = load_daily_digest_from_manifest(
        config=load_config(config_path),
        run_dir=run_dir,
        insights=insights,
    )

    assert digest.topics[0].items[0].title == "Swift news"
    assert digest.topics[0].insight is not None
    assert digest.topics[0].insight.summary == "Swiftの動向まとめ"


def test_generate_pdf_with_topic_insight(tmp_path: Path) -> None:
    config = load_config(_write_topic_config(tmp_path / "topics.yml"))
    insight = TopicInsight(
        topic_id="swift",
        summary="Swiftの動向まとめ",
        key_points=("Swift 6関連の更新",),
        background="Apple開発者向けの文脈",
        personal_takeaway="移行計画を確認する",
        sources=(SourceReference(title="Swift article", url="https://example.com"),),
    )
    digest = TopicDigest(topic=config.topics[0], items=(), insight=insight)

    pdf_path = generate_topic_pdf(
        digest,
        tmp_path / "swift.pdf",
        datetime.now(),
    )

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def _write_summary_file(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "topics": [
                    {
                        "topic_id": "swift",
                        "summary": "Swiftの動向まとめ",
                        "key_points": [],
                        "background": "",
                        "personal_takeaway": "",
                        "sources": [],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _write_topic_config(path: Path) -> Path:
    path.write_text(
        """
topics:
  - id: swift
    title: Swift
    queries:
      - Swift
""",
        encoding="utf-8",
    )
    return path
