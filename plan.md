# Bus Tracer 計画

## 現在の状態

- 静的な GitHub Pages アプリは実装済み。
- 定期 GitHub Actions デプロイは実装済み。
- スクレイパーの検証は実装済み。
- ローカルでのスナップショット生成は動作済み。
- 初回本番デプロイはまだ未確認。
- 実際のバス運行時間帯での確認はまだ未実施。

## 直近の目標

GitHub cron に依存せず、外部 scheduler を主系トリガーとして更新鮮度を安定させる。

## リリース手順

1. 現在の workspace 変更を commit する。
2. `main` を `origin` に push する。
3. GitHub repository settings で `Pages -> Source = GitHub Actions` を確認する。
4. external scheduler から `repository_dispatch` で `external-refresh` を 5 分ごとに投げる設定を入れる。
5. `Deploy GitHub Pages` workflow を一度手動実行する。
6. 公開されたサイトと `data/status.json` にアクセスできることを確認する。

## 本番確認手順

1. 対象ルートで実際にバスが走っている時間帯を待つ。
2. 公開ページと upstream の神奈中ページを並べて開く。
3. ルート表示が正しいことを確認する。
4. ステータスメッセージと details が upstream と一致することを確認する。
5. ブラウザ側の 5 分更新を確認できるまでページを開いたままにする。
6. 直近の GitHub Actions run summary で取得状態を確認する。

## 残 TODO

- `cron-job.org` を実際に設定し、設定前後で `python3 scripts/dispatch_external_refresh.py --wait` を使って dispatch 疎通を確認する。
- GitHub cron は 5 分間隔の backup として残し、`schedule` / `repository_dispatch` は `status.json` 更新 commit を作り、push run で Pages を publish する。
- 履歴スナップショットを残すか、latest-state-only でよいか決める。
- 公開 URL が確定したら health badge や status note の追加を検討する。
- upstream 不安定化が繰り返すなら parser 抽出テスト追加を検討する。

## 決定事項

- 専用デプロイ branch は作らない。
- 定期更新に commit/push hook は使わない。
- 定期更新の主系は external scheduler dispatch、scheduled GitHub Actions は backup とする。
- ルートは当面固定とする。
- 通常の実装作業は、追加確認なしで commit / push して公開反映まで進める。