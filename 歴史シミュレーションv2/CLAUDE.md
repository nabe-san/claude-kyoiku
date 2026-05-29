# 歴史シミュレーションv2 — CLAUDE.md

高校生向け歴史人物視点シミュレーションゲーム（ビジュアルノベル形式）のv2。  
v1（`../歴史シミュレーション/`）からUI・画像管理を全面刷新。HTML単体ファイルで動作。

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
├── index.html                    ← シナリオ選択トップ画面
└── scenarios/
    ├── _template/
    │   └── index.html            ← 新シナリオ作成用テンプレート
    └── 01_日露戦争_桂太郎/       ← （後で移植予定）
        └── index.html
```

---

## シナリオ作成手順

### Step 1：人物・テーマ選定
- 教科書画像をアップロード → Claudeが登場人物・概念候補を提案
- **先生の確認を取ってから Step 2 へ**（v1と同じ）
- 対象概念は `../歴史シミュレーション/CLAUDE.md` の中核概念一覧を参照

### Step 2：資料収集
v1と同じ優先順位で参照：
1. `../books/`（ローカル読書データ）
2. `../参考資料/`（中核概念参考資料）
3. ウェブ検索（上記にない場合のみ）

### Step 3：テンプレートをコピーして編集

```powershell
Copy-Item -Recurse "scenarios/_template" "scenarios/XX_タイトル_人物名"
```

`scenarios/XX_タイトル_人物名/index.html` を開き、★マークのついたセクションを編集する：
- `CHARS`（キャラクター定義・写真）
- `SCENARIO_TITLE`, `PLAYER_ROLE_DESC`, `TL`（タイムライン）
- `P`（ストーリーデータ）
- `ENDING_NARRATION`, `SCORE_EVALS`, `CONCEPT_CARDS`

### Step 4：写真をBase64でHTMLに埋め込む

```powershell
# ① 写真をダウンロード（Wikimedia Commons などから）
Invoke-WebRequest -Uri "https://upload.wikimedia.org/..." -OutFile "temp.jpg"

# ② Base64エンコード
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("temp.jpg"))

# ③ HTMLのCHARS定義に貼り付け
# photo: 'data:image/jpeg;base64,' + $b64  の形式で設定
```

HTMLの `CHARS` に設定：
```javascript
protagonist: {
  name: '桂太郎',
  photo: 'data:image/jpeg;base64,/9j/4AAQSkZJRgAB...',  // ← ここに貼る
  bg: 'linear-gradient(180deg, #6a7a5a 0%, #3a4a2a 100%)'
}
```

写真がない場合は `photo: null` → シルエットSVGが自動表示される。

### Step 5：index.html（トップ画面）を更新

`歴史シミュレーションv2/index.html` の `scenarios-grid` に新しいカードを追加する。

---

## UIデザインルール（v2）

### カラーパレット（変更しない）
v1と同じ。
- ページ背景：`#ede4cc`
- 対話ボックス：`#f5ead2` → `#ecddc0` → `#e6d6ae`
- 上辺ライン：金・深紅交互グラデーション
- アクセント金：`#c8a84b`
- アクセント深紅：`#8b2020`

### VNステージ（v2の変更点）
| 要素 | v1 | v2 |
|---|---|---|
| `.vn-stage` background | 黒 (`#080504`...) | **暖色グラデーション**（`CHARS[key].bg`で設定） |
| `.vn-stage` height | 420px | **460px** |
| `.char-photo` filter | sepia + contrast | **drop-shadow のみ**（自然な色で表示） |

### ナレーション行のステージ表示ルール（重要）
`speaker: null`（ナレーション）の行では、セリフボックスに名前ラベルは表示しないが、ステージには **`protagonist` の写真を表示する**。

```javascript
// テンプレートエンジンに実装済み（変更不要）
const displayKey = (!isStatus && !speakerKey) ? 'protagonist' : speakerKey;
```

- `speakerKey`（null）→ 名前ラベルなし
- `displayKey`（'protagonist'）→ ステージに主人公の写真を表示

このルールにより、ナレーションでシルエットが表示される問題が起きない。新シナリオで `speaker: null` を多用しても写真が消えない設計になっている。

### ステージ背景プリセット（`CHARS.bg` に設定可能）
```
室内・執務室: 'linear-gradient(180deg,#8a7a5a 0%,#5a4a30 100%)'
夜・屋外:    'linear-gradient(180deg,#2a3050 0%,#12183a 100%)'
明るい屋外:  'linear-gradient(180deg,#7a9a6a 0%,#4a6a3a 100%)'
戦場:        'linear-gradient(180deg,#5a5040 0%,#2a2010 100%)'
宮廷・赤:    'linear-gradient(180deg,#7a4040 0%,#401818 100%)'
```

### フォントサイズ基準
| 用途 | サイズ |
|---|---|
| VN対話テキスト（`.vn-text`） | 19px |
| 決断の文脈説明（`.decision-context`） | 17px |
| 選択肢ボタン（`.choice-btn`） | 17px |
| エンディング本文（`.narration`） | 18px |
| 概念カード本文（`.concept-body`） | 14px |

### 結果画面の視覚ヒエラルキー（変更しない）
1. **あなたの選択**（`.result-your`）：薄い青・小さめ
2. **一致/不一致バナー**（`.match-banner`）：緑or黄
3. **史実の判断**（`.result-historical`）：緑ヘッダー付き・最重要

### エンディングの概念カード
- 4枚を `CONCEPT_CARDS` 配列で設定
- 色：① 深紅 ② 緑 ③ 青 ④ 茶（CSSで自動適用）

### タイマー
- `TIMER_TOTAL`（秒）を変えるだけで表示が自動更新
- 決断場面でのみ表示（グループ審議用）

---

## 構成パターン（テンプレートに準拠）

1. **タイトル画面**
2. **導入シーン**（背景・人物紹介・状況説明）
3. **決断①〜③**（A/B/C選択 → 結果 → 史実解説）
4. **エンディング**（ナレーション + スコア + 概念カード4枚）

---

## commitルール

改善作業が完了したら必ず git commit を提案する（自動では行わない）。  
コミットメッセージ例：`歴史シミュレーションv2：桂太郎シナリオ追加`

---

## 既存シナリオ

| フォルダ名 | 人物 | 状態 |
|---|---|---|
| `_template/` | テンプレート | 完成 |
| （v1からの移植は後日） | | |
