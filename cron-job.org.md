# cron-job.org 設定メモ

この repository で外部 refresh を有効化する最後の手順だけをまとめる。

## 1. GitHub token を作る

- GitHub の classic PAT を作る。
- public repository のままなら scope は `public_repo` で足りる。
- token の用途はこの `repository_dispatch` 専用に分ける。

## 2. ローカル疎通を確認する

```bash
export GITHUB_TOKEN=<YOUR_CLASSIC_PAT>
python3 scripts/dispatch_external_refresh.py --wait
```

期待結果:

- `repository_dispatch accepted` と出る。
- GitHub Actions run URL が出る。
- 最後に `workflow conclusion: success` と出る。

## 3. cron-job.org に入れる値

- URL

```text
https://api.github.com/repos/Npieju/bus-tracer/dispatches
```

- Request method

```text
POST
```

- Schedule

```text
Every 5 minutes
```

- Request headers

```text
Accept: application/vnd.github+json
Authorization: Bearer <YOUR_CLASSIC_PAT>
Content-Type: application/json
X-GitHub-Api-Version: 2022-11-28
```

- Request body

```json
{"event_type":"external-refresh"}
```

## 4. cron-job.org で確認すること

1. `Test run` で 204 が返る。
2. GitHub Actions に `event = repository_dispatch` の run が起動する。
3. run conclusion が `success` になる。

## 5. 問題が出たときの切り分け

まず cron-job.org を疑う前にローカルで次を再実行する。

```bash
export GITHUB_TOKEN=<YOUR_CLASSIC_PAT>
python3 scripts/dispatch_external_refresh.py --wait
```

- これが失敗するなら token か GitHub 側設定の問題。
- これが成功するなら cron-job.org の header、body、間隔設定の問題。