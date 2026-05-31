# シナリオJSON化メモ

## 目的

これまで各シナリオの `index.html` に直接書いていた人物・本文・選択肢・概念カードを、`scenario.json` に分離する。

これにより、新しいシナリオを作るときにHTMLやJavaScriptをほぼ触らず、教材内容だけを編集できる。

## 新しい作り方

1. `scenarios/_json_template/scenario.json` を新しいシナリオフォルダにコピーする
2. コピー先フォルダ名を `04_タイトル_人物名` のように変更する
3. `scenario.json` だけを編集する
4. `scenarios.json` にトップ画面用のカード情報を1件追加する
5. ローカルサーバー経由で `player.html` を開く

例:

```powershell
New-Item -ItemType Directory "scenarios/04_ビスマルク_国民国家"
Copy-Item "scenarios/_json_template/scenario.json" "scenarios/04_ビスマルク_国民国家/scenario.json"
```

## 重要な注意

`scenario.json` は外部ファイルなので、HTMLをダブルクリックで直接開くとブラウザが読み込みを止めることがある。

その場合は、`歴史シミュレーションv2` フォルダで簡易サーバーを起動して開く。

```powershell
python -m http.server 8000
```

ブラウザで開くURL:

```text
http://localhost:8000/scenarios/_json_template/index.html
```

既存シナリオのJSON版サンプルを開くURL:

```text
http://localhost:8000/player.html?data=scenarios/03_帝国主義_ドゥメール/scenario.json
```

## JSONの主な項目

- `meta`: タイトル、科目、説明文、開始シーン、タイマー秒数
- `meta.bigQuestion`: シナリオ開始時に提示する大きな問い
- `characters`: 主人公や助言者などの人物情報
- `timeline`: 画面上部の進行表示
- `passages`: タイトル、ストーリー、決断、エンディングの流れ
- `ending`: 最後のナレーション、評価文、概念カード`n- `ending.learningPoints`: 終了画面に表示する「学びの要点」。生徒が紙に転記しやすい短文にする

## トップ画面の管理

トップ画面のカード一覧は `scenarios.json` で管理する。

- `url`: 既存HTMLシナリオへ直接リンクする場合に使う
- `data`: JSON版シナリオを `player.html` で開く場合に使う
- `status`: `ready` ならクリック可能、`coming-soon` なら準備中カード
- `bigQuestion`: 授業で最初に提示する大きな問い

## ダブルクリックで開いたとき

JSON版は `fetch()` で外部JSONを読むため、`file:///` で開くとブラウザに止められる。

その場合はエラー画面に出る通り、ローカルサーバー経由で開く。

## 教育的なメリット

- シナリオ作成時に「教材内容」と「画面の仕組み」を分けられる
- 生徒に考えさせたい問い・制約・概念カードを整理しやすい
- 同じ画面設計で、日本史・公共・探究の意思決定教材を増やせる

## 学びの要点

終了画面には `ending.learningPoints` を番号付きで表示する。

ここは生徒に自由記述させる欄ではなく、教師側から「このシミュレーションで押さえるべきこと」を短く示す欄として使う。

例:

```json
"learningPoints": [
  "帝国主義は「文明化」や「近代化」を理由に正当化された。",
  "しかし実際には、植民地の人々に税・労働・文化的な負担を押しつけた。",
  "同じ政策でも、支配する側には「発展」、支配される側には「収奪」と見えた。"
]
```

## 旧HTML版との混在を避ける

JSON化済みのシナリオでは、各シナリオフォルダの `index.html` は直接ゲーム本体を持たせず、`player.html?data=...` へ誘導する入口にする。

旧HTML版が必要な場合は `index_legacy.html?teacher=1` で先生用確認として開く。生徒用導線には出さない。

これにより、トップ画面・直接URL・フォルダ内HTMLのどこから開いても、通常はJSON版へ入る。
