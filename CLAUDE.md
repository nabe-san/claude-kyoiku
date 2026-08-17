# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このフォルダについて

高校教員（日本史・公共・探究）の業務自動化・授業改善を目的とした作業フォルダ。
Claude Code をここで起動して作業する。

---

## フォルダ構造と用途

```
claude開発/
├── .claude/
│   ├── settings.json       ← ツール使用許可設定
│   └── commands/           ← スキル定義（スライド作成・一問一答・授業自動生成・確認テスト）
├── CLAUDE.md               ← この指示書
│
├── 教科書/                 ← 教科書画像の一元管理フォルダ（全ツール共通の入力元）
│   ├── 歴史総合/           ← 歴史総合の教科書画像（試験範囲フォルダごとに整理）
│   │   └── 第N回_タイトル/ ← 教科書画像 (.jpg/.png)
│   ├── 公共/               ← 公共の教科書画像（試験範囲フォルダごとに整理）
│   │   └── 第N回_タイトル/
│   └── 分析キャッシュ/     ← Claude Vision による画像分析結果 (.json)
│
├── スライド作成/            ← 対話型AI → 授業スライド .pptx 自動生成（歴史総合・公共）
│   ├── input/
│   │   ├── texts/          ← 教科書テキスト（.txt または .docx）
│   │   └── memos/          ← 箇条書きメモ（.txt または .docx）
│   ├── output/             ← 生成された .pptx
│   ├── templates/          ← スライドテンプレート置き場
│   ├── generate.py
│   ├── build_from_json.py
│   └── requirements.txt
│
├── テスト問題作成/          ← 教科書画像 → 4択テスト問題 Word出力
│   ├── input/
│   │   ├── past_exams/     ← 過去問ファイル
│   │   └── worksheets/     ← ワークシート
│   ├── output/             ← 生成されたWord（サブフォルダで試験名管理）
│   ├── exam_config.yaml    ← テスト設定（使用する教科書フォルダのパスをここで指定）
│   ├── generate.py
│   └── requirements.txt
│
├── 一問一答/               ← 教科書画像 → 一問一答カード Word + Google Forms 出力
│   ├── output/
│   │   └── 第N回_タイトル/ ← 教科書/以下と同名フォルダに Word が自動出力される
│   ├── generate_anki.py    ← 一問一答カード生成（教科書/ 以下のフォルダを参照）
│   ├── generate_quiz.py    ← Google Forms クイズ生成
│   ├── gas_anki.js         ← Google Apps Script（Anki連携）
│   ├── gas_quiz.js         ← Google Apps Script（クイズ連携）
│   └── requirements.txt
│
├── 授業自動生成/           ← 教科書画像 → 一問一答カード・テスト問題・文字資料を一括生成
│   ├── output/
│   │   └── 第N回_タイトル/ ← 教科書/以下と同名フォルダに自動出力
│   │       ├── analysis.txt
│   │       ├── 一問一答カード.docx
│   │       ├── テスト問題.docx
│   │       └── 文字資料.docx
│   ├── generate.py         （教科書/ 以下のフォルダを参照）
│   └── requirements.txt
│
├── プリント作成/           ← 教科書画像 → 生徒作業用プリント＋模範解答（固定テンプレ・Word）
│   ├── output/
│   │   └── 第N回_タイトル/ ← 教科書/以下と同名フォルダに自動出力
│   │       ├── structure.json      ← Phase2構造化データ（デザイン再描画用）
│   │       ├── <タイトル>_学生用.docx
│   │       └── <タイトル>_模範解答.docx
│   ├── generate.py         （Phase1分析＋Phase2 JSON生成。教科書/分析キャッシュ をテスト問題作成と共有）
│   ├── build_docx.py       （JSON→Word。デザイン調整はここだけでAPI不要）
│   └── requirements.txt
│
├── books/                  ← 参照用読書データ（.txt）歴史シミュレーションv2・授業自動生成で共有
│
├── Obsidian連携/           ← Obsidian Vault（デスクトップの MyObsidian）へのログ取り込み
│   ├── import_claude_code_logs.py  ← Claude Codeのセッション履歴をMarkdown化
│   ├── import_chat_exports.py      ← ChatGPT/Claude.aiのエクスポートをMarkdown化
│   ├── import_books.py             ← books/ の読書テキストを参考文献ノートにMarkdown化
│   └── _inbox/             ← ChatGPT/Claude.aiのエクスポートZIPの置き場
│
├── 歴史シミュレーションv2/        ← 開発用（JSONシナリオ・先生用legacy含む）
│   ├── index.html          ← シナリオ選択トップ画面
│   ├── player.html         ← JSON共通プレイヤー（ポートレート・ヒーロー画像表示対応）
│   ├── scenarios.json      ← シナリオ一覧
│   ├── CLAUDE.md           ← シナリオ設計の詳細指示書
│   ├── assets/
│   │   ├── portraits/      ← 登場人物ポートレート画像（katsura-taro.webp 等）
│   │   └── scenes/         ← シナリオヒーロー画像（*-hero.webp）
│   └── scenarios/
│       ├── 01_日露戦争_桂太郎/
│       ├── 02_帝国主義_ドゥメール/
│       ├── _json_template/
│       └── _template/
│
├── 歴史シミュレーションv2_public/ ← 生徒公開用（GitHub Pages対象）
│   ├── index.html
│   ├── player.html
│   ├── scenarios.json
│   ├── assets/
│   │   ├── portraits/      ← 登場人物ポートレート画像
│   │   └── scenes/         ← シナリオヒーロー画像
│   └── scenarios/
│
├── 参考資料/               ← 授業設計の参考資料（中核概念モデル等）
│
├── 授業記録/               ← Notta .txt → 授業記録PDF + Google Classroom 配信
│   ├── appsscript.json     ← GAS プロジェクト設定
│   └── gas_lesson.js       ← Google Apps Script 本体
│
├── 知識ログ/               ← スマホ発の調べものメモ → 週次Claude要約 → メールダイジェスト
│   ├── CLAUDE.md           ← セットアップ手順書
│   ├── pwa/                ← スマホ側キャプチャ画面（PWA。index.html/app.js/manifest.json/service-worker.js）
│   └── gas/                ← GASプロジェクト（Web App受信 + 週次バッチ）
│
└── rekishi-hp_ARCHIVED/    ← 【凍結・Git非管理】歴史教師の探究ノートは独立リポジトリに移行済み（2026-07-27）
                              　今後の開発は C:\projects\rekishi-hp（nabe-san/rekishi-hp, Vercel本番接続）で行う
                              　このフォルダはローカル参照専用。中身は更新しない
```

