# bus-tracer

伊勢山（平塚市）から大野農協前（平塚市）までの神奈中バス接近情報を追跡し、5分ごとに公開データを更新する GitHub Pages アプリです。

## 同梱パッケージ

- FastAPI
- Uvicorn
- HTTPX
- Beautiful Soup 4
- selectolax
- lxml
- pandas
- SQLAlchemy
- Alembic
- Jinja2
- aiofiles
- orjson
- pydantic-settings
- python-dotenv
- tenacity
- pytest
- Ruff

## 開発

開発コンテナを使うか、compose サービスを起動してシェル環境を使います。

```bash
docker compose up -d --build
docker compose exec app bash
```

dev container の設定を変えたら、VS Code で `Dev Containers: Rebuild and Reopen in Container` を実行して再構築します。

## コンテナ内の GitHub CLI

dev container には `gh` が入っています。

さらに、認証情報と git 設定を共有するために、次のホスト側ファイルを読み取り専用でコンテナにマウントします。

- `~/.config/gh`
- `~/.gitconfig`
- `~/.ssh`

そのため、ホスト側で実行した `gh auth login` をコンテナ再構築後も再利用できます。

## 構成

- `scripts/fetch_bus_data.py`: 神奈中の接近情報ページを取得して解析し、`docs/data/status.json` を出力します。
- `docs/`: GitHub Pages で公開する静的サイトです。
- `.github/workflows/pages.yml`: 5分ごとにスクレイパーを実行し、更新済みサイトをデプロイします。

## ローカル確認

現在のデータスナップショットを生成します。

```bash
python3 scripts/fetch_bus_data.py --output docs/data/status.json
```

静的サイトをローカルで確認します。

```bash
python3 -m http.server 8000 --directory docs
```

その後 `http://localhost:8000` を開きます。

## GitHub Pages 公開

1. このリポジトリを GitHub に push します。
2. GitHub 側で Pages のソースを `GitHub Actions` に設定します。
3. workflow は push 時、手動実行時、5分間隔の cron でデプロイされます。

## 本番前チェックリスト

1. 少なくとも一度はローカルの `main` を `origin/main` に push します。最初の push までは remote 側に default branch がなく、Pages は開始できません。
2. private Pages に対応しないプランの場合は、公開前にリポジトリを public に変更します。
3. GitHub の `Settings -> Pages` で source が `GitHub Actions` になっていることを確認します。
4. `Actions` 画面から `Deploy GitHub Pages` を一度手動実行して、cron を待たずに初回デプロイを走らせます。
5. 初回実行後、公開 URL のルートと `docs/data/status.json` の両方にアクセスできることを確認します。
6. バス運行時間帯に、公開ページと元サイトを見比べてパーサが live レイアウトに合っているか確認します。

## トラブルシュート

- 初回デプロイ成功前に `gh api repos/Npieju/bus-tracer/pages` が `404` を返すのは想定内です。
- scheduled workflow は default branch 上でのみ動き、非アクティブなリポジトリでは自動停止されることがあります。
- upstream の HTML レイアウトが変わった場合でも、workflow summary には直近の取得結果が残り、`status.json` は壊れたデータを黙って公開せず error payload にフォールバックします。

補足:

- GitHub Actions の cron は 5 分間隔を指定できますが、実際の実行時刻には多少のズレがあります。
- アプリ自体もブラウザ側で 5 分ごとに `status.json` を再取得するため、開いたままのタブでも新しいデプロイを追従できます。

## GitHub リポジトリ

ローカルの git は初期化済みです。

GitHub CLI で認証した後、必要なら次のコマンドで remote repository を作成します。

```bash
gh auth login --hostname github.com --git-protocol https --web
gh repo create bus-tracer --public --source=. --remote=origin
```