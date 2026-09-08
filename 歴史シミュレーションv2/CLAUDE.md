# 歴史シミュレーションv2 — CLAUDE.md

高校生向け歴史人物視点シミュレーションゲーム（ビジュアルノベル形式）のv2。  
v1（歴史シミュレーション）からUI・画像管理を全面刷新。現在は **JSONシナリオ + 共通プレイヤー** を基本形とする。

---

## v1 との主な違い

| 項目 | v1 | v2 |
|---|---|---|
| 人物写真 | `images/`フォルダ参照（相対パス） | **Base64埋め込み**（HTML内に直接エンコード） |
| ステージ背景 | 真っ黒なグラデーション | **暖色系グラデーション**（写真が見えやすい） |
| キャラクター位置 | 中央 | **中央**（変わらず） |
| ゲームHUD | なし（v1も元々シンプル） | **なし**（ハート・好感度・メニューバー不要） |
| ステージ高さ | 420px | **460px** |

---

## フォルダ構造

```
歴史シミュレーションv2/
├── CLAUDE.md                     ← この指示書
├── リファレンス.md                ← 読書データ・参考資料・概念一覧・UIデザインルール
├── index.html                    ← シナリオ選択トップ画面（scenarios.jsonを読む）
├── player.html                   ← JSON共通プレイヤー
├── scenarios.json
├── assets/portraits/              ← 生徒画面で使う人物イラスト                ← トップ画面のシナリオ一覧
├── JSON化メモ.md                 ← JSON運用メモ
└── scenarios/
    ├── _json_template/
    │   └── scenario.json         ← JSONシナリオ作成用テンプレート
    ├── _template/
    │   └── index.html            ← 旧HTML作成用テンプレート（原則使わない）
    ├── 01_日露戦争_桂太郎/
    │   ├── scenario.json         ← 生徒用JSONシナリオ
    │   ├── index.html            ← JSON版への案内・リダイレクト
    │   └── index_legacy.html     ← 先生用旧HTML確認（?teacher=1 のみ）
    └── 02_帝国主義_ドゥメール/
        ├── scenario.json
        ├── index.html
        └── index_legacy.html     ← 先生用旧HTML確認（?teacher=1 のみ）

../歴史シミュレーションv2_public/
├── index.html
├── player.html
├── scenarios.json
├── assets/portraits/              ← 生徒画面で使う人物イラスト
└── scenarios/*/scenario.json      ← 生徒公開用。先生用ファイルは入れない
```

---

## 現在の運用ルール（重要）

### 生徒用はJSON版を使う

- 生徒用の正規版は `player.html` + 各シナリオの `scenario.json`。
- トップ画面 `index.html` は `scenarios.json` を読み、`data` に指定されたJSONを `player.html?data=...` で開く。
- 新規シナリオは原則 `scenarios/_json_template/scenario.json` をもとに作る。
- 旧HTML直書き方式は新規作成では使わない。

### 対象読者の語句レベル

| 対象 | 語句の基準 |
|------|-----------|
| 高校生（デフォルト） | 教科書レベルの用語を使ってよい。専門語には短い補足を付ける |
| 中学生 | 難語は使わず「〜という」で言い換える。カタカナ固有名詞には読み仮名か説明を添える |

中学生向けシナリオを作る場合は `meta.gradeLevel: "middle"` を入れ、語句の難易度を下げること。

### 架空の人物を主人公にする場合

実在の歴史的人物ではなく架空の人物（民衆・商人・学生など）を主人公にする場合は：

- `meta.protagonistType: "fictional"` を設定すること
- これにより結果画面の表示が「史実と一致」→「歴史の流れに沿った選択」に自動で切り替わる
- `isHistorical: true` の選択肢は「当時の多くの人々が実際に選んだ行動」を表す
- `historicalText` は「なぜその選択が歴史的に多数派だったか」を説明する文にする

### プロローグシーン（時代背景説明）

シナリオが短い場合や、授業で十分な背景知識がない場合は、`prelude` という名前の `story` パッセージを最初に入れること。

- `"start": "prelude"` に設定し、`prelude.next` で `scene01` に繋げる
- `tl: 0` を設定（タイムライン上では最初の位置）
- 内容：①時代の構造（帝国主義・国際関係）②登場する国々の思惑 ③主人公が置かれた社会の説明
- 決断は入れない。`status` ブロックで登場国の思惑を箇条書きにすると見やすい

### JSONシナリオで必ず入れる項目

- `meta.title`, `meta.titleHtml`, `meta.bigQuestion`, `meta.description`
- `meta.scenarioPoints`：タイトル画面に出す「シナリオの要点」
- `passages`：タイトル・物語・決断・終了画面
- `ending.narration`：エピローグ
- `ending.learningPoints`：終了画面に出す「このシミュレーションで学ぶこと」
- `ending.conceptCards`：歴史的概念カード

`learningPoints` は生徒に考えさせる振り返りではなく、先生側から短文で示し、生徒が紙のプリントに転記しやすい形にする。