---

## 各ツールの実行方法

### スライド作成
```bash
cd スライド作成
pip install -r requirements.txt   # 初回のみ
# input/texts/ に教科書テキスト(.txt/.docx)を、input/memos/ にメモ(.txt/.docx)を置く
# .env に OPENAI_API_KEY を設定する
python generate.py
```

### テスト問題作成
教科書画像 → 4択テスト問題（Word出力）。実行方法・出題方針は `テスト問題作成/CLAUDE.md` を参照。

### 一問一答
教科書画像 → 一問一答カード（Word + Google Forms）。実行方法・生成ルールは `一問一答/CLAUDE.md` を参照。スキル `/一問一答` からも実行できる。

### 授業自動生成
教科書画像 → 一問一答カード・テスト問題・文字資料を一括生成。実行方法・各出力物の方針は `授業自動生成/CLAUDE.md` を参照。スキル `/授業自動生成` からも実行できる。

### プリント作成
教科書画像 → 生徒作業用プリント＋模範解答（固定テンプレのWord）。実行方法・デザイン仕様は `プリント作成/CLAUDE.md` を参照。

### 歴史シミュレーション
- 生徒用公開URL: `https://nabe-san.github.io/claude-kyoiku/歴史シミュレーションv2_public/`
- 先生は `歴史シミュレーションv2/` を編集する。生徒公開用は `歴史シミュレーションv2_public/` に反映する
- JSON版はローカルサーバー経由で確認する。例: `cd 歴史シミュレーションv2_public` → `python -m http.server 8000`
- シナリオ本文は各 `scenario.json`、一覧カードは `scenarios.json`、共通表示は `player.html` を更新する
- 画像は `assets/portraits/` と `assets/scenes/` に置き、公開時はWebPなど軽量な形式を使う
- 更新後は公開用フォルダも確認し、必要な変更だけをコミットして GitHub に push する

