# Bus Tracer 計画

## 現在の状態

- 静的な GitHub Pages アプリは実装済み。
- 定期 GitHub Actions デプロイは実装済み。
- スクレイパーの検証は実装済み。
- ローカルでのスナップショット生成は動作済み。
- 初回本番デプロイはまだ未確認。
- 実際のバス運行時間帯での確認はまだ未実施。

## 直近の目標

コードベース側で追加作業をせずに、初回本番デプロイを起動できる状態にする。

## リリース手順

1. 現在の workspace 変更を commit する。
2. `main` を `origin` に push する。
3. GitHub repository settings で `Pages -> Source = GitHub Actions` を確認する。
4. `Deploy GitHub Pages` workflow を一度手動実行する。
5. 公開されたサイトと `data/status.json` にアクセスできることを確認する。

## 本番確認手順

1. 対象ルートで実際にバスが走っている時間帯を待つ。
2. 公開ページと upstream の神奈中ページを並べて開く。
3. ルート表示が正しいことを確認する。
4. ステータスメッセージと details が upstream と一致することを確認する。
5. ブラウザ側の 5 分更新を確認できるまでページを開いたままにする。
6. 直近の GitHub Actions run summary で取得状態を確認する。

## 残 TODO

- 初回 GitHub Pages デプロイが GitHub 上で成功することを確認する。
- repository visibility が public に変更済みであることを前提に Pages 有効化を再確認する。
- 履歴スナップショットを残すか、latest-state-only でよいか決める。
- 公開 URL が確定したら health badge や status note の追加を検討する。
- upstream 不安定化が繰り返すなら parser 抽出テスト追加を検討する。

## 決定事項

- 専用デプロイ branch は作らない。
- 定期更新に commit/push hook は使わない。
- 定期更新の正本は scheduled GitHub Actions とする。
- ルートは当面固定とする。
- 通常の実装作業は、追加確認なしで commit / push して公開反映まで進める。