### 人物画像は生成イラストを使う

- 生徒用に表示する人物画像は、写真ではなく授業用の生成イラストを基本にする。
- 画像は `assets/portraits/` に置き、`scenarios.json` の `image` と各 `scenario.json` の `characters.protagonist.photo` から参照する。
- `meta.imageNote` に「人物画像は授業用イメージです。」を入れ、史料写真そのものではないことを示す。

### 旧HTML版は先生用だけ

- `index_legacy.html` は教材作成・比較確認用のバックアップ。
- 通常アクセスでは「先生用の旧HTML版です」という案内だけ表示する。
- 先生が旧版を確認するときだけ `index_legacy.html?teacher=1` を使う。
- 生徒用導線から `index_legacy.html` へのリンクを出さない。

### 生徒公開用フォルダ

- 生徒公開用は `../歴史シミュレーションv2_public/`。
- このフォルダには `index.html`, `player.html`, `scenarios.json`, `scenarios/*/scenario.json`, `assets/portraits/*`, `.nojekyll` だけを入れる。
- `CLAUDE.md`, `JSON化メモ.md`, `_template`, `_json_template`, `index_legacy.html` は公開用に入れない。
- シナリオを更新したら、開発用 `歴史シミュレーションv2/` だけでなく公開用 `歴史シミュレーションv2_public/` にも反映する。

### GitHub Pages公開

- リポジトリ：`nabe-san/claude-kyoiku`
- 公開URL：`https://nabe-san.github.io/claude-kyoiku/`
- ルート `index.html` は `歴史シミュレーションv2_public/` へリダイレクトする。
- GitHub Actions：`.github/workflows/deploy-history-simulation.yml`
- 公開前に、公開用フォルダへ先生用ファイルが混ざっていないか検索する。

## シナリオ作成手順

### Step 1：人物・テーマ選定
- 教科書画像をアップロード → Claudeが登場人物・概念候補を提案
- 各候補に対して「このシナリオが深めさせる中核的な概念」を1〜2個提示する
- **先生の確認を取ってから Step 2 へ**（概念とシナリオの両方を確認）
- 対象概念は `リファレンス.md` の「中核的な概念一覧」セクションから選ぶ

### Step 2：資料収集
以下の優先順位で参照：
1. **最優先：ローカル読書データ**（`../books/`）→ 詳細は `リファレンス.md` の「参照できる読書データ」セクション
2. **概念確定の参照：中核概念参考資料**（`../参考資料/`）→ 詳細は `リファレンス.md` の「参照できる参考資料」「中核的な概念一覧」セクション
3. **補助：ウェブ検索**（上記に該当資料がない場合のみ）

### Step 3：JSONテンプレートをコピーして編集

```powershell
Copy-Item -Recurse "scenarios/_json_template" "scenarios/XX_タイトル_人物名"
```

`scenarios/XX_タイトル_人物名/scenario.json` を編集する。主な編集箇所：
- `meta`（タイトル・大きな問い・シナリオの要点）
- `characters`（登場人物・役割・写真）
- `timeline`
- `passages`（物語・決断・結果解説）
- `ending`（エピローグ・学びの要点・概念カード）

### Step 4：scenarios.json（トップ画面）にカードを登録する

`歴史シミュレーションv2/scenarios.json` にカード情報を追加する。生徒用に開くシナリオは `url` ではなく `data` を指定する。`image`（カードの扉絵）は Step 5 のスクリプトが自動で設定するので、この時点では省略してよい。

```json
{
  "id": "example_id",
  "title": "シナリオ名",
  "tag": "単元名",
  "data": "scenarios/XX_タイトル_人物名/scenario.json",
  "status": "ready"
}
```

### Step 5：人物イラスト・ヒーロー画像を自動生成する

人物イラスト（`characters.*.photo`）とカード扉絵・タイトル画面のヒーロー画像（`scenarios.json` の `image` / `scenario.json` の `meta.heroImage`）は、**`generate_portraits.py` で自動生成する**。手動でのダウンロード・Base64貼り付けは行わない。

1. `portraits_todo/XX_タイトル_人物名.json` をキューファイルとして作成する（既存シナリオのファイルを参考にする）。登場人物ごとに1件（`type`省略で人物イラスト扱い）、扉絵用に1件（`type: "hero"`）を書く。

```json
[
  {
    "id": "character-id",
    "prompt": "英語での見た目の説明（年代・服装・表情・背景色のヒントなど）",
    "scenario": "scenarios/XX_タイトル_人物名/scenario.json",
    "characterKey": "protagonist"
  },
  {
    "id": "scene-id-hero",
    "type": "hero",
    "prompt": "英語での場面の説明（登場人物・状況・構図・雰囲気など）",
    "scenario": "scenarios/XX_タイトル_人物名/scenario.json",
    "scenarioListId": "example_id"
  }
]
```

