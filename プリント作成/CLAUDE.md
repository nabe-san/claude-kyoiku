# CLAUDE.md — プリント作成

このフォルダ専用の指示書。`generate.py`・`build_docx.py` の動作・デザイン設計はここを優先する。

---

## 目的

教科書画像から「生徒作業用プリント」と「模範解答」をWordで自動生成する。
両者は同じレイアウト関数（`build_docx.py`）から生成され、解答欄の中身以外は完全に同一デザインになる。
これにより、Claude.aiのプロジェクト機能でその場アーティファクト生成していた頃に起きていた
「生成のたびに枠幅・デザインがブレて手直しが必要」という問題を構造的になくす。

このツールの設計原則は、ケンゴさんがClaude.aiプロジェクト「歴史総合プリント作成」に
与えていた指示書（下記に統合済み）を踏襲している。

---

## フォルダ構造

```
プリント作成/
├── CLAUDE.md
├── generate.py          # Phase1(教科書分析) + Phase2(Claude→JSON構造) + Phase3呼び出し
├── build_docx.py         # structure.json → 学生用/模範解答 docx を固定テンプレで生成（API不要・再実行可）
├── requirements.txt
├── .env                  # ANTHROPIC_API_KEY
└── output/
    └── <教科書フォルダ名>/
        ├── structure.json       # Phase2の構造化出力（再利用・デザイン再調整用）
        ├── <タイトル>_学生用.docx
        └── <タイトル>_模範解答.docx
```

入力は `教科書/歴史総合/第N回_タイトル/`（`--subject 公共` で `教科書/公共/` も指定可）。
Phase1の分析結果は `教科書/分析キャッシュ/<フォルダ名>.json` に保存し、
`テスト問題作成/generate.py` と同じ場所・同じ形式を使う。どちらかで既に分析済みの単元は
API呼び出し不要で再利用できる。

---

## 実行方法

```bash
cd プリント作成
python generate.py                          # 教科書/歴史総合・公共 配下の未処理フォルダを一括生成
python generate.py --subject 歴史総合        # 科目を絞る
python generate.py 第6回_変容する東アジア     # フォルダ名指定で1件だけ
python generate.py --force                  # 出力済みも再生成

python build_docx.py 第6回_変容する東アジア   # structure.json からデザインだけ再描画（API不要）
```

出力済み判定は「学生用.docx・模範解答.docx が両方揃っているか」（`build_docx.is_done()`）。

---

## 処理フロー

```
教科書/<科目>/<授業回>/画像
      ↓
  Phase 1（テスト問題作成と共有キャッシュ）
  Claude Vision で画像を分析 → 教科書/分析キャッシュ/<授業回>.json
      ↓
  Phase 2
  分析テキスト → Claude が「プリントの構造」をJSONで設計 → output/<授業回>/structure.json
      ↓
  Phase 3（build_docx.py・API不要）
  structure.json → 学生用.docx（解答欄は空欄）
                 → 模範解答.docx（解答欄は解答＋ポイント）
```

デザインだけ直したい場合は Phase 3 だけを再実行すればよい（`python build_docx.py <フォルダ名>`）。

---

## 問いの設計原則（Phase2プロンプトの核）

- 教科書に掲載されている問いを中心に組み立てる。**教科書の問いに無駄なものはない**ので、できる限りそのまま使う
- **教科書にない問いは原則加えない**（一問一答的な暗記問題も作らない）
- 問いは「答えることで歴史の解像度が上がる」流れになるよう配列する（「〜は誰か」ではなく「なぜ〜か」「〜の結果どうなったか」「〜の意義は何か」）
- 問いの文中にすでに資料番号がある場合は参照の追記は不要。資料番号がない問いにのみ `reference` で参照先を補う

## プリントの構成原則

- 冒頭：単元タイトル（プレーン見出し）→ 大きな問い（ネイビー帯）→ テーマへのアプローチ（2〜3本柱の一覧表）
- 各セクションが「導入→展開→合流→帰結→まとめ」の論理的な流れでつながるよう配列し、
  セクション帯の副題で「テーマ①」「テーマ①②の合流点」「テーマ②の帰結」のように対応する観点を明示する
- 各史料・重要語句の近くに「キーワード整理」（用語解説テーブル）を適宜配置する
- 一次史料を使う設問には、資料の内容を「補助資料」ボックスとしてその設問の直前に配置する
- 2つの対象を比較させる設問は2列テーブル形式にする
- 最後のセクションは必ず「まとめ」：大きな問いの再掲＋指定語句を使った記述形式の模範解答
- 資料の図版・年表そのものはプリントに載せない（生徒は教科書を見ながら取り組むため）

