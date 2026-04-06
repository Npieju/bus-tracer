# bus-tracer

特定の固定ルートについて、順方向と逆方向の両方の神奈中バス接近情報を追跡し、5分ごとに公開データを更新する GitHub Pages アプリです。

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

- `scripts/fetch_bus_data.py`: 神奈中の接近情報ページを順方向・逆方向の両方で取得して解析し、`docs/data/status.json` を出力します。
- `docs/`: GitHub Pages で公開する静的サイトです。
- `.github/workflows/pages.yml`: 5分ごとにスクレイパーを実行し、更新済みサイトをデプロイします。

## ローカル確認

現在の双方向データスナップショットを生成します。

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
3. workflow は push 時、手動実行時、external dispatch、5分間隔の cron でデプロイされます。

## 更新トリガー方針

- GitHub Actions の `schedule` は 5 分間隔で安定しないため、主系の更新トリガーとしては使わない。
- 主系は外部 scheduler からの `repository_dispatch` とし、GitHub 側の `schedule` は backup 扱いにする。
- 推奨サービスは `cron-job.org` とする。無料で 1 分間隔まで設定でき、HTTP POST、任意ヘッダ、実行履歴に対応しているため、この用途に十分。
- stale snapshot を避けたい場合は、5 分ごとに外部 scheduler から次の endpoint を叩く。

```bash
curl -L -X POST \
	-H "Accept: application/vnd.github+json" \
	-H "Authorization: Bearer ${GITHUB_TOKEN}" \
	https://api.github.com/repos/Npieju/bus-tracer/dispatches \
	-d '{"event_type":"external-refresh"}'
```

- public repository だけを触る classic PAT なら `public_repo`、private repository を触るなら `repo` scope が必要。
- cron-job.org、EasyCron、GitHub App Script、Cloudflare Workers Cron Trigger など、任意の外部 scheduler を使ってよい。
- 外部 scheduler ではタイムアウトを 30 秒以上にし、失敗時は少なくとも 1 回再試行させる。

## cron-job.org 設定例

1. `cron-job.org` に登録する。
2. `Create cronjob` から新規 job を作る。
3. URL は `https://api.github.com/repos/Npieju/bus-tracer/dispatches` にする。
4. Request method は `POST` にする。
5. 実行間隔は 5 分にする。
6. Request headers に次を入れる。

```text
Accept: application/vnd.github+json
Authorization: Bearer <GITHUB_TOKEN>
Content-Type: application/json
```

7. Request body に次を入れる。

```json
{"event_type":"external-refresh"}
```

8. 作成後に `Test run` で 204 が返ることを確認する。
9. GitHub Actions 側で `repository_dispatch` を受けた run が起動することを確認する。

補足:

- `GITHUB_TOKEN` は classic PAT で十分。
- repo が public なら `public_repo` scope で足りる。
- まずは cron-job.org だけ設定し、GitHub cron は backup として残す。

## 運用メモ

- 実装依頼に対する通常の更新では、別途確認を挟まずに commit / push して Pages 反映まで進めてよい運用とする。
- 破壊的変更、要件不明、外部権限不足などの例外時のみ停止して確認する。
- 鮮度が重要な更新では GitHub cron を信用せず、external scheduler の dispatch を主系として扱う。

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
- GitHub Actions の cron は設定どおりの 5 分間隔で走らないことがあり、20 分超から数時間の空白が発生することがあります。
- upstream の HTML レイアウトが変わった場合でも、workflow summary には直近の取得結果が残り、`status.json` は壊れたデータを黙って公開せず error payload にフォールバックします。

補足:

- GitHub Actions の cron は 5 分間隔を指定できますが、実際の実行時刻には多少のズレがあります。
- この repo では実測上、cron の空白が 1 時間超になることがあるため、5 分鮮度を求めるなら external scheduler が必須です。
- アプリ自体もブラウザ側で 5 分ごとに `status.json` を再取得するため、開いたままのタブでも双方向の新しいデプロイを追従できます。

## GitHub リポジトリ

ローカルの git は初期化済みです。

GitHub CLI で認証した後、必要なら次のコマンドで remote repository を作成します。

```bash
gh auth login --hostname github.com --git-protocol https --web
gh repo create bus-tracer --public --source=. --remote=origin
```