2. `python generate_portraits.py portraits_todo/XX_タイトル_人物名.json --dry-run` でプロンプトを確認する（課金なし）。
3. 問題なければ `python generate_portraits.py portraits_todo/XX_タイトル_人物名.json` を実行する（OpenAI APIの課金が発生する。先生に一言確認してから実行する）。
4. 実行すると自動的に反映される：
   - `assets/portraits/<id>.webp` / `assets/scenes/<id>.webp`（開発用・公開用の両方）
   - 各 `scenario.json` の `characters.<characterKey>.photo` または `meta.heroImage`（開発用・公開用の両方。公開用にまだシナリオが無ければスキップ）
   - `scenarios.json` の該当カードの `image`（開発用・公開用の両方）

画風は既存シナリオと統一されるよう `generate_portraits.py` 内の `PORTRAIT_STYLE_PREFIX` / `HERO_STYLE_PREFIX` で共通指定している（変更不要）。

### Step 6：公開用フォルダへの反映を確認する

画像・`scenarios.json`・各シナリオの `photo`/`heroImage` は Step 5 のスクリプトが開発用・公開用の両方に書き込み済み。残っているのは本文（`meta`・`passages`・`ending` など）の反映のみ：

- `../歴史シミュレーションv2_public/scenarios/XX_タイトル_人物名/scenario.json` に本文の変更を反映する

公開用フォルダに `index_legacy.html` や先生用メモを入れない。

---

## リファレンス（読書データ・参考資料・概念一覧・UIデザインルール）

シナリオ作成時に参照する固定データ（`../books/` 書籍一覧、`../参考資料/` ファイル一覧、中核的な概念一覧、カラーパレット・フォントサイズ等のUIデザインルール）は `リファレンス.md` にまとめている。参照手順もそちらに記載。

**唯一ここで運用ルールとして明記する点：** `speaker: null`（ナレーション）の行はセリフボックスに名前ラベルを出さないが、ステージには `protagonist` の写真を表示する（テンプレートエンジンに実装済み・変更不要）。新シナリオで `speaker: null` を多用してもシルエット化しない設計になっている。

---

## 構成パターン（テンプレートに準拠）

1. **タイトル画面**
   - 大きな問い
   - シナリオ説明
   - シナリオの要点（`meta.scenarioPoints`）
2. **導入シーン**（背景・人物紹介・状況説明）
3. **決断①〜③/④**（A/B/C選択 → 結果 → 史実解説）
4. **エンディング**
   - エピローグ
   - 選択記録
   - 学びの要点（`ending.learningPoints`）
   - 歴史的概念カード

---

## シナリオ設計の原則

### 教育目標
- 生徒が「当時の人物・立場の制約」を体感する
- 「なぜそう判断したか」の合理性を理解させる（**正解当てゲームにしない**）
- **各シナリオは必ず1〜2個の「中核的な概念」の理解を深めることを主目的とする**
- エンディングの概念カード4枚は、対象概念に直接つながる内容にする

### 決断場面の設計ルール
- 選択肢は2〜3個（多すぎない）
- 各選択肢に「当時の視点からは合理的に見える理由」を設ける
- 「正解」は史実の選択だが、それを押し付けない説明文にする
- 制約（財政・軍事・国際関係・国内政治）を必ず絡める

### 人物・立場の選び方の目安
- 高校「歴史総合」「日本史探究」の教科書に登場する人物・集団
- 明確な「決断の場面」が複数ある人物（単純な英雄譚にしない）
- 複数の視点・立場が存在する歴史的場面の中心人物
- プレイヤーの立場は特定の人物に限らず、**民衆・労働者・国民・植民地の人々などの抽象的な立場でもよい**

---

## commitルール

改善作業が完了したら必ず git commit を提案する（自動では行わない）。  
コミットメッセージ例：`歴史シミュレーションv2：桂太郎シナリオ追加`

---

## 既存シナリオ

| フォルダ名 | 人物 | 授業回（教科書単元） | 対象概念 | 状態 |
|---|---|---|---|---|
| `_json_template/` | JSONテンプレート | ─ | ─ | 完成 |
| `_template/` | 旧HTMLテンプレート | ─ | ─ | 参考用 |
| `01_日露戦争_桂太郎/` | 桂太郎 | 第7回 日露戦争 | ② 因果と帰結・④ 歴史的パースペクティブ | 完成 |
| `02_帝国主義_ドゥメール/` | ポール・ドゥメール | 第5回 帝国主義 | ⑨ 帝国主義と植民地主義・⑤ 解釈と論争性 | 完成 |
| `03_帝国主義_イラン立憲革命/` | アリー（架空・中学生向け） | 帝国主義単元 | ⑨ 帝国主義と植民地主義・④ 歴史的パースペクティブ | 完成（要イラスト）|
| `04_日露戦争影響_ドンズー運動/` | ファン・ボイ・チャウ | 日露戦争の影響単元 | ⑨ 帝国主義と植民地主義・② 因果と帰結 | 完成 |
| `05_ロシア革命_レーニン/` | レーニン | 戦争と社会主義単元 | ② 因果と帰結・⑬ 自由と統治（権力と権利） | 完成 |

