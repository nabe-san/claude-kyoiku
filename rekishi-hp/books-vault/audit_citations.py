#!/usr/bin/env python3
"""
引用ブロックの機械的チェック。AIは使わず、文字数・文末記号・混入記号のみを見る。

- 単体で実行すると、公開済み src/content/books/*.md 全体を棚卸しする（読み取り専用）。
- generate.py からは check_citations_text() を呼び出し、生成直後の本文を検証する。

Usage:
  python audit_citations.py
"""

import re
from pathlib import Path

VAULT_DIR = Path(__file__).parent
SRC_BOOKS_DIR = VAULT_DIR.parent / "src" / "content" / "books"

EXCLUDE_UNDER = 30            # この文字数未満は例外なく除外する（プロンプトの既存ルールと同じ）
SHORT_UNDER = 80              # 30字以上でもこの文字数未満は「短い引用」とみなす
MAX_SHORT_ALLOWED = 1         # 「短い引用」を1冊あたり許容する数
SENTENCE_END_CHARS = "。」』！？…”\""  # 引用がこれらで終わっていれば「文末が自然」とみなす
STRAY_SYMBOLS = ["◎", "縦線", "横線"]  # 引用文中に混入してはいけない記号


def split_frontmatter(content: str) -> str:
    """フロントマター（--- ... ---）を除いた本文を返す。"""
    match = re.match(r'^---\n.*?\n---\n', content, re.DOTALL)
    return content[match.end():] if match else content


def parse_citation_blocks(body: str):
    """[slug].astro の parseCitations と同じロジックで引用ブロックを分割する。"""
    normalized = body.replace('\r\n', '\n').strip()
    raw_blocks = re.split(r'\n-{3,}\n', normalized)

    blocks = []
    for raw in raw_blocks:
        heading_match = re.search(r'^##\s+(.+)$', raw, re.MULTILINE)
        heading = heading_match.group(1).strip() if heading_match else ''

        quote_lines = [
            line for line in raw.split('\n') if line.strip().startswith('>')
        ]
        if not quote_lines and not heading:
            continue

        blocks.append({'heading': heading, 'quote_lines': quote_lines})
    return blocks


def strip_one_marker(line: str) -> str:
    """先頭の '>' を1つだけ取り除く（parseCitations と同じ挙動）。"""
    return re.sub(r'^>\s?', '', line)


def quote_text_of(quote_lines: list[str]) -> str:
    return ''.join(strip_one_marker(l).strip() for l in quote_lines)


def check_block(quote_lines: list[str]) -> tuple[list[str], set[str]]:
    """引用1ブロックの機械的チェック。(メッセージ一覧, タグ集合) を返す。
    タグ: 'too_short'（30字未満・例外なく除外）/ 'short'（30〜80字・1冊1件まで）
          / 'truncated'（文末が不自然）/ 'stray_marker' / 'stray_symbol'
    """
    issues = []
    tags = set()

    quote_text = quote_text_of(quote_lines)
    length = len(quote_text)

    if length < EXCLUDE_UNDER:
        issues.append(f"短すぎる（{length}字 < {EXCLUDE_UNDER}字。例外なく除外対象）")
        tags.add('too_short')
    elif length < SHORT_UNDER:
        issues.append(f"短い引用（{length}字。1冊につき{MAX_SHORT_ALLOWED}件まで許容）")
        tags.add('short')

    if quote_text and quote_text[-1] not in SENTENCE_END_CHARS:
        issues.append(f"文末が句読点等で終わっていない（末尾: 「...{quote_text[-12:]}」）")
        tags.add('truncated')

    stripped_lines = [strip_one_marker(l) for l in quote_lines]
    if any(l.strip().startswith('>') for l in stripped_lines):
        issues.append("引用記号 '>' の混入（元データが '> >' の二重表記だった可能性）")
        tags.add('stray_marker')

    for sym in STRAY_SYMBOLS:
        if sym in quote_text:
            issues.append(f"記号「{sym}」の混入")
            tags.add('stray_symbol')

    return issues, tags


def check_citations_text(body: str):
    """本文（フロントマターを除いた引用ブロックの連なり）を検査する。
    generate.py から呼び出す想定。「短い引用」は1冊内で許容数を超えた分だけ問題として返す。
    戻り値: [{heading, issues, length}, ...]（問題がある引用のみ）
    """
    blocks = parse_citation_blocks(body)

    per_block = []
    for b in blocks:
        issues, tags = check_block(b['quote_lines'])
        per_block.append({
            'heading': b['heading'],
            'issues': issues,
            'tags': tags,
            'length': len(quote_text_of(b['quote_lines'])),
        })

    # 'short' タグは1冊内で許容数を超えた分だけを問題として残す（短い順に許容数だけ見逃す）
    short_items = [b for b in per_block if 'short' in b['tags']]
    short_items.sort(key=lambda b: b['length'], reverse=True)  # 長い方から許容
    for b in short_items[MAX_SHORT_ALLOWED:]:
        pass  # 既に issues に理由が入っているのでそのまま残す
    forgiven_headings = {b['heading'] for b in short_items[:MAX_SHORT_ALLOWED]}

    results = []
    for b in per_block:
        issues = b['issues']
        if 'short' in b['tags'] and b['heading'] in forgiven_headings:
            issues = [i for i in issues if '短い引用' not in i]
        if issues:
            results.append({'heading': b['heading'], 'issues': issues})
    return results


def audit_file(path: Path):
    content = path.read_text(encoding='utf-8')
    body = split_frontmatter(content)
    blocks = parse_citation_blocks(body)
    results = check_citations_text(body)

    # プレビュー文言を付け直す
    preview_by_heading = {
        b['heading']: quote_text_of(b['quote_lines'])[:80] + (
            '…' if len(quote_text_of(b['quote_lines'])) > 80 else ''
        )
        for b in blocks
    }
    for r in results:
        r['preview'] = preview_by_heading.get(r['heading'], '')

    return results, len(blocks)


def main():
    md_files = sorted(SRC_BOOKS_DIR.glob('*.md'))
    total_flagged = 0
    total_blocks = 0

    for path in md_files:
        results, block_count = audit_file(path)
        total_blocks += block_count

        print(f"\n=== {path.name}（全{block_count}ブロック） ===")
        if not results:
            print("  問題なし")
            continue

        for r in results:
            total_flagged += 1
            print(f"  ● 「{r['heading']}」")
            for issue in r['issues']:
                print(f"      - {issue}")
            print(f"      引用冒頭: {r['preview']}")

    print(f"\n--- 合計: 全{len(md_files)}冊・{total_blocks}ブロック中 {total_flagged}件を検出 ---")


if __name__ == '__main__':
    main()