### 授業記録（Google Apps Script）
- `授業記録/gas_lesson.js` を Google Apps Script エディタに貼り付けてデプロイする
- `gas_lesson.js` 冒頭の `SUBJECTS` 定数に Google Drive フォルダIDと Classroom IDを設定する
- スクリプトプロパティに `ANTHROPIC_API_KEY` を登録する
- `checkAndProcess()` をトリガー（例：毎時実行）に設定すると自動処理される

### 調べものログ（知識ログアプリ）
スマホ（PWA）で調べたい語句を1タップ送信 → 中継スプレッドシートに蓄積 → 週次でClaude（Web検索ツール）が出典つき要約を生成 → メールダイジェストで届く。実行方法・セットアップ手順は `知識ログ/CLAUDE.md` を参照。

### Obsidian連携
Obsidian Vault（デスクトップの `MyObsidian`）を「第二の脳」として使うため、各種チャットログをMarkdown化して取り込む。
```bash
cd Obsidian連携
# Claude Codeのセッション履歴（~/.claude/projects/以下）を取り込む
python import_claude_code_logs.py
# → MyObsidian/ログ/ClaudeCode/<プロジェクト名>/ に出力（再実行で差分反映）

# ChatGPT / Claude.aiのエクスポートを取り込む
# 1. ChatGPT: 設定 → データ管理 → データをエクスポート
#    Claude.ai: 設定 → アカウント → データをエクスポート
# 2. メールで届いたZIPを Obsidian連携/_inbox/ に置く
python import_chat_exports.py
# → MyObsidian/ログ/ChatGPT/ または MyObsidian/ログ/Claude/ に出力

# books/ の読書テキスト（歴史シミュレーションv2・授業自動生成と共有）を参考文献ノート化
python import_books.py
# → MyObsidian/参考文献/ に出力
```
`import_chat_exports.py` は公開されているエクスポート形式をもとに書いているが、実際のZIPの中身で形式が微妙に違う場合は都度調整する。

---

## 共通ルール

- `input/` にファイルを置いてからスクリプトを実行する
- 出力は必ず `output/` に保存する
- `.env` に APIキーを設定する（各ツールフォルダに置く）
  - Anthropic 系ツール: `ANTHROPIC_API_KEY=sk-ant-...`、モデルは `claude-sonnet-4-6`
  - スライド作成: `OPENAI_API_KEY=sk-...`、モデルは `gpt-4o`

---

## 私について（Claude への指示）

**職種:** 高校教員（日本史・公共・探究）  
**目的:** 授業の質向上・業務効率化・AI活用  
**対象生徒:** 高校生（1人1台PC・AI利用可）

---

## コミュニケーションルール

- 回答は必ず日本語
- フランクかつ論理的に説明する
- 抽象論ではなく具体例で示す
- 専門用語には簡潔な説明を付ける

---

## 授業設計の方針

### 目指す授業像
- 教員の説明は「生徒が考えるための前提」であり、説明だけで完結する授業にしない
- 生徒が資料・教科書をもとに重要な歴史的概念を**納得しながら**理解していく授業を目指す
- 「知識を知っている」ではなく「概念を自分の言葉で説明できる・他の出来事と結び付けられる」状態が理解の証

### 知識習得フェーズ
- **先行オーガナイザーを必ず提示する**：個別知識を教える前に、単元全体の構造・因果の骨格を示す
- 背景・因果関係をわかりやすく丁寧に伝える（ここは教員の役割）
- 一問一答形式は禁止

### 概念化フェーズ
- グループワーク後に「気づき」を書かせ、そこから概念への橋渡しをする
- **気づき→概念の橋渡しが最重要**：生徒が観察したことを抽象化・一般化するプロセスを必ず設計する
- AIを活用してソクラテス式対話で個別に概念理解を深める仕組みを組み込む

### 問いの設計
- 必ず「大きな問い」を単元に設定する
- 複数視点で考えさせる発問を用意する
- 意味・意義・関連・抽象化を促す問いを優先する

### 理解の評価基準
- 知識をより抽象的な言葉で説明できる
- 出来事の意味・意義について自分の言葉で語れる
- 他の出来事・現代と結び付けて説明できる
- 適切な言葉に言い換えて説明できる

---

## 出力ルール

- 構造化（見出し・箇条書き）する
- 実行可能な形で提案する
- 教育的価値を必ず示す
