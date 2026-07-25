"""
rekishi-hp/src/content/books/*.md（GAS「サイト用文字起こし」が公開した引用データ）を
Obsidian Vaultの参考文献ノートに変換する。

import_books.py（books/*.txt＝「自動で画像文字化」の全文OCRを手動txt化したもの）とは
入力元が異なる別スクリプト。役割は同じ（06_RawSources/books/への変換）だが、以下の点が異なる。

- 入力元: books/*.txt ではなく rekishi-hp/src/content/books/*.md
  （GASのpublishToGitHub()がGitHubへ自動commit済み。このスクリプトはDrive・GitHub APIには
   一切アクセスせず、事前に `git pull` 済みのローカルcloneを読むだけ）
- 著者名・年号: frontmatterに既に入っているため、books_meta.json相当の手動登録は不要
- 概念タグ: GASのGemini Visionが選定済みのconceptsフィールドをそのままVault側にも引き継ぐ
  （tags:とは別にfrontmatterのconcepts:として保持する）

出力ファイル名は import_books.py と同一の display_title ロジックを用いる
（タイトルから著者名・年号と重複するトークンを除去し、sanitize_filenameで整形）。

注意:
    import_books.py と出力先ディレクトリ（06_RawSources/books/）が同じため、
    同じ書籍を両方のスクリプトで変換すると、同一ファイル名を取り合って上書きし合う。
    引用データへの一本化を進める場合は、対象書籍について import_books.py 側の
    books/*.txt・books_meta.json のエントリを削除しておくことを推奨する。

    本文は毎回 rekishi-hp 側のソースで丸ごと上書きするため、Vault側の出力ファイルに
    直接書き込んだ手動編集（関連書籍・気づきなど）は次回実行時に消える。書籍同士の
    関連付けは Vault ではなく rekishi-hp 側 frontmatter の relatedBookLinks に書くこと
    （このスクリプトが「## 関連書籍」として自動反映する）。

前提:
    rekishi-hp フォルダで事前に `git pull` を実行し、最新の引用データを取得しておくこと。

使い方:
    python import_citations.py
"""
import re
import unicodedata
from pathlib import Path

import yaml

CITATIONS_DIR = Path(__file__).parent.parent / "rekishi-hp" / "src" / "content" / "books"
VAULT_REF_DIR = Path.home() / "Desktop" / "MyObsidian" / "06_RawSources" / "books"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def sanitize_filename(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen] if text else "無題"


def display_title(title: str, author: str | None, year: str | None) -> str:
    """import_books.py と同一ロジック。ファイル名に著者名・年号が含まれる本は、
    frontmatterの値と一致する末尾トークンをタイトルから取り除いて重複を防ぐ。"""
    tokens = re.split(r"[_　]", title)
    while tokens and tokens[-1] in (author, year):
        tokens.pop()
    return "　".join(tokens)


def read_existing_status(path: Path) -> str | None:
    """import_books.py と同一ロジック。出力先に同名ファイルが既にあり、
    frontmatterにstatusがあればその値を維持する（再実行のたびにdraftが消えないように）。"""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    m = re.search(r"^status:\s*(.+)$", text[:end], re.MULTILINE)
    return m.group(1).strip() if m else None


