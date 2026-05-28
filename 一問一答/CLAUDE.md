# CLAUDE.md — 一問一答

このフォルダ専用の指示書。スクリプトの動作・出力仕様はここを優先する。

---

## 目的

教科書の授業回画像（JPEG/PNG）から一問一答カードを自動生成し、Word と Google Forms（クイズモード）を出力する。

---

## フォルダ構造

```
一問一答/
├── CLAUDE.md               ← この指示書
├── generate_anki.py        ← 画像 → 一問一答カード（Word + Google Forms）
├── generate_quiz.py        ← 授業音声(MP3) → 4択確認テスト（Word）※別用途
├── gas_anki.js             ← Google Apps Script（Anki連携）
├── gas_quiz.js             ← Google Apps Script（クイズ連携）
├── requirements.txt
├── start_anki.bat          ← generate_anki.py の起動ショートカット
├── .env                    ← ANTHROPIC_API_KEY を記入
├── credentials.json        ← Google Forms API 認証ファイル（任意）
├── token.json              ← Google OAuth トークン（自動生成）
├── input/
│   └── 01_（授業回名）/    ← 授業回フォルダに教科書画像 (.jpg/.png) を入れる
│       ├── 画像1.jpg
│       └── 画像2.jpg
└── output/
    └── 01_（授業回名）/    ← input と同名フォルダに自動出力
        ├── 画像1.docx             ← 一問一答カード（印刷用Word）
        └── 画像1_form_url.txt     ← Google Forms の URL（credentials.json がある場合のみ）
```

---

## 実行方法

```bash
cd 一問一答
pip install -r requirements.txt   # 初回のみ
python generate_anki.py
```

または `start_anki.bat` をダブルクリックして起動。

スキルからも実行できる：Claude Code で `/一問一答` と入力。

---

## 動作フロー

```
input/<授業回フォルダ>/<画像>.jpg
        ↓
    Claude Vision で画像を解析
    → 一問一答カードを 20〜30 枚生成（JSON）
        ↓                      ↓
    Word 出力              Google Forms 作成
    output/.../画像.docx   output/.../画像_form_url.txt
                           （credentials.json がある場合のみ）
```

- **5分ごとに `input/` を自動監視**する（Ctrl+C で停止）
- すでに `output/` に同名 `.docx` があるフォルダ・画像はスキップ

---

## カード生成のルール（プロンプト仕様）

- 人名・地名・事件名・制度名・概念など重要語句を **1つだけ** 空欄にする
- 空欄は `＿＿＿＿` で表記
- 答えは空欄に入る語句のみ（1〜6語程度）
- **年号・西暦など「数字の年」を答えさせる問題は絶対に作らない**
- **1画像あたり 20〜30 枚**生成する
- 画像に写っている内容のみから出題する（推測や補足情報は使わない）
- モデル：`claude-sonnet-4-6`

---

## Word の出力形式

- タイトル行：`一問一答カード　{授業回名}　{画像名}`
- 2列テーブル：「問題（表）」列 + 「答え（裏）」列
- 奇数行：薄青（`#F4F6F9`）、偶数行：白（`#FFFFFF`）の交互配色
- 答えは赤字太字（`#C04508`）

---

## Google Forms 出力（任意設定）

`credentials.json` を配置すると、Word と同時に Google Forms（クイズモード・自動採点）を作成する。

### セットアップ
詳細手順は `README_FORMS_SETUP.txt` を参照。概要：
1. Google Cloud Console で Google Forms API を有効化
2. OAuth クライアント ID（デスクトップアプリ）を作成してJSONをダウンロード
3. `credentials.json` としてこのフォルダに配置
4. 初回実行時にブラウザで認証 → 以降は `token.json` で自動認証

**`credentials.json` がない場合**はWordのみ出力し、Forms生成をスキップ（エラーにはならない）。

---

## generate_quiz.py について

授業音声（MP3）→ 4択確認テストを生成する**別用途**スクリプト。  
入出力先が Google Drive (`G:\マイドライブ\生成AI【確認テスト】\`) にハードコードされており、`generate_anki.py` とは独立した運用。

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `anthropic` | Claude Vision API |
| `python-dotenv` | .env の読み込み |
| `python-docx` | Word ファイル出力 |
| `google-api-python-client` | Google Forms API |
| `google-auth-oauthlib` | Google OAuth 認証 |

---

## よくあるエラー

| エラー | 原因 | 対処 |
|---|---|---|
| `ANTHROPIC_API_KEY が見つかりません` | `.env` 未設定 | `.env` に `ANTHROPIC_API_KEY=sk-ant-...` を追記 |
| `JSONが見つかりませんでした` | Claude の応答が崩れた | 再実行（稀に発生） |
| `credentials.json がない` | Google Forms 未設定 | WordのみでOKなら無視してよい |
| 画像がスキップされる | `output/` に同名 `.docx` が存在 | 該当 `.docx` を削除して再実行 |
