# Bus Tracer ナレッジ

## 目的

- GitHub Pages 上で軽量な web アプリを公開する。
- 固定ルート 伊勢山（平塚市） -> 大野農協前（平塚市）の神奈中リアルタイム接近情報を表示する。
- 公開データを 5 分ごとに更新する。

## 固定ルート定義

- 乗車停留所: 伊勢山（平塚市）
- 乗車停留所 ID: `16240`
- 降車停留所: 大野農協前（平塚市）
- 降車停留所 ID: `16244`

## 設計判断

- サイトは静的構成で、`docs/` を GitHub Pages から配信する。
- upstream サイトにはこの用途で使える permissive な CORS 経路がないため、live data をブラウザから直接取得しない。
- データ取得は GitHub Actions 内で 5 分ごとに server-side 実行する。
- スクレイパーは正規化済み JSON スナップショットを `docs/data/status.json` に出力する。
- フロントエンドは `status.json` を読み、ブラウザ内でも 5 分ごとに再取得する。

## 主要ファイル

- `scripts/fetch_bus_data.py`: upstream 取得、解析、JSON 生成。
- `docs/index.html`: 静的 UI 本体。
- `docs/app.js`: JSON 取得、タイマー、描画ロジック。
- `docs/styles.css`: 見た目の定義。
- `.github/workflows/pages.yml`: 定期取得と GitHub Pages デプロイ。
- `docs/.nojekyll`: Pages 上で Jekyll 処理を無効化する。

## デプロイ前提

- default branch は `main`。
- GitHub Pages の source は `GitHub Actions` を使う。
- 初回デプロイは最初の push 後に一度起動する必要がある。
- repository を private のまま使うなら、GitHub プランが private GitHub Pages をサポートしている必要がある。

## データ契約

`docs/data/status.json` には常に次のキーが入る。

- `status`: `ok` または `error`
- `fetchedAt`: ISO 8601 形式の UTC timestamp
- `message`: 取得結果を示すトップレベル文言
- `hasLiveData`: boolean
- `route.fromStop.id`: `16240`
- `route.toStop.id`: `16244`
- `source.url`: upstream の結果 URL
- `details`: 元ページから抽出した平坦化済みテキスト

## 運用リスク

- upstream の HTML は予告なく変わり、解析が壊れる可能性がある。
- GitHub Actions cron は厳密なリアルタイム実行ではなく、実行時刻にズレが出る。
- scheduled workflow は default branch でのみ動く。
- GitHub Pages は初回 deploy 成功まで未公開のままになりうる。
- 運行時間外は、取得自体が成功していても `該当する情報は現在ありません。` になることがある。

## 確認コマンド

ローカルでスナップショットを生成する。

```bash
python3 scripts/fetch_bus_data.py --output docs/data/status.json
```

ローカルでサイトを確認する。

```bash
python3 -m http.server 8000 --directory docs
```

初回デプロイ後に Pages 設定を確認する。

```bash
gh api repos/Npieju/bus-tracer/pages
```