#!/usr/bin/env python3
"""
publish スクリプト: Vault → 公開用 src/content/books/[slug].md

Usage:
  python generate.py <slug>
  例: python generate.py ashita-no-kindaishi

事前準備:
  1. GAS で processBook() を実行し、Drive の books-vault/[slug]/[slug].md を生成する
  2. そのファイルをローカルの books-vault/<slug>.md にダウンロードして置く
  3. books-vault/.env に ANTHROPIC_API_KEY を設定する（sk-ant-... で始まる）

出力先: src/content/books/<slug>.md
"""

import os
import sys
import re
import json
from pathlib import Path
from dotenv import load_dotenv

VAULT_DIR = Path(__file__).parent
SRC_BOOKS_DIR = VAULT_DIR.parent / "src" / "content" / "books"
CONCEPT_VOCABULARY_PATH = VAULT_DIR.parent / "src" / "data" / "concepts" / "history-general.json"

load_dotenv(VAULT_DIR / ".env")

PUBLISH_PROMPT = """\
あなたは教師の読書ノートの編集者です。
以下は Vault（全引用ストック）です。この中から公開サイトに掲載する引用を選んでください。

【Vault（全引用）】
{vault_content}

【選択基準（重要な順）】
1. 概念理解に役立つ——知識ではなく思考の材料になる引用
2. 授業との接続性が高い——授業テーマ「{concepts}」に関連する
3. 著者の視点・論点がよく表れている——著者の独自の主張が読み取れる
4. 引用だけで考える余白がある——解説なしで読者が自分で考えられる

【除外すべきブロック】
- 同じ文が繰り返されている（反復ループ）
- 途中で文が切れている（末尾が「…」「求めたの」「五年」など中途半端）
- 1行だけの極端に短い引用（30字未満）

【選択数】
6〜10 ブロックを選ぶ。重複・欠陥があれば躊躇なく除外してよい。

【出力フォーマット】
フロントマターから始め、選んだ引用ブロックをそのまま並べる。
<!-- concepts: ... --> タグは本文から除去する。
## 見出し、> 引用、*出典* の形式はそのまま維持する。
引用ブロックの間には --- を入れる。

---
title: {title}
author: {author}
year: {year}
summary: （この本の主題を2〜3文で。著者の独自の論点を中心に書く）
concepts:
{concepts_yaml}
relatedUnits:
{related_units_yaml}
---

（引用ブロックをここに並べる）

【厳守事項】
- AI による解説・要約・コメントを本文に追加しない
- <!-- featured --> を出力しない
- 引用テキストは一字一句変えない
- 前置き文（「以下に引用を示します」等）を書かない
- concepts: の値は上記フロントマターの通りに出力し、変更・追加しない
"""


def read_vault(slug: str) -> str:
    vault_path = VAULT_DIR / f"{slug}.md"
    if not vault_path.exists():
        print(f"エラー: Vault ファイルが見つかりません: {vault_path}")
        print(f"  → Drive の books-vault/{slug}/{slug}.md をローカルにダウンロードして")
        print(f"     books-vault/{slug}.md として置いてください")
        sys.exit(1)
    content = vault_path.read_text(encoding="utf-8")
    # Google Drive ダウンロード時に Markdown 記号がエスケープされる場合の前処理
    content = re.sub(r'\\([#\-<>!*])', r'\1', content)  # バックスラッシュエスケープを除去
    content = re.sub(r'[ \t]+\n', '\n', content)          # 行末スペースを除去
    return content


def parse_vault_frontmatter(vault_content: str) -> dict:
    match = re.match(r'^---\n(.*?)\n---\n', vault_content, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        if ': ' in line:
            key, val = line.split(': ', 1)
            meta[key.strip()] = val.strip()
    return meta


def load_concept_vocabulary() -> set:
    """マスター語彙（歴史総合）の概念名の集合を読み込む。ファイルがなければ空集合を返す。"""
    if not CONCEPT_VOCABULARY_PATH.exists():
        return set()
    data = json.loads(CONCEPT_VOCABULARY_PATH.read_text(encoding="utf-8"))
    return {item["name"] for item in data}


def extract_concepts_from_vault(vault_content: str, vocabulary: set) -> list:
    tags = re.findall(r'<!-- concepts:\s*([^-]+?)\s*-->', vault_content)
    seen = set()
    result = []
    unmatched = set()
    for tag_line in tags:
        for t in tag_line.split(','):
            t = t.strip()
            # 「新規タグ候補:」は概念タグではないので除外
            if not t or t.startswith('新規タグ候補') or t in seen:
                continue
            seen.add(t)
            # マスター語彙にない語は公開タグに含めず、確認用にだけ表示する
            if not vocabulary or t in vocabulary:
                result.append(t)
            else:
                unmatched.add(t)
    if unmatched:
        print(f"⚠ 語彙外の概念タグ（公開からは除外）: {', '.join(sorted(unmatched))}")
    return result[:8]


def read_existing_related_units(slug: str) -> list:
    pub_file = SRC_BOOKS_DIR / f"{slug}.md"
    if not pub_file.exists():
        return []
    content = pub_file.read_text(encoding="utf-8")
    match = re.search(r'relatedUnits:\s*\n((?:[ \t]+-[^\n]+\n)*)', content)
    if not match:
        return []
    return re.findall(r'-\s+(.+)', match.group(1))


def call_gemini(vault_content: str, meta: dict, concepts: list, related_units: list) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        print("エラー: google-generativeai がインストールされていません")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: GEMINI_API_KEY が設定されていません")
        print("  → books-vault/.env に GEMINI_API_KEY=AIzaSy... を記述してください")
        sys.exit(1)

    concepts_yaml = "\n".join(f"  - {c}" for c in concepts) if concepts else "  []"
    related_units_yaml = "\n".join(f"  - {u}" for u in related_units) if related_units else "  []"

    prompt = PUBLISH_PROMPT.format(
        vault_content=vault_content,
        title=meta.get("title", ""),
        author=meta.get("author", ""),
        year=meta.get("year", ""),
        concepts=", ".join(concepts[:5]),
        concepts_yaml=concepts_yaml,
        related_units_yaml=related_units_yaml,
    )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=genai.GenerationConfig(temperature=0.3, max_output_tokens=4096),
    )
    print("Gemini API に送信中...")
    response = model.generate_content(prompt)
    text = response.text.strip()
    # Gemini がコードブロックで囲んだ場合の除去（```yaml ... ``` や ``` ... ```）
    text = re.sub(r'^```(?:yaml|markdown)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    return text.strip()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)

    slug = args[0]
    pub_path = SRC_BOOKS_DIR / f"{slug}.md"

    vault_content = read_vault(slug)
    meta = parse_vault_frontmatter(vault_content)
    print(f"書誌情報: 『{meta.get('title')}』 {meta.get('author')}")

    vocabulary = load_concept_vocabulary()
    concepts = extract_concepts_from_vault(vault_content, vocabulary)
    related_units = read_existing_related_units(slug)
    print(f"概念タグ候補: {concepts}")
    if related_units:
        print(f"関連授業単元（既存から継承）: {related_units}")

    output = call_gemini(vault_content, meta, concepts, related_units)

    pub_path.write_text(output, encoding="utf-8")
    print(f"\n公開用ファイルを生成しました: {pub_path}")
    print("  必要であれば最後だけ手動修正してください")


if __name__ == "__main__":
    main()
