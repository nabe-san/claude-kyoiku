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
import requests
from pathlib import Path
from dotenv import load_dotenv

from audit_citations import split_frontmatter, check_citations_text

VAULT_DIR = Path(__file__).parent
SRC_BOOKS_DIR = VAULT_DIR.parent / "src" / "content" / "books"
CONCEPT_VOCABULARY_DIR = VAULT_DIR.parent / "src" / "data" / "concepts"

load_dotenv(VAULT_DIR / ".env")

PUBLISH_PROMPT = """\
あなたは教師の読書ノートの編集者です。
以下は Vault（全引用ストック）です。この中から公開サイトに掲載する引用を選んでください。

【Vault（全引用）】
{vault_content}

【選択基準（優先順位順）】
1. 授業との接続性が高い——授業テーマ「{concepts}」に関連する（最優先基準）
2. 概念理解に役立つ——知識ではなく思考の材料になる引用
3. 著者の視点・論点がよく表れている——著者の独自の主張が読み取れる
4. 引用だけで考える余白がある——解説なしで読者が自分で考えられる

授業との接続性で優劣がつけがたい場合は、内容の重要性（上記2〜4への合致度）を根拠に判断してよい。

【除外すべきブロック】
- 同じ文が繰り返されている（反復ループ）
- 30字未満の極端に短い引用（例外なく除外する）
- 途中で文が切れていて、かつ次のブロックにも続きが見当たらない引用
  （この Vault は「重要だと感じた箇所」だけを画像化して文字起こししたものなので、
    Vault の時点で既に途切れている＝重要でない可能性が高い。無理に含めず除外してよい）

【引用が2ブロックに分断されている場合の扱い】
まれに、1つの連続した文章が、Vault内で見出し・出典が別々の2ブロックに分かれてしまって
いることがある（例：ブロックAの引用が「…補給を」で終わり、次のブロックBの引用が
「層困難にしたのである。」から始まる → 本来は「補給を一層困難にしたのである。」という
1つの文）。
後続ブロックの冒頭が明らかに前のブロックの文の続きになっており、欠落が数文字程度
（目安：3字以内）で自然に補えると判断できる場合に限り、2つを1つの引用ブロックに
統合し、欠落部分を文脈から自然な形で補ってよい（100%の正確性は求めない。1〜2文字
程度の誤りは許容する）。欠落が数文字を超える場合や、続きかどうか確信が持てない場合は
統合せず、不完全な方のブロックを除外すること。

【短い引用の扱い】
- 30字未満は上記の通り必ず除外する
- 30字以上でも他の引用と比べて明らかに短い（目安：80字未満）引用は、1冊につき
  最大1個までとする。該当候補が複数あれば、最も内容的に自立して読める
  （説明なしで理解できる）ものを1つだけ残し、残りは除外する

【選択数】
20 ブロック程度を目安に選ぶ（引用が特に多い場合は最大25ブロックまで）。重複・欠陥があれば躊躇なく除外してよい。

【出力フォーマット】
フロントマターから始め、選んだ引用ブロックをそのまま並べる。
<!-- concepts: ... --> タグは各引用ブロックの見出しの直前に残す（除去しない）。
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
    """マスター語彙（歴史総合・公共など全科目）の概念名の集合を読み込む。
    src/data/concepts/ 配下の *.json をすべて走査するため、科目を追加しても変更不要。
    """
    if not CONCEPT_VOCABULARY_DIR.exists():
        return set()
    names = set()
    for path in CONCEPT_VOCABULARY_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        names.update(item["name"] for item in data)
    return names


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


def filter_citation_concepts(text: str, vocabulary: set) -> str:
    """公開Markdown本文中の引用ごとの <!-- concepts: --> を、マスター語彙にあるタグだけに絞り込む。
    語彙外のタグ（自由記述・新規タグ候補など）はこの時点で落とし、タグが0件になった行は削除する。
    """
    def replace(match: re.Match) -> str:
        tags = [t.strip() for t in match.group(1).split(',') if t.strip()]
        kept = [t for t in tags if not vocabulary or t in vocabulary]
        if not kept:
            return ''
        return f'<!-- concepts: {", ".join(kept)} -->'

    return re.sub(r'<!--\s*concepts:\s*([^-]+?)\s*-->', replace, text)


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

    # google.generativeai（非推奨SDK）の GenerationConfig は thinking_config に非対応のため、
    # gas_vault.js の callGeminiForSelection() と同じくREST APIを直接叩く。
    # 思考を無効化しないと、Vaultが大きい・内容が複雑な本でモデルの内部思考が長引き、
    # タイムアウト（DEADLINE_EXCEEDED）を繰り返す。
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 65536,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    print("Gemini API に送信中...")
    res = requests.post(url, json=payload, timeout=600)
    result = res.json()
    if "error" in result:
        raise RuntimeError(f"Gemini API エラー: {result['error'].get('message')}")

    finish_reason = result.get("candidates", [{}])[0].get("finishReason", "UNKNOWN")
    if finish_reason != "STOP":
        print(f"⚠ 応答が途中で終了しました（{finish_reason}）")

    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Gemini がコードブロックで囲んだ場合の除去（```yaml ... ``` や ``` ... ```）
    text = re.sub(r'^```(?:yaml|markdown)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text)
    return text.strip()


def auto_clean(text: str) -> str:
    """機械的に判断できる不備だけを自動で取り除く（見出し・概念タグ・出典行など
    ブロック構造そのものには手を加えない、引用行内の記号のみの単純な置換）。
    - '> >' の二重引用記号 → '> ' に統一
    - 引用行に混入した '◎' などの書き込み記号を除去
    """
    text = re.sub(r'(?m)^>\s*>\s*', '> ', text)
    text = re.sub(r'(?m)^(>.*)◎', r'\1', text)
    return text


def warn_remaining_issues(output: str) -> None:
    """auto_clean 後も残る、AIの判断が必要な問題を警告として表示する（ファイルは変更しない）。"""
    body = split_frontmatter(output)
    results = check_citations_text(body)
    if not results:
        return
    print(f"\n⚠ 引用チェックで{len(results)}件、要確認の箇所があります（自動修正はしていません）:")
    for r in results:
        print(f"  ● 「{r['heading']}」")
        for issue in r['issues']:
            print(f"      - {issue}")


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
    output = filter_citation_concepts(output, vocabulary)
    output = auto_clean(output)

    pub_path.write_text(output, encoding="utf-8")
    print(f"\n公開用ファイルを生成しました: {pub_path}")
    warn_remaining_issues(output)
    print("  必要であれば最後だけ手動修正してください")


if __name__ == "__main__":
    main()
