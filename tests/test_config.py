from pathlib import Path

from trend_news.config import load_config
from trend_news.storage import prepare_run_dir


def test_load_config_parses_topics(tmp_path: Path) -> None:
    config_path = tmp_path / "topics.yml"
    config_path.write_text(
        """
timezone: Asia/Tokyo
topics:
  - id: ai
    title: AI
    queries:
      - OpenAI
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.timezone == "Asia/Tokyo"
    assert config.topics[0].id == "ai"
    assert config.topics[0].queries == ("OpenAI",)


def test_prepare_run_dir_clears_previous_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "2026-05-02"
    run_dir.mkdir()
    stale_file = run_dir / "old.pdf"
    stale_file.write_text("old", encoding="utf-8")

    prepared = prepare_run_dir(tmp_path, "2026-05-02")

    assert prepared == run_dir
    assert not stale_file.exists()
