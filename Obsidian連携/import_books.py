"""
books/ フォルダの読書テキスト（.txt、歴史シミュレーションv2・授業自動生成と共有）を
Obsidian Vaultの参考文献ノートに変換する。

各引用ブロック（▼で始まる区切り）の末尾に、著者名・タイトル・年号を付記する。
- 著者名・年号は books_meta.json に登録した本のみ表示される
  （テキストのヘッダー表記が本ごとにバラバラで、自動抽出すると誤検出しやすいため）。
- ページ番号は、OCR由来の単独数字行（スキャン時のページ番号がそのまま拾われたもの）が
  ブロック内に見つかった場合のみ、自動で付記される。登録は不要。

新しい本を追加する場合:
    1. books/ に .txt を置く
    2. 著者名・年号を出したい場合は books_meta.json に
       {"ファイル名（拡張子なし）": {"author": "...", "year": "..."}} を追加する
       （タイトルはファイル名から自動生成されるので登録不要）
    3. python import_books.py を再実行する（同名ファイルは上書き）

使い方:
    python import_books.py
"""
import json
import re
from pathlib import Path

BOOKS_DIR = Path(__file__).parent.parent / "books"
VAULT_REF_DIR = Path.home() / "Desktop" / "MyObsidian" / "参考文献"
META_PATH = Path(__file__).parent / "books_meta.json"

BLOCK_HEADER_RE = re.compile(r"^\*{0,2}▼")
PAGE_LINE_RE = re.compile(r"^\*{0,2}(\d{1,4})\*{0,2}$")


def sanitize_filename(text: str, maxlen: int = 60) -> str:
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen] if text else "無題"


def load_meta() -> dict:
    if META_PATH.exists():
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    return {}


def split_blocks(body: str):
    """▼で始まる行を区切りにブロック分割する（▼より前の前置き行は捨てる）。"""
    blocks = []
    header = None
    buf = []
    for line in body.splitlines():
        if BLOCK_HEADER_RE.match(line.strip()):
            if header is not None:
                blocks.append((header, buf))
            header = line
            buf = []
        else:
            buf.append(line)
    if header is not None:
        blocks.append((header, buf))
    return blocks


def extract_pages(lines: list[str]) -> list[int]:
    """ブロック内のOCR由来の単独数字行からページ番号候補を抽出する。

    単独の数字行にはページ番号以外（脚注番号・OCR誤読など）も混ざるため、
    値が近い数字が連続するまとまり（クラスタ）だけを採用し、
    孤立した外れ値（例: 明らかに離れた値が1つだけ混じる場合）は捨てる。
    """
    candidates = [int(m.group(1)) for line in lines if (m := PAGE_LINE_RE.match(line.strip()))]
    if len(candidates) < 2:
        return []

    values = sorted(set(candidates))
    clusters: list[list[int]] = [[values[0]]]
    for v in values[1:]:
        if v - clusters[-1][-1] <= 3:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    largest = max(clusters, key=len)
    return largest if len(largest) >= 2 else []


def display_title(title: str, author: str | None, year: str | None) -> str:
    """ファイル名に著者名・年号が含まれる本（例: 食権力の現代史_藤原辰司_2025、禅談　澤木興道）は、
    books_meta.jsonの値と一致する末尾トークンをタイトルから取り除いて重複を防ぐ。"""
    tokens = re.split(r"[_　]", title)
    while tokens and tokens[-1] in (author, year):
        tokens.pop()
    return "　".join(tokens)


def format_citation(title: str, author: str | None, year: str | None, pages: list[int]) -> str:
    shown_title = display_title(title, author, year)
    name = f"{author}『{shown_title}』" if author else f"『{shown_title}』"
    extras = []
    if year:
        extras.append(str(year))
    if pages:
        lo, hi = min(pages), max(pages)
        extras.append(f"p.{lo}" if lo == hi else f"p.{lo}-{hi}")
    return f"— {name}（{'、'.join(extras)}）" if extras else f"— {name}"


def build_body(body: str, title: str, author: str | None, year: str | None) -> str:
    blocks = split_blocks(body)
    if not blocks:
        return body.rstrip() + "\n\n" + format_citation(title, author, year, [])

    out_lines = []
    for header, lines in blocks:
        pages = extract_pages(lines)
        content_lines = [l for l in lines if not PAGE_LINE_RE.match(l.strip())]
        out_lines.append(header)
        out_lines.extend(content_lines)
        out_lines.append("")
        out_lines.append(format_citation(title, author, year, pages))
        out_lines.append("")
    return "\n".join(out_lines).rstrip() + "\n"


def main():
    if not BOOKS_DIR.exists():
        print(f"{BOOKS_DIR} が見つかりません。")
        return

    VAULT_REF_DIR.mkdir(parents=True, exist_ok=True)
    meta = load_meta()
    count = 0
    for txt_path in sorted(BOOKS_DIR.glob("*.txt")):
        title = re.sub(r"^\d+_", "", txt_path.stem)
        body = txt_path.read_text(encoding="utf-8", errors="ignore")
        book_meta = meta.get(txt_path.stem, {})
        author = book_meta.get("author")
        year = book_meta.get("year")

        new_body = build_body(body, title, author, year)

        out_path = VAULT_REF_DIR / f"{sanitize_filename(title)}.md"
        lines = [
            "---",
            f"title: {title}",
            f"source: books/{txt_path.name}",
            "tags: [参考文献, 読書]",
        ]
        if author:
            lines.append(f"author: {author}")
        if year:
            lines.append(f"year: {year}")
        lines += [
            "---",
            "",
            f"# {title}",
            "",
            new_body,
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")
        count += 1
        print(f"変換: {out_path.name}" + (f"（{author}）" if author else "（著者未登録）"))

    print(f"\n完了: {count}冊を {VAULT_REF_DIR} に変換しました。")


if __name__ == "__main__":
    main()
