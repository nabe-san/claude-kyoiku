#!/usr/bin/env python3
"""
Vault 読書ノート生成スクリプト（画像入力版）

書き込み済みページ画像から Vault Markdown 下書きを生成する。

Usage:
  python generate.py <slug>

  例: python generate.py ashita-no-kindaishi

事前準備:
  1. books-vault/input/<slug>/ フォルダを作成する
  2. books-vault/input/<slug>/meta.yaml に書誌情報を記述する（下記参照）
  3. 書き込み済みページ画像（page_001.jpg など）を同フォルダに置く
  4. books-vault/.env に Gemini API キーを設定する（Google AI Studio で発行）
     書き方: GEMINI_API_KEY=AIzaSy...（OpenAI のキーではありません）

meta.yaml の書き方:
  title: 明日のための近代史
  author: 伊勢弘志
  year: 2022
  concepts_hint:
    - 帝国主義
    - 国民国家
    - 近代化
    - 万国公法

出力先: books-vault/<slug>.md

注意:
  - <!-- featured --> はAIが付けません。原本照合後に教師が手動で追加してください
  - 生成後は必ず原本画像と引用テキストを照合してください（誤読の可能性があります）
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

VAULT_DIR = Path(__file__).parent
INPUT_DIR = VAULT_DIR / "input"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

load_dotenv(VAULT_DIR / ".env")

BODY_PROMPT = """\
これらは書籍のページ画像です。読者が書き込んだ記号に従って引用箇所を特定し、抽出してください。

【書誌情報】
タイトル：{title}
著者：{author}
出版年：{year}年

【書き込み記号の意味】
◎　　… 極めて重要。その行・段落を引用する
縦線 … 余白に引いた縦の線。隣接するテキストブロック全体が重要
横線 … 文字の下に引いた線。その行またはその段落が重要

印刷の罫線や装飾と区別すること。読者の手書き記号のみを対象にしてください。

【引用ルール】
- 記号のある箇所を起点に、文として意味が完結する範囲を抽出する
- 途中から始まる文は文頭まで戻り、途中で終わる文は文末まで延ばす
- 引用は原文のまま。一字一句変えない。要約・言い換えは禁止
- 複数行にわたる場合は各行の先頭に「> 」を付ける
- 書き込み記号がない箇所は引用しない

【概念タグのルール】
以下の候補リストから引用に関係するタグを2〜5個選ぶ。
リストにない概念が必要な場合は末尾に「新規タグ候補: ○○」と別記する（引用ブロック外に）。
候補: {concepts_hint}

【出力フォーマット】
書き込みのある引用ブロックを以下の形式で出力する。
前置き文・説明文は一切書かず、引用ブロックのみを並べる。

<!-- concepts: タグ1, タグ2 -->
## テーマを端的に表す見出し（15字以内）

> 引用テキスト
> 複数行の場合は各行の先頭に > を付ける

*{author}『{title}』（{year}年）*

---

（次の引用ブロックをそのまま続ける）

【禁止事項（厳守）】
- <!-- featured --> は絶対に出力しない
- 引用の後に解説・要約・コメントを書かない
- 「この引用のポイントは」などの説明を書かない
- 「以下に引用を提示します」などの前置き文を書かない
- 「授業での活用法」「教師メモ」などの教育的コメントを書かない
"""


def load_images(input_dir: Path) -> list:
    images = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        print(f"エラー: 画像ファイルが見つかりません: {input_dir}")
        print(f"  → {input_dir}/ に .jpg / .png 画像を置いてください")
        sys.exit(1)
    return images


def build_frontmatter(meta: dict, slug: str) -> str:
    lines = [
        "---",
        f"ref: {slug}",
        f"title: {meta['title']}",
        f"author: {meta['author']}",
    ]
    if year := meta.get("year"):
        lines.append(f"year: {year}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def call_gemini(meta: dict, image_paths: list) -> str:
    try:
        import google.generativeai as genai
        from PIL import Image
    except ImportError:
        print("エラー: 必要なパッケージがインストールされていません")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEY が設定されていません")
        print("  → books-vault/.env に以下を記述してください")
        print("     GEMINI_API_KEY=AIzaSy...（Google AI Studio のキー）")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = BODY_PROMPT.format(
        title=meta["title"],
        author=meta["author"],
        year=meta.get("year", ""),
        concepts_hint="・".join(meta.get("concepts_hint", [])) or "（未設定）",
    )

    contents = [prompt]
    for path in image_paths:
        print(f"  読み込み: {path.name}")
        contents.append(Image.open(path))

    print(f"Gemini Vision API に送信中（{len(image_paths)} 枚）...")
    response = model.generate_content(contents)
    return response.text.strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)

    slug = args[0]
    input_dir = INPUT_DIR / slug

    if not input_dir.exists():
        print(f"エラー: 入力フォルダが見つかりません: {input_dir}")
        print(f"  → books-vault/input/{slug}/ を作成し meta.yaml と画像を置いてください")
        sys.exit(1)

    meta_file = input_dir / "meta.yaml"
    if not meta_file.exists():
        print(f"エラー: meta.yaml が見つかりません: {meta_file}")
        sys.exit(1)

    meta = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
    print(f"書誌情報: 『{meta.get('title')}』 {meta.get('author')}")

    image_paths = load_images(input_dir)
    print(f"画像: {len(image_paths)} 枚")

    body = call_gemini(meta, image_paths)
    content = build_frontmatter(meta, slug) + body + "\n"

    output_file = VAULT_DIR / f"{slug}.md"
    output_file.write_text(content, encoding="utf-8")

    print(f"\n生成完了: {output_file}")
    print("  ⚠ 引用は必ず原本と照合してください（Gemini の誤読の可能性あり）")
    print("  ⚠ 公開する引用には <!-- featured --> を手動で追加してください")


if __name__ == "__main__":
    main()
