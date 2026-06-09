# テスト問題作成

教科書画像・過去問・プリント・Web資料メモをもとに、4択中心の定期試験問題を Word 形式で生成するツールです。

## 基本方針

- 教科書画像は、上位の `教科書/` フォルダに集約する。
- `テスト問題作成/input/` は、今回だけ使う追加資料の置き場にする。
- Web資料はAIに検索させず、先生がURL・出典・本文メモを指定する。
- 試験ごとの設定は `configs/` に分け、再利用できるようにする。

## フォルダの役割

```text
テスト問題作成/
├── generate.py              # 問題生成
├── improve.py               # 既存問題の改善レポート生成
├── exam_config.yaml         # 既定の設定
├── configs/                 # 試験ごとの設定YAML
├── input/
│   ├── past_exams/          # 今回だけ参照する過去問
│   ├── textbook_images/     # 今回だけ参照する教科書画像
│   ├── worksheets/          # 今回だけ参照する授業プリント
│   ├── web_sources/         # URL・出典・本文メモを入れたWeb資料
│   └── improve/             # 改善したい既存問題
├── output/
│   ├── generated/           # 生成されたテスト
│   └── reports/             # 改善レポートなど
└── templates/               # 将来のWordテンプレート置き場
```

## 実行方法

既定設定で実行する場合：

```bash
python generate.py
```

試験ごとの設定を指定する場合：

```bash
python generate.py --config configs/sample.yaml
```

## Web資料の書き方

`input/web_sources/` に `.txt` を置きます。1ファイルに1資料が見やすいです。

```text
タイトル: 綿工業の輸出額推移
URL: https://example.com/source
出典: ○○統計資料
メモ:
- 1880年代以降、綿製品の輸出が増加している。
- グラフから、産業革命と貿易構造の変化を問える。
```

この資料を使う場合は、設定YAMLで `use_web_sources: true` にします。

## 設定ファイルの使い分け

`exam_config.yaml` はすぐ実行するための既定設定です。実際の運用では、試験ごとに `configs/` へコピーして使うと安全です。

例：

```text
configs/
├── 歴史総合_前期中間.yaml
├── 歴史総合_前期期末.yaml
└── 公共_民主政治.yaml
```

これにより、前回の設定を上書きしてしまう事故を防げます。