def parse_frontmatter(text: str) -> tuple[str, str]:
    """frontmatter部分の生テキストと、それ以降の本文を分離する。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def get_scalar(fm_text: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.*)$", fm_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def get_list(fm_text: str, key: str) -> list[str]:
    """`key:\n  - item\n  - item` 形式のYAMLリストを取り出す。
    `key: []`（空リスト）や未設定の場合は空リストを返す。"""
    m = re.search(rf"^{key}:\s*\n((?:[ \t]+-[^\n]+\n?)*)", fm_text, re.MULTILINE)
    if not m or not m.group(1).strip():
        return []
    items = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("-"):
            items.append(line[1:].strip())
    return items


def get_related_book_links(fm_text: str) -> list[dict]:
    """`relatedBookLinks:` は `- slug: ...` / `note: ...` のオブジェクトのリストで、
    get_list() の単純な正規表現では取り出せないため、この項目だけPyYAMLに委ねる。
    frontmatter全体が壊れていても他フィールドの処理を止めないよう、失敗時は空リストを返す。"""
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return []
    items = data.get("relatedBookLinks") or []
    return [item for item in items if isinstance(item, dict) and item.get("slug")]


def build_output(title: str, author: str, year: str, concepts: list[str],
                  status: str, source_rel_path: str, body: str,
                  related_lines: list[str]) -> str:
    shown_title = display_title(title, author, year)

    lines = [
        "---",
        f"title: {title}",
        f"source: {source_rel_path}",
        "tags: [参考文献, 読書, 引用]",
    ]
    if author:
        lines.append(f"author: {author}")
    if year:
        lines.append(f"year: {year}")
    lines.append("type: source_excerpt")
    lines.append(f"book_title: {shown_title}")
    if concepts:
        lines.append("concepts:")
        for c in concepts:
            lines.append(f"  - {c}")
    lines.append(f"status: {status}")
    lines += [
        "---",
        "",
        f"# {shown_title}",
        "",
    ]
    if related_lines:
        lines.append("## 関連書籍")
        lines.extend(related_lines)
        lines.append("")
    lines += [
        body.strip(),
        "",
    ]
    return "\n".join(lines)


def main():
    if not CITATIONS_DIR.exists():
        print(f"{CITATIONS_DIR} が見つかりません。")
        print("rekishi-hp フォルダで `git pull` を実行済みか確認してください。")
        return

    VAULT_REF_DIR.mkdir(parents=True, exist_ok=True)
    md_paths = sorted(CITATIONS_DIR.glob("*.md"))

    # 1パス目: relatedBookLinks のslugからWikilink先タイトルを解決するため、
    # 全書籍のタイトルを先に集めておく（glob順とrelatedBookLinksの参照順は一致しないため）。
    titles_by_slug: dict[str, str] = {}
    for md_path in md_paths:
        fm_text, _ = parse_frontmatter(md_path.read_text(encoding="utf-8", errors="ignore"))
        if not fm_text:
            continue
        title = get_scalar(fm_text, "title") or md_path.stem
        titles_by_slug[md_path.stem] = display_title(
            title, get_scalar(fm_text, "author"), get_scalar(fm_text, "year")
        )

    count = 0
    for md_path in md_paths:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        fm_text, body = parse_frontmatter(text)

        if not fm_text:
            print(f"スキップ: {md_path.name}（frontmatterが見つかりません）")
            continue

        title = get_scalar(fm_text, "title") or md_path.stem
        author = get_scalar(fm_text, "author")
        year = get_scalar(fm_text, "year")
        concepts = get_list(fm_text, "concepts")

        related_lines = []
        for link in get_related_book_links(fm_text):
            target_title = titles_by_slug.get(link["slug"])
            if not target_title:
                print(f"警告: {md_path.name} の relatedBookLinks に未知のslug '{link['slug']}'")
                continue
            note = link.get("note")
            related_lines.append(f"- [[{target_title}]]" + (f" — {note}" if note else ""))

        shown_title = display_title(title, author, year)
        out_path = VAULT_REF_DIR / f"{sanitize_filename(shown_title)}.md"
        status = read_existing_status(out_path) or "unprocessed"

        source_rel_path = f"rekishi-hp/src/content/books/{md_path.name}"
        output = build_output(title, author, year, concepts, status, source_rel_path, body, related_lines)

        out_path.write_text(output, encoding="utf-8")
        count += 1
        tag_note = f"（概念タグ{len(concepts)}件）" if concepts else "（概念タグなし）"
        print(f"変換: {out_path.name}" + tag_note)

    print(f"\n完了: {count}冊を {VAULT_REF_DIR} に変換しました。")


if __name__ == "__main__":
    main()
