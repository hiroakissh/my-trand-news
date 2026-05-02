# My Trend News

分野ごとにニュース/RSSを取得し、日次PDFとして保存して、Gmail SMTPで自分宛に送信する自動実行向けプロジェクトです。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env` に Gmail のアプリパスワードを設定してください。通常のGoogleログインパスワードでは送信できません。

## 分野の編集

`config/topics.yml` の `topics` に分野を追加します。

- `id`: ファイル名にも使う英数字ID
- `title`: PDFに表示する分野名
- `queries`: Google News RSSで検索する語句
- `feeds`: 任意のRSS/Atomフィード
- `max_items`: その分野でPDFに載せる最大件数

## 手動実行

送信せずにPDF生成まで確認します。

```bash
python -m trend_news run --config config/topics.yml --dry-run
```

本番送信します。

```bash
python -m trend_news run --config config/topics.yml
```

PDFと実行結果は `output/daily/YYYY-MM-DD/` に保存されます。ログは `logs/daily-news.log` です。

## Codexオートメーション用

8:00の定期実行では、ワークスペースをこのリポジトリにして以下を実行するプロンプトにします。

```text
Run ./scripts/run_daily.sh and report whether the daily news PDFs were generated and mailed successfully.
```

`scripts/run_daily.sh` は `.venv` があれば自動で有効化します。
