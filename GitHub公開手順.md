# GitHub Pages 公開手順

このフォルダは生徒公開用です。先生用メモや旧HTML版は入れていません。

## 公開するフォルダ

`歴史シミュレーションv2_public/`

## GitHubでの公開手順

1. GitHubで新しいリポジトリを作る。
   例：`history-simulation-v2-public`
2. この `歴史シミュレーションv2_public` フォルダの中身だけをリポジトリに入れる。
3. GitHubのリポジトリ画面で `Settings` → `Pages` を開く。
4. `Build and deployment` の `Source` を `Deploy from a branch` にする。
5. `Branch` を `main`、フォルダを `/root` にして保存する。
6. 数分後に表示されるURLを生徒に配布する。

## 注意

- 開発用の `歴史シミュレーションv2/` を丸ごと公開しない。
- `index_legacy.html`、`CLAUDE.md`、`JSON化メモ.md` は公開しない。
- シナリオを追加したら、公開用フォルダにも `scenario.json` と `scenarios.json` を反映する。