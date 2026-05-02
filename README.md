# My Trend News

分野ごとにニュース/RSSを取得し、日次PDFとして保存して、Gmail APIで自分宛に送信する自動実行向けプロジェクトです。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Gmail API OAuth

Google CloudでGmail APIを有効化し、OAuthクライアントを作成します。

1. Google Cloud ConsoleでGmail APIを有効化します。
2. OAuth同意画面を設定します。
3. OAuthクライアントIDを `Desktop app` として作成します。
4. ダウンロードしたJSONを `secrets/gmail_oauth_client.json` に保存します。
5. `.env` の `NEWS_MAIL_TO` と `NEWS_MAIL_FROM` を設定します。

初回だけブラウザで認可します。

```bash
python -m trend_news auth-gmail
```

成功すると `data/gmail_token.json` が作成されます。このトークンはコミットしません。
使用スコープは送信専用の `https://www.googleapis.com/auth/gmail.send` です。

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

8:00の定期実行でGmail送信まで行う場合は、ワークスペースをこのリポジトリにして以下を実行するプロンプトにします。

```text
Run ./scripts/run_daily.sh and report whether the daily news PDFs were generated and mailed successfully.
```

生成PDFをGitHubへpushする場合は、こちらを使います。

```text
Run ./scripts/run_daily_and_push.sh and report whether the daily news PDFs were generated, mailed, committed, and pushed successfully.
```

`scripts/run_daily.sh` と `scripts/run_daily_and_push.sh` は `.venv` があれば自動で有効化します。
OAuthクライアントJSON、OAuthトークン、`.env`、ログはGit管理外のままです。
