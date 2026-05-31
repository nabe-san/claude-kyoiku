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
├── 授業自動生成/           ← 教科書画像 → 一問一答カード・テスト問題を一括生成
│   ├── output/
│   │   └── 第N回_タイトル/ ← 教科書/以下と同名フォルダに自動出力
│   │       ├── analysis.txt
│   │       ├── 一問一答カード.docx
│   │       └── テスト問題.docx
│   ├── generate.py         （教科書/ 以下のフォルダを参照）
│   └── requirements.txt
│
├── books/                  ← 参照用読書データ（.txt）歴史シミュレーションv2・授業自動生成で共有
│
├── 歴史シミュレーションv2/        ← 開発用（JSONシナリオ・先生用legacy含む）
│   ├── index.html          ← シナリオ選択トップ画面
│   ├── player.html         ← JSON共通プレイヤー
│   ├── scenarios.json      ← シナリオ一覧
│   ├── CLAUDE.md           ← シナリオ設計の詳細指示書
│   └── scenarios/
│       ├── 01_日露戦争_桂太郎/
│       ├── 03_帝国主義_ドゥメール/
│       ├── _json_template/
│       └── _template/
│
├── 歴史シミュレーションv2_public/ ← 生徒公開用（GitHub Pages対象）
│   ├── index.html
│   ├── player.html
│   ├── scenarios.json
│   └── scenarios/
│
├── 参考資料/               ← 授業設計の参考資料（中核概念モデル等）
│
└── 授業記録/               ← Notta .txt → 授業記録PDF + Google Classroom 配信
    ├── appsscript.json     ← GAS プロジェクト設定
    └── gas_lesson.js       ← Google Apps Script 本体
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
```bash
cd テスト問題作成
pip install -r requirements.txt   # 初回のみ
# exam_config.yaml の textbooks: に使用する教科書フォルダのパスを指定する
# 例: - "C:\Users\kengo\...\教科書\歴史総合\第7回 日露戦争"
python generate.py
```

### 一問一答
```bash
cd 一問一答
pip install -r requirements.txt   # 初回のみ
# 教科書/<科目>/<授業回フォルダ>/ に画像を置く（各ツール共通の置き場所）
python generate_anki.py
```
スキルからも実行できる：Claude Code で `/一問一答` と入力。

### 授業自動生成
```bash
cd 授業自動生成
pip install -r requirements.txt   # 初回のみ
# 教科書/<科目>/<授業回フォルダ>/ に教科書画像を置く（各ツール共通の置き場所）
python generate.py           # 未処理フォルダのみ生成
python generate.py --force   # 出力済みフォルダも強制再生成
```
スキルからも実行できる：Claude Code で `/授業自動生成` と入力。

### 歴史シミュレーション
- 単体HTMLファイルで動作。ブラウザで `歴史シミュレーションv2/scenarios/<シナリオ名>/index.html` を直接開く
- 新シナリオ作成は `歴史シミュレーションv2/CLAUDE.md` の手順に従う

### 授業記録（Google Apps Script）
- `授業記録/gas_lesson.js` を Google Apps Script エディタに貼り付けてデプロイする
- `gas_lesson.js` 冒頭の `SUBJECTS` 定数に Google Drive フォルダIDと Classroom IDを設定する
- スクリプトプロパティに `ANTHROPIC_API_KEY` を登録する
- `checkAndProcess()` をトリガー（例：毎時実行）に設定すると自動処理される

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
