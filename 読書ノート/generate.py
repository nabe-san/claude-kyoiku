#!/usr/bin/env python3
"""
読書ノート自動生成スクリプト

Usage:
  python generate.py <slug>          # input/<slug>.yaml の設定に従って生成
  python generate.py <slug> --force  # 既存ファイルを確認なしで上書き

事前準備:
  1. books/<slug>.txt に本のテキストデータを置く
  2. 読書ノート/input/<slug>.yaml に書誌情報を記述する（下記参照）
  3. .env に GEMINI_API_KEY を設定する

input/<slug>.yaml の書き方:
  title: 明日のための近代史
  author: 伊勢弘志
  year: 2022
  publisher: 朝日新書（省略可）
  summary: 一文紹介（省略可）
  concepts:
    - 帝国主義
    - 近代化
  relatedUnits:
    - teikoku-shugi

出力先: 歴史HP/src/content/books/<slug>.md
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
BOOKS_TXT_DIR = ROOT_DIR / "books"
BOOKS_CONTENT_DIR = ROOT_DIR / "歴史HP" / "src" / "content" / "books"
INPUT_DIR = SCRIPT_DIR / "input"

EXTRACT_PROMPT = """\
あなたは日本史・歴史総合・公共の高校教員の助手です。
以下の本のテキストを読み、授業（近代史・帝国主義・日本史探究など）に直接活かせる読書ノートを作成してください。

書名: {title}
著者: {author}
関連授業単元: {units}
関連概念: {concepts}

【出力形式（Markdown）】

## 授業に持ち込んだポイント

[この本から授業に持ち込んだ主な視点・論点を2〜3段落の散文で説明する。
 箇条書き不可。「この本が授業にとって価値ある理由」まで含めて書く。]

## 本から抜粋・メモ

### [テーマ名1（端的に）]

> [本文からの引用——原文のまま抜粋すること。要約・改変不可。]

[この引用の歴史的意義と文脈の説明。最後に以下の形式で授業での使い方を示す：
 → **授業への使い方**: 具体的な発問・活動・他の授業内容との接続を示す。]

---

[上記セットを4〜7テーマ繰り返す。重要度の高い順。]

【制約】
- 引用は必ず原文からの正確な抜粋（要約不可）
- 生徒の「常識」を問い直す視点を優先
- 「→ **授業への使い方**:」の行は各テーマに必ず含める
- 日本語で出力

【本文（長い場合は前半を優先）】
{text}
"""


def generate_with_gemini(config: dict, text: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        print("エラー: google-generativeai がインストールされていません")
        print("  pip install google-generativeai")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEY が設定されていません (.env を確認してください)")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = EXTRACT_PROMPT.format(
        title=config.get("title", ""),
        author=config.get("author", ""),
        units="、".join(config.get("relatedUnits", [])) or "未設定",
        concepts="、".join(config.get("concepts", [])) or "未設定",
        text=text[:300000],  # Flash の制限内に収める
    )

    print("Gemini API に送信中...")
    response = model.generate_content(prompt)
    return response.text


def build_frontmatter(config: dict) -> str:
    lines = ["---"]
    lines.append(f"title: {config.get('title', '')}")
    lines.append(f"author: {config.get('author', '')}")

    if year := config.get("year"):
        lines.append(f"year: {year}")
    if publisher := config.get("publisher"):
        lines.append(f"publisher: {publisher}")
    if summary := config.get("summary"):
        # YAML multiline を避けてシングルクォートで囲む
        safe = summary.replace("'", "''")
        lines.append(f"summary: '{safe}'")

    concepts = config.get("concepts", [])
    if concepts:
        lines.append("concepts:")
        for c in concepts:
            lines.append(f"  - {c}")
    else:
        lines.append("concepts: []")

    related = config.get("relatedUnits", [])
    if related:
        lines.append("relatedUnits:")
        for u in related:
            lines.append(f"  - {u}")
    else:
        lines.append("relatedUnits: []")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print(__doc__)
        sys.exit(1)

    slug = args[0]

    # テキストファイル確認
    txt_file = BOOKS_TXT_DIR / f"{slug}.txt"
    if not txt_file.exists():
        print(f"テキストファイルが見つかりません: {txt_file}")
        print(f"  → {BOOKS_TXT_DIR}/ に {slug}.txt を置いてください")
        sys.exit(1)

    text = txt_file.read_text(encoding="utf-8")
    print(f"テキスト読み込み完了: {len(text):,} 文字")

    # 設定ファイル確認
    config_file = INPUT_DIR / f"{slug}.yaml"
    if not config_file.exists():
        print(f"設定ファイルが見つかりません: {config_file}")
        print("\n以下のテンプレートを参考に作成してください:\n")
        print(yaml.dump({
            "title": "本のタイトル",
            "author": "著者名",
            "year": 2024,
            "summary": "一文で本を紹介（省略可）",
            "concepts": ["帝国主義", "近代化"],
            "relatedUnits": ["teikoku-shugi"],
        }, allow_unicode=True, default_flow_style=False))
        sys.exit(1)

    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    print(f"設定: {config.get('title')} / {config.get('author')}")

    # 出力先確認
    BOOKS_CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = BOOKS_CONTENT_DIR / f"{slug}.md"

    if output_file.exists() and not force:
        answer = input(f"\n既存ファイルがあります: {output_file}\n上書きしますか？ (y/N): ").strip()
        if answer.lower() != "y":
            print("中止しました")
            sys.exit(0)

    # 生成
    body = generate_with_gemini(config, text)
    content = build_frontmatter(config) + body

    output_file.write_text(content, encoding="utf-8")
    print(f"\n✓ 読書ノートを生成しました: {output_file}")
    print("  → 生成後に内容を確認・編集してください")


if __name__ == "__main__":
    main()
