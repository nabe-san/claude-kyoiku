# 調べものログ（知識ログアプリ）

スマホの読書中・移動中に気になった人物・用語・出来事をその場で1タップ送信し、
週1回まとめてWeb検索＋要約し、メールでダイジェストを受け取るツール。
最終的にはメール本文をコピーしてObsidianに貼り付ける想定。

## 全体の流れ

```
[iPhone PWA] --POST--> [GAS Web App] --追記--> [中継スプレッドシート]
                                                        |
                                          （週次トリガー）|
                                                        v
                                          [GAS 週次バッチ]
                                          Claude API + web_search で要約
                                                        |
                                                        v
                                          [Gmail: 週次ダイジェストメール]
                                                        |
                                          （手動コピペ）  |
                                                        v
                                              [Obsidian Vault]
```

## フォルダ構成

```
知識ログ/
├── CLAUDE.md         ← この設定手順書
├── pwa/               ← スマホ側キャプチャ画面（PWA）
│   ├── index.html
│   ├── app.js          （送信処理・オフラインキュー）
│   ├── manifest.json
│   └── service-worker.js
└── gas/                ← Google Apps Script（1つのGASプロジェクトにまとめる）
    ├── appsscript.json
    ├── Config.gs        （非秘密設定：シートID・送信先メール・モデル名）
    ├── WebApp.gs         （doPost：スマホからの受信 → シートへ追記）
    └── WeeklyBatch.gs    （週次処理：Claude要約 → メール送信）
```

---

## セットアップ手順

### 1. 中継スプレッドシートを作成

新規スプレッドシートを1つ作成し、そのIDを控える（URLの `/d/` と `/edit` の間の文字列）。

### 2. GASプロジェクトを作成

Google Apps Script（script.google.com）で新規プロジェクトを作成し、`gas/` フォルダの4ファイルの内容を貼り付ける。

- `appsscript.json` は「プロジェクトの設定」→「"appsscript.json" マニフェスト ファイルをエディタで表示する」を有効にしてから中身を貼り替える。

### 3. 非秘密設定を編集

`Config.gs` の `CONFIG` を実際の値に書き換える：

```js
const CONFIG = {
  QUEUE_SHEET_ID:   '手順1で控えたスプレッドシートID',
  QUEUE_SHEET_NAME: 'キュー',
  DIGEST_TO:        '自分のGmailアドレス',
  CLAUDE_MODEL:     'claude-opus-5',
};
```

### 4. 秘密情報をスクリプトプロパティに登録

GASエディタ左メニュー「プロジェクトの設定」→「スクリプト プロパティ」で以下を追加：

| プロパティ名 | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `SHARED_TOKEN` | 自分で決めた適当な文字列（PWA側の設定にも同じ値を入れる。推測されにくい長さがよい） |

### 5. スプレッドシートのヘッダーを作成

GASエディタで `setupSheet` 関数を選択して実行（初回のみ）。「タイムスタンプ／クエリ／状態／メモ」の見出し行ができる。

### 6. 週次トリガーを設定

`setupTrigger` 関数を実行（初回のみ）。毎週日曜20時に `weeklyDigest` が自動実行されるようになる。時間を変えたい場合は `WeeklyBatch.gs` の `setupTrigger()` 内の `.atHour(20)` を編集してから再実行する。

### 7. Web Appとしてデプロイ

「デプロイ」→「新しいデプロイ」→ 種類「ウェブアプリ」を選択：

- 実行するユーザー: **自分**
- アクセスできるユーザー: **全員**

デプロイ後に表示される `https://script.google.com/macros/s/xxxxx/exec` の形のURLを控える（PWA側の設定で使う）。

> 認証はGoogleログインではなく、手順4で決めた共有トークンで行う（`ANYONE_ANONYMOUS`設定でも、doPost内でトークンを照合しない限り誰でも書き込めてしまうので注意）。

### 8. PWAを公開する

`pwa/` フォルダ内の4ファイルをHTTPSで配信できる場所に置く（GitHub Pages、Firebase Hosting など。iPhoneで「ホーム画面に追加」するにはHTTPS配信が必要）。

このリポジトリはGitHub Pagesのルートとして公開されている場合、`知識ログ/pwa/` を配置してpushすれば `https://<公開ドメイン>/知識ログ/pwa/` でアクセスできる想定。ただしこのリポジトリのローカルmainと配信先リモートは分岐していることがあるため、pushする前に必ず `git status` / `git log` で差分を確認すること。

### 9. iPhoneで初期設定

1. Safariで公開したURLを開く
2. 共有ボタン →「ホーム画面に追加」
3. ホーム画面のアイコンから起動 →「⚙ 送信先の設定」で手順7のURLと手順4のトークンを入力して保存

---

## 動作確認

1. PWAから適当な語句を送信 → スプレッドシートに `pending` 行が追加されることを確認
2. GASエディタで `testRun` を実行 → ログで成功/失敗を確認、行が `processed` になっているか確認
3. 設定したGmailにダイジェストメールが届くか確認
4. メール本文をコピーしてObsidianに貼り付け、Markdownとして正しく表示されるか確認（要実機確認 — うまく崩れる場合はメール送信部分の改行コード処理を見直す）

## 診断

`checkConfig` 関数を実行すると、設定値・APIキー・トークンの登録状況・スプレッドシートへのアクセス可否をログに出力する。