## ヒントの設計原則

- 難しい問い（背景知識・論理の補助が必要、または問いの意図が分かりにくい）にのみ付ける
- 易しい問い（史料に答えが直接書いてある）・中程度の問い（複数史料を結びつける）はヒントなし
- 形式：「💡 ヒント：〜」で一言のみ。なるべく自力で考えさせる

## 模範解答の作成原則

- 各問いの模範解答は教科書の本文・史料・用語解説の内容に基づいて作成する
- 比較問いは2列対照表で示す
- 各解答の末尾に「▶ ポイント：」（キーワード・論理の確認事項）を付記する
- まとめの模範解答は指定語句をすべて使って作成する

---

## structure.json のスキーマ

```json
{
  "title": "第N回　単元タイトル",
  "big_question": "単元を貫く大きな問い",
  "page_range": "pp.86-89（分からなければnull）",
  "subject": "歴史総合（generate.pyが自動設定）",
  "overview_questions": ["観点1", "観点2", "観点3"],
  "sections": [
    {
      "roman": "I",
      "heading": "セクション見出し",
      "subtitle": "テーマ① など",
      "items": [
        {"type": "glossary", "label": "▼ キーワード整理 か null", "terms": [{"term": "...", "definition": "..."}]},
        {"type": "question", "number": 1, "text": "...", "hint": "null可", "reference": "null可", "answer": "...", "point": "null可"},
        {"type": "supplementary", "label": "補助資料　図②「〇〇」の内容", "body": "..."},
        {"type": "comparison_question", "number": 3, "text": "...", "hint": "null可", "columns": ["列1", "列2"], "answers": ["...", "..."], "point": "null可"}
      ]
    },
    {
      "roman": "IV",
      "heading": "まとめ",
      "subtitle": "テーマ①②③",
      "items": [
        {"type": "summary", "central_question": "...", "vocabulary": ["語句1", "語句2"], "answer": "...", "point": "..."}
      ]
    }
  ]
}
```

`number` は question / comparison_question 共通でセクションをまたいだ通し番号。

---

## デザイン仕様（`build_docx.py`）

- フォント：游明朝のみ（本文・見出し共通。太字とサイズで階層化する）。
  `w:rFonts` は `w:eastAsia="游明朝"` と `w:hint="eastAsia"` のみ指定し、`w:ascii`/`w:hAnsi`/`w:cs` は設定しない
  （フォントのPC環境依存を避けるため）。Noto Serif CJK JPのdocx埋め込みは行っていない
  （同一PC内で生成・閲覧する用途のため優先度を下げた。必要になれば追加を検討する）
- カラー：ネイビー `1A3A5C`（大きな問い帯・セクション帯）／ブルー `2C5F8A`（見出し・補助資料ラベル）／
  ライトブルー `D6E8F5`（キーワード整理・テーマ番号セル・補助資料背景）／
  ゴールド `7B5E00`（ヒント文字・まとめの使用語句文字）
- 解答例（緑）の色は指示書に指定がなく、参考画像からの目視推定（`COLOR_GREEN_HEADER` / `COLOR_GREEN_BODY`）。
  実物と色味がズレていたらここを直接編集して再描画する
- 記入欄：横罫線なし・1行テーブルで作り、`w:cantSplit` でページまたぎを防止、
  高さは `w:trHeight`（行数×420dxa）で確保する（複数の空段落を積む方式は使わない）
- 学生用と模範解答は同じレイアウト関数から生成し、`add_answer_box(filled=...)` の引数だけが違う

---

## 改善時の編集ポイント

- **問いの生成内容・JSON設計を変えたい** → `generate.py` の `build_print_prompt` / `JSON_SCHEMA_EXAMPLE`
- **色・余白・罫線・フォントサイズを変えたい** → `build_docx.py` のデザイン定数・各 `add_*` 関数
  （Claude APIを呼び直さず `python build_docx.py <フォルダ名>` で再描画できる）
- **教科書分析の精度を上げたい** → `generate.py` の `ANALYSIS_PROMPT`
  （`テスト問題作成/generate.py` と同じキャッシュを共有するため、両ツールに影響する点に注意）

---

## 開発環境

- Python 3.10 以上
- API: Anthropic Claude（`claude-sonnet-4-6`）
- 依存ライブラリ: `anthropic`, `python-docx`, `Pillow`, `python-dotenv`
- `.env` に `ANTHROPIC_API_KEY=sk-ant-...` を設定する
