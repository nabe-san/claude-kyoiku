"""
rekishi-hp/books-vault/*.md（GAS「サイト用文字起こし」が書き出す引用データ。
教師が本に引いた手書き記号（◎・縦線・横線）の箇所を機械的に抽出したもの）を
Obsidian Vaultの参考文献ノートに変換する。

import_books.py（books/*.txt＝「自動で画像文字化」の全文OCRを手動txt化したもの）とは
入力元が異なる別スクリプト。役割は同じ（06_RawSources/books/への変換）だが、以下の点が異なる。

- 入力元: books/*.txt ではなく rekishi-hp/books-vault/*.md
  （books-vaultはローカル専用・gitignore対象のフォルダなので、git pullは不要。
   Google Driveから書籍ごとのmdファイルを手動でダウンロードして置くだけでよい）
- 著者名・年号: frontmatterに既に入っているため、books_meta.json相当の手動登録は不要
- 本文: books-vaultの引用ブロック（見出し・引用・出典・concepts コメント）を
  そのまま転記する。generate.py側で行われる「公開用に13〜16件へ絞り込む」
  キュレーションは経由しない（このVaultには線を引いた箇所を網羅的に残す方針のため）
- relatedBookLinks（旧版が「## 関連書籍」として出力していた書籍間リンク）は扱わない。
  この情報は公開キュレーション段階（src/content/books側）で人手が加えるものであり、
  books-vault側には存在しないため。rekishi-hp側に行けば今も参照できる。

出力ファイル名は import_books.py と同一の display_title ロジックを用いる
（タイトルから著者名・年号と重複するトークンを除去し、sanitize_filenameで整形）。

注意:
    import_books.py と出力先ディレクトリ（06_RawSources/books/）が同じため、
    同じ書籍を両方のスクリプトで変換すると、同一ファイル名を取り合って上書きし合う。
    現状は import_books.py 側の MIGRATED_TO_CITATIONS で対象書籍を除外済み。

    本文は毎回 books-vault 側のソースで丸ごと上書きするため、Vault側の出力ファイルに
    直接書き込んだ手動編集は次回実行時に消える。

前提:
    rekishi-hp/books-vault/ に最新のmdファイルが揃っていること
    （Google Driveの生成AI【読書文字化】books-vaultから手動ダウンロード済みであること）。

使い方:
    python import_citations.py
"""
import re
import unicodedata
from pathlib import Path

BOOKSVAULT_DIR = Path(__file__).parent.parent.parent / "rekishi-hp" / "books-vault"
VAULT_REF_DIR = Path.home() / "Desktop" / "MyObsidian" / "06_RawSources" / "books"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def sanitize_filename(text: str, maxlen: int = 60) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', " ", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen] if text else "無題"


def display_title(title: str, author: str | None, year: str | None) -> str:
    """ファイル名に著者名・年号が含まれる本は、frontmatterの値と一致する
    末尾トークンをタイトルから取り除いて重複を防ぐ（import_books.pyと同一ロジック）。"""
    tokens = re.split(r"[_　]", title)
    while tokens and tokens[-1] in (author, year):
        tokens.pop()
    return "　".join(tokens)


def read_existing_status(path: Path) -> str | None:
    """出力先に同名ファイルが既にあり、frontmatterにstatusがあればその値を維持する
    （再実行のたびにdraft等のstatusが消えないように）。"""
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


def build_output(title: str, author: str, year: str, status: str,
                  source_rel_path: str, body: str) -> str:
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
    lines.append(f"status: {status}")
    lines += [
        "---",
        "",
        f"# {shown_title}",
        "",
        body.strip(),
        "",
    ]
    return "\n".join(lines)


def main():
    if not BOOKSVAULT_DIR.exists():
        print(f"{BOOKSVAULT_DIR} が見つかりません。")
        print("Google Driveのbooks-vaultから最新のmdファイルをダウンロード済みか確認してください。")
        return

    VAULT_REF_DIR.mkdir(parents=True, exist_ok=True)
    md_paths = sorted(BOOKSVAULT_DIR.glob("*.md"))

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

        shown_title = display_title(title, author, year)
        out_path = VAULT_REF_DIR / f"{sanitize_filename(shown_title)}.md"
        status = read_existing_status(out_path) or "unprocessed"

        source_rel_path = f"rekishi-hp/books-vault/{md_path.name}"
        output = build_output(title, author, year, status, source_rel_path, body)

        out_path.write_text(output, encoding="utf-8")
        count += 1
        print(f"変換: {out_path.name}")

    print(f"\n完了: {count}冊を {VAULT_REF_DIR} に変換しました。")


if __name__ == "__main__":
    main